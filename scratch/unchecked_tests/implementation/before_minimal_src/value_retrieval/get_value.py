"""Select reported facts and evaluate complete filed calculations.

Public get_*_value functions return Decimal or None, as in the original code.
The internal *_amount functions also retain currency, precision and evidence.
"""
from value_retrieval.amount import Amount, SelectionError, select_consistent_amount, calculate_weighted_total, reported_selection, overlaps, uses_reported
from value_retrieval.source import period_type


def normalize_concept_name(concept):
    if concept.startswith('us-gaap_'):
        return 'us-gaap:' + concept[len('us-gaap_'):]
    return concept


def matching_facts(financial_data, concept, period_end, period_start=None):
    matches = []
    for fact in financial_data.records:
        if fact['concept'] != concept:
            continue
        if fact['is_dimensioned'] or fact['entity_identifier'] != financial_data.cik:
            continue
        if period_start is None:
            if fact['period_instant'] != period_end:
                continue
        else:
            if fact['period_start'] != period_start or fact['period_end'] != period_end:
                continue
        matches.append(fact)
    return matches


def get_reported_amount(financial_data, concept, period_end, period_start=None,
                        currency=None, issues=None):
    if issues is None:
        issues = set()
    expected_period = 'instant' if period_start is None else 'duration'
    if period_type(concept, financial_data.year) != expected_period:
        issues.add('unsupported_concept_or_period')
        return None

    matches = matching_facts(financial_data, concept, period_end, period_start)
    numeric_facts = []
    for fact in matches:
        if fact.get('nil') or fact['value'] == '':
            continue
        unit = financial_data.units.get(fact['unit_ref'])
        if unit is None:
            raise SelectionError(f'{concept}: monetary unit cannot be resolved', 'incompatible_basis')
        if currency is not None and unit != currency:
            continue
        numeric_facts.append(dict(fact, unit_ref=unit))
    if not numeric_facts:
        return None

    selected_currency = numeric_facts[0]['unit_ref']
    for fact in matches:
        if fact.get('nil') and financial_data.units.get(fact['unit_ref']) == selected_currency:
            raise SelectionError(f'{concept}: nil and numeric duplicates conflict')

    value, lower, upper = reported_selection(numeric_facts, concept, period_end)
    occurrences = []
    for fact in numeric_facts:
        occurrences.append(dict(
            context=fact['context_ref'], fact_id=fact.get('fact_id'),
            value=fact['value'], decimals=fact.get('decimals'),
        ))
    evidence = dict(
        method='reported', concept=concept, taxonomy=financial_data.namespace,
        accession=financial_data.accession, occurrences=occurrences,
    )
    period = (financial_data.cik, period_start, period_end)
    return Amount(value, selected_currency, period, lower, upper, evidence)


def is_blank_caption(financial_data, concept, period_end, period_start=None):
    if concept != 'us-gaap:CommitmentsAndContingencies':
        return False
    matches = matching_facts(financial_data, concept, period_end, period_start)
    if not matches:
        return False
    for fact in matches:
        if not fact.get('nil') or fact['value'] != '':
            return False
    return True


def calculation_applies(financial_data, parent, children, period_end,
                        period_start=None, currency=None, issues=None):
    from value_retrieval.get_equity import equation_applies

    if issues is None:
        issues = set()
    if financial_data.calculation_issue:
        issues.add('unsupported_calculation_structure')
        return False

    names = set()
    for name, weight in children:
        if name in names:
            issues.add('duplicate_relationship')
            return False
        names.add(name)

    expected_period = 'instant' if period_start is None else 'duration'
    if period_type(parent, financial_data.year) != expected_period:
        issues.add('unsupported_calculation_component')
        return False
    for name, weight in children:
        if weight not in (-1, 1) or period_type(name, financial_data.year) != expected_period:
            issues.add('unsupported_calculation_component')
            return False
    return equation_applies(
        financial_data, parent, children, period_end, period_start, currency, issues,
    )


