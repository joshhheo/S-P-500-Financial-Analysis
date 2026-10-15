"""Select reported facts and evaluate complete filed calculations.

Public get_*_value functions return Decimal or None, as in the original code.
The internal *_amount functions also retain currency, precision and reported-concept dependencies.
"""


from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext


class SelectionError(ValueError):
    """Source evidence does not support an unambiguous result."""

    def __init__(self, message, code='conflict'):
        super().__init__(message)
        self.code = code


def decimal_value(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise SelectionError('Invalid numeric value', 'invalid_number') from error
    if not result.is_finite():
        raise SelectionError('Nonfinite numeric value', 'invalid_number')
    if len(result.as_tuple().digits) > 60 or abs(result.adjusted()) > 1000:
        raise SelectionError('Numeric precision exceeds supported arithmetic', 'unsupported_precision')
    return result


def accuracy_interval(value, decimals):
    if decimals is None:
        raise SelectionError('Missing decimals metadata', 'missing_accuracy')
    try:
        accuracy = Decimal(str(decimals))
    except InvalidOperation as error:
        raise SelectionError('Invalid decimals metadata', 'missing_accuracy') from error
    if accuracy == Decimal('Infinity'):
        return value, value, accuracy
    if not accuracy.is_finite() or accuracy != accuracy.to_integral_value() or abs(accuracy) > 1000:
        raise SelectionError('Invalid decimals metadata', 'missing_accuracy')
    with localcontext() as context:
        context.prec = 2200
        radius = Decimal(10) ** (-accuracy) / 2
        return value - radius, value + radius, accuracy


@dataclass(frozen=True)
class Amount:
    value: Decimal
    unit: str
    period: tuple  # CIK, start (None for instant), end
    lower: Decimal
    upper: Decimal
    sources: frozenset  # Reported concepts used by this amount or its reconciliation.
    direct: bool = False


def calculate_weighted_total(parts):
    """Signed arithmetic with matching contexts and conservative rounding bounds."""
    if not parts or any(amount is None for _, amount in parts):
        return None
    first_amount = parts[0][1]
    unit = first_amount.unit
    period = first_amount.period
    with localcontext() as context:
        context.prec = 2200
        value = Decimal(0)
        lower = Decimal(0)
        upper = Decimal(0)
        for weight, amount in parts:
            if amount.unit != unit or amount.period != period:
                raise SelectionError('Incompatible currency, entity or period', 'incompatible_basis')
            weight = Decimal(weight)
            value += weight * amount.value
            if weight >= 0:
                lower += weight * amount.lower
                upper += weight * amount.upper
            else:
                lower += weight * amount.upper
                upper += weight * amount.lower
        value = decimal_value(value)
    sources = frozenset().union(*(amount.sources for _, amount in parts))
    return Amount(value, unit, period, lower, upper, sources)


def add_amounts(amounts):
    parts = []
    for amount in amounts:
        parts.append((1, amount))
    return calculate_weighted_total(parts)


def subtract_amounts(total, amounts):
    parts = [(1, total)]
    for amount in amounts:
        parts.append((-1, amount))
    return calculate_weighted_total(parts)


def overlaps(left, right):
    return (left.unit == right.unit and left.period == right.period
            and max(left.lower, right.lower) <= min(left.upper, right.upper))


def select_consistent_amount(candidates, label, reported=None):
    """Compare all derivations; overlapping rounding ranges do not pick a unique value."""
    candidates = [c for c in candidates if c is not None]
    if not candidates:
        return reported
    first_amount = candidates[0]
    for candidate in candidates:
        if candidate.unit != first_amount.unit or candidate.period != first_amount.period:
            raise SelectionError('Candidates use incompatible bases', 'incompatible_basis')
    if len(candidates) == 1 and reported is None:
        return candidates[0]
    lower = max(c.lower for c in candidates)
    upper = min(c.upper for c in candidates)
    if lower > upper:
        raise SelectionError(f'{label}: calculation equations disagree beyond rounding')
    if reported is not None:
        if any(not overlaps(reported, c) for c in candidates):
            raise SelectionError(f'{label}: independent reported amount fails reconciliation')
        sources = reported.sources.union(*(c.sources for c in candidates))
        return Amount(reported.value, reported.unit, reported.period, reported.lower, reported.upper, sources)
    values = {c.value for c in candidates}
    if len(values) != 1:
        raise SelectionError(f'{label}: rounding-compatible equations do not identify one disclosed arithmetic result',
                             'rounding_ambiguity')
    candidate = candidates[0]
    sources = frozenset().union(*(c.sources for c in candidates))
    return Amount(candidate.value, candidate.unit, candidate.period, lower, upper, sources)


def uses_reported(amount, concept):
    return concept in amount.sources


# SEC Guide 9.10: selecting consistent repeated reported amounts.
def reported_selection(matches, concept, period_end):
    label = f'{concept} at {period_end}'
    units = {row.get('unit_ref') for row in matches}
    if not units or any(not unit for unit in units):
        raise SelectionError(f'{label}: missing unit metadata', 'incompatible_basis')
    if len(units) != 1:
        raise SelectionError(f'{label}: matching facts use different units', 'incompatible_basis')
    lower, upper = Decimal('-Infinity'), Decimal('Infinity')
    by_accuracy = {}
    selected = None
    best = Decimal('-Infinity')
    for row in matches:
        value = decimal_value(row['value'])
        fact_lower, fact_upper, accuracy = accuracy_interval(value, row.get('decimals'))
        if accuracy in by_accuracy and by_accuracy[accuracy] != value:
            raise SelectionError(f'{label}: differing amounts have equal declared accuracy')
        by_accuracy[accuracy] = value
        lower = max(lower, fact_lower)
        upper = min(upper, fact_upper)
        if accuracy > best:
            selected = value
            best = accuracy
    if lower > upper:
        raise SelectionError(f'{label}: differing amounts cannot be explained by declared rounding')
    return selected, lower, upper


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
    from value_retrieval.source import period_type
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
    period = (financial_data.cik, period_start, period_end)
    return Amount(value, selected_currency, period, lower, upper, frozenset({concept}), True)


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

    from value_retrieval.source import period_type
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
                result = calculate_weighted_total(parts)
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
                result = calculate_weighted_total(signed_parts)
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
             validated=False,
             currency=None, issues=None):
    """Retrieve one metric, preserving its basis, rounding bounds and dependencies."""
    if financial_data is None:
        return None
    from value_retrieval.source import period_type
    duration = period_type(concept, financial_data.year) == 'duration'
    currencies = ([currency] if currency is not None else
                  available_currencies(financial_data, period_end, period_start, duration=validated and duration))
    if validated and duration and period_start is None:
        raise SelectionError('Required annual start not established', 'ambiguous_period')
    if issues is None:
        issues = set()
    amounts = []
    for unit in currencies:
        amount = get_amount(financial_data, concept, period_end, period_start, unit, issues=issues)
        if amount is None:
            continue
        if validated:
            check_reported_amount(
                financial_data, concept, amount, period_end, period_start, unit, issues)
            if concept == 'us-gaap:Assets':
                from value_retrieval.get_assets import check_balance
                check_balance(financial_data, amount, period_end, unit, issues)
        amounts.append(amount)
    if len(amounts) > 1:
        raise SelectionError(
            'Multiple currencies available; reporting currency is not established', 'ambiguous_currency',
        )
    return amounts[0] if amounts else None


def get_value(financial_data, concept, period_end, period_start=None, *, currency=None, issues=None):
    amount = retrieve(financial_data, concept, period_end, period_start,
                      validated=True, currency=currency, issues=issues)
    if amount is None:
        return None
    return amount.value


def check_reported_amount(financial_data, concept, amount, period_end,
                          period_start=None, currency=None, issues=None):
    """Compare a reported operand with calculations that do not reuse that operand."""
    if not amount.direct:
        return
    candidates = get_calculated_amounts(
        financial_data, concept, period_end, period_start,
        currency, trail=(concept,), issues=issues,
    )
    for candidate in candidates:
        if uses_reported(candidate, concept):
            continue
        if not overlaps(amount, candidate):
            raise SelectionError(f'{concept}: independent filed equation fails reconciliation')
