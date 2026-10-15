"""Select reported facts and evaluate complete filed calculations.

Public get_*_value functions return Decimal or None, as in the original code.
All arithmetic uses values fetched with the same explicit currency and dates.
"""


from decimal import Decimal, localcontext


def decimal_value(value):
    """Convert a compliant numeric fact; missing values stay missing."""
    return None if value is None else Decimal(str(value))


def calculate_weighted_total(parts):
    """Components have already been fetched on one company/period/currency basis."""
    if not parts or any(value is None for _, value in parts):
        return None
    with localcontext() as context:
        context.prec = 2200
        return sum(weight * value for weight, value in parts)


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


def get_reported_fact(financial_data, concept, period_end, period_start=None,
                        currency=None):
    from value_retrieval.source import period_type
    expected_period = 'instant' if period_start is None else 'duration'
    if period_type(concept) != expected_period:
        return None

    matches = matching_facts(financial_data, concept, period_end, period_start)
    numeric_facts = []
    for fact in matches:
        if fact.get('nil') or fact['value'] == '':
            continue
        unit = financial_data.units.get(fact['unit_ref'])
        if unit is None:
            return None
        if currency is not None and unit != currency:
            continue
        numeric_facts.append(dict(fact, unit_ref=unit))
    if not numeric_facts:
        return None

    selected_currency = numeric_facts[0]['unit_ref']
    for fact in matches:
        if fact.get('nil') and financial_data.units.get(fact['unit_ref']) == selected_currency:
            return None

    if len({fact['unit_ref'] for fact in numeric_facts}) != 1:
        return None
    # Compliant duplicates agree or differ only in rounding; keep the first.
    return numeric_facts[0]


def get_reported_amount(financial_data, concept, period_end, period_start=None,
                        currency=None):
    fact = get_reported_fact(financial_data, concept, period_end, period_start, currency)
    return decimal_value(fact['value']) if fact is not None else None


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
                        period_start=None, currency=None):
    from value_retrieval.get_equity import equation_applies

    if financial_data.calculation_issue:
        return False

    if len({name for name, _ in children}) != len(children):
        return False

    from value_retrieval.source import period_type
    expected_period = 'instant' if period_start is None else 'duration'
    if period_type(parent) != expected_period:
        return False
    for name, weight in children:
        if weight not in (-1, 1) or period_type(name) != expected_period:
            return False
    return equation_applies(
        financial_data, parent, children, period_end, period_start, currency,
    )


def get_calculated_amount(financial_data, concept, period_end, period_start=None,
                           currency=None, trail=(), role=None):
    """Return the first complete applicable equation in supplied network order.

    trail lists concepts already being calculated, preventing circular fallbacks.
    role keeps nested calculations inside the same filed calculation network.
    """
    for (network, parent), children in financial_data.equations.items():
        if role is not None and network != role:
            continue
        child_names = [name for name, weight in children]
        if parent != concept and concept not in child_names:
            continue
        if not calculation_applies(
            financial_data, parent, children, period_end, period_start, currency,
        ):
            continue

        parts = []
        component_sign = 1
        if parent != concept:
            # Solve one missing child from an independently reported total.
            total = get_reported_amount(
                financial_data, parent, period_end, period_start, currency,
            )
            if total is None:
                continue
            target_weight = next(weight for child, weight in children if child == concept)
            parts.append((target_weight, total))
            component_sign = -target_weight

        for child, weight in children:
            if parent != concept and child == concept:
                continue
            if is_blank_caption(financial_data, child, period_end, period_start):
                continue
            amount = get_amount(
                financial_data, child, period_end, period_start, currency, trail, network,
            )
            if amount is None:
                break
            parts.append((component_sign * weight, amount))
        else:
            result = calculate_weighted_total(parts)
            if result is not None:
                return result
    return None


def get_amount(financial_data, concept, period_end, period_start=None,
               currency=None, trail=(), role=None):
    """Look up a calculation component, using its metric rules when applicable."""

    with localcontext() as context:
        context.prec = 2200
        reported = get_reported_amount(
            financial_data, concept, period_end, period_start, currency,
        )
        if reported is not None:
            return reported
        if concept in trail or concept == 'us-gaap:CommitmentsAndContingencies':
            return None
        trail = trail + (concept,)
        calculated = get_calculated_amount(
            financial_data, concept, period_end, period_start, currency, trail, role,
        )
        if calculated is not None:
            return calculated

        # Only after reported and filed calculations, use the metric's accounting rules.
        if concept == 'us-gaap:Assets':
            from value_retrieval.get_assets import derive_assets
            return derive_assets(
                financial_data, period_end, period_start, currency, trail, role,
            )
        if concept == 'us-gaap:Liabilities':
            from value_retrieval.get_liabilities import derive_liabilities
            return derive_liabilities(
                financial_data, period_end, period_start, currency, trail, role,
            )
        if concept in (
            'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
            'us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests',
        ):
            from value_retrieval.get_equity import derive_equity
            return derive_equity(
                financial_data, concept, period_end, period_start, currency, trail, role,
            )
        if concept in ('us-gaap:InterestExpense', 'us-gaap:InterestExpenseOperating'):
            from value_retrieval.get_interest_expense import derive_interest
            return derive_interest(
                financial_data, period_start, period_end, concept=concept,
                currency=currency, trail=trail, role=role,
            )

        return None


def available_currencies(financial_data, period_end, period_start=None, *, duration=False):
    """Return candidate currencies, or None when the reporting basis is invalid."""
    if duration and period_start is None:
        return None
    if financial_data is None:
        return None
    preferred = financial_data.reporting_currencies(period_end)
    if len(preferred) > 1:
        return None
    return sorted(preferred) if preferred else financial_data.currencies(period_end, period_start)


def get_value(financial_data, concept, period_end, period_start=None, *,
             currency=None):
    """Retrieve one metric, using the first successful fallback on each currency basis."""
    if financial_data is None:
        return None
    from value_retrieval.source import period_type
    duration = period_type(concept) == 'duration'
    currencies = ([currency] if currency is not None else
                  available_currencies(financial_data, period_end, period_start, duration=duration))
    if currencies is None:
        return None
    if duration and period_start is None:
        return None
    amounts = []
    for unit in currencies:
        amount = get_amount(financial_data, concept, period_end, period_start, unit)
        if amount is None:
            continue
        amounts.append(amount)
    if len(amounts) > 1:
        return None
    return amounts[0] if amounts else None