def get_calculated_amounts(financial_data, concept, period_end, period_start=None,
                           currency=None, trail=(), role=None, issues=None):
    """Keep each complete equation separate so conflicting results can be checked.

    trail lists concepts already being calculated, preventing circular fallbacks.
    role keeps nested calculations inside the same filed calculation network.
    """
    if issues is None:
        issues = set()
    candidates = []
    for (network, parent), children in financial_data.equations.items():
        if role is not None and network != role:
            continue
        child_names = [name for name, weight in children]
        if parent != concept and concept not in child_names:
            continue
        if not calculation_applies(
            financial_data, parent, children, period_end, period_start, currency, issues,
        ):
            continue

        if parent == concept:
            # The target is the total: add its immediate children with filed weights.
            parts = []
            for child, weight in children:
                if is_blank_caption(financial_data, child, period_end, period_start):
                    continue
                amount = get_amount(
                    financial_data, child, period_end, period_start,
                    currency, trail, network, issues,
                )
                if amount is None:
                    break
                parts.append((weight, amount))
            else:
                rule = dict(kind='filed_forward', role=network, parent=parent)
                result = calculate_weighted_total(parts, rule)
                if result is not None:
                    candidates.append(result)
        else:
            # The target is one unknown child. The total must be reported independently.
            total = get_reported_amount(
                financial_data, parent, period_end, period_start, currency, issues,
            )
            if total is None:
                continue
            for child, weight in children:
                if child == concept:
                    target_weight = weight
                    break

            parts = [(1, total)]
            for child, weight in children:
                if child == concept or is_blank_caption(financial_data, child, period_end, period_start):
                    continue
                amount = get_amount(
                    financial_data, child, period_end, period_start,
                    currency, trail, network, issues,
                )
                if amount is None:
                    break
                parts.append((-weight, amount))
            else:
                signed_parts = []
                for weight, amount in parts:
                    signed_parts.append((weight * target_weight, amount))
                rule = dict(kind='filed_inverse', role=network, parent=parent, target=concept)
                result = calculate_weighted_total(signed_parts, rule)
                if result is not None:
                    candidates.append(result)
    return candidates


def calculation_path(concept, trail, issues):
    """Track amounts already being calculated so fallbacks cannot circle back."""
    if concept == 'us-gaap:CommitmentsAndContingencies' or concept in trail:
        return None
    if len(trail) > 30:
        issues.add('calculation_depth_limit')
        return None
    return trail + (concept,)


def get_amount(financial_data, concept, period_end, period_start=None,
               currency=None, trail=(), role=None, issues=None):
    """Look up a calculation component, using its metric rules when applicable."""
    if issues is None:
        issues = set()

    # Named metric getters own both reported lookup and their accounting fallbacks.
    # This routing also makes those rules available to nested filed calculations.
    if concept == 'us-gaap:Assets':
        from value_retrieval.get_assets import get_asset_amount
        return get_asset_amount(
            financial_data, period_end, period_start, currency, trail, role, issues,
        )
    if concept == 'us-gaap:Liabilities':
        from value_retrieval.get_liabilities import get_liability_amount
        return get_liability_amount(
            financial_data, period_end, period_start, currency, trail, role, issues,
        )
    if concept in (
        'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
        'us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests',
    ):
        from value_retrieval.get_equity import get_equity_amount
        return get_equity_amount(
            financial_data, concept, period_end, period_start, currency, trail, role, issues,
        )
    if concept in ('us-gaap:InterestExpense', 'us-gaap:InterestExpenseOperating'):
        from value_retrieval.get_interest_expense import get_interest_amount
        return get_interest_amount(
            financial_data, period_start, period_end, concept=concept,
            currency=currency, trail=trail, role=role, issues=issues,
        )

    reported = get_reported_amount(
        financial_data, concept, period_end, period_start, currency, issues,
    )
    if reported is not None:
        return reported
    trail = calculation_path(concept, trail, issues)
    if trail is None:
        return None
    candidates = get_calculated_amounts(
        financial_data, concept, period_end, period_start, currency, trail, role, issues,
    )
    return select_consistent_amount(candidates, concept)


def available_currencies(financial_data, period_end, period_start=None, *, duration=False):
    """Return the filing's reporting currency, or its disclosed candidate currencies."""
    if duration and period_start is None:
        raise SelectionError('Required annual start not established', 'ambiguous_period')
    if financial_data is None:
        raise SelectionError('No financial source available', 'missing_source')
    preferred = financial_data.reporting_currency(period_end)
    return [preferred] if preferred else financial_data.currencies(period_end, period_start)


def retrieve(financial_data, concept, period_end, period_start=None, *,
             reported_only=False, calculated_only=False, validated=False,
             currency=None, audit=None):
    """Retrieve one metric independently; optional audit records its checks."""
    if financial_data is None:
        return None
    duration = period_type(concept, financial_data.year) == 'duration'
    currencies = ([currency] if currency is not None else
                  available_currencies(financial_data, period_end, period_start, duration=validated and duration))
    if validated and duration and period_start is None:
        raise SelectionError('Required annual start not established', 'ambiguous_period')
    issues = set()
    amounts = []
    checks = []
    for unit in currencies:
        if reported_only:
            amount = get_reported_amount(financial_data, concept, period_end, period_start, unit, issues)
        elif calculated_only:
            candidates = get_calculated_amounts(
                financial_data, concept, period_end, period_start, unit,
                trail=(concept,), issues=issues,
            )
            amount = select_consistent_amount(candidates, concept)
        else:
            amount = get_amount(financial_data, concept, period_end, period_start, unit, issues=issues)
        if amount is None:
            continue
        if validated:
            checks.extend(check_reported_amount(
                financial_data, concept, amount, period_end, period_start, unit, issues))
            if concept == 'us-gaap:Assets':
                from value_retrieval.get_assets import check_balance
                checks.extend(check_balance(financial_data, amount, period_end, unit, issues))
        amounts.append(amount)
    if len(amounts) > 1:
        raise SelectionError(
            'Multiple currencies available; reporting currency is not established', 'ambiguous_currency',
        )
    amount = amounts[0] if amounts else None
    if audit is not None:
        audit.setdefault('issues', set()).update(issues)
        audit.setdefault('checks', []).extend(checks)
        audit.setdefault('amounts', {})[concept] = amount.serializable() if amount is not None else None
    return amount


def get_reported_value(financial_data, concept, period_end, period_start=None):
    amount = retrieve(financial_data, concept, period_end, period_start, reported_only=True)
    if amount is None:
        return None
    return amount.value


def get_calculated_value(financial_data, concept, period_end, period_start=None):
    amount = retrieve(financial_data, concept, period_end, period_start, calculated_only=True)
    if amount is None:
        return None
    return amount.value


def get_value(financial_data, concept, period_end, period_start=None, *, currency=None, audit=None):
    amount = retrieve(financial_data, concept, period_end, period_start,
                      validated=True, currency=currency, audit=audit)
    if amount is None:
        return None
    return amount.value


def get_instant_value(financial_data, concept, period_end):
    return get_value(financial_data, concept, period_end)


def get_duration_value(financial_data, concept_name, period_start, period_end):
    if period_start is None or period_end is None:
        return None
    return get_value(financial_data, concept_name, period_end, period_start)


def check_reported_amount(financial_data, concept, amount, period_end,
                          period_start=None, currency=None, issues=None):
    """Compare a reported operand with calculations that do not reuse that operand."""
    checks = []
    if amount.evidence.get('method') != 'reported':
        return checks
    candidates = get_calculated_amounts(
        financial_data, concept, period_end, period_start,
        currency, trail=(concept,), issues=issues,
    )
    for candidate in candidates:
        if uses_reported(candidate, concept):
            continue
        if not overlaps(amount, candidate):
            raise SelectionError(f'{concept}: independent filed equation fails reconciliation')
        checks.append(dict(
            check='independent_filed_equation', concept=concept, amount=candidate.serializable(),
        ))
    return checks
