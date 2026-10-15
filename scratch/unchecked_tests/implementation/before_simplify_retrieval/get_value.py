"""Select reported facts and evaluate complete filed calculations.

Public get_*_value functions return Decimal or None, as in the original code.
The internal *_amount functions also retain currency and precision.
"""


from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext


def decimal_value(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not result.is_finite():
        return None
    if len(result.as_tuple().digits) > 60 or abs(result.adjusted()) > 1000:
        return None
    return result


def accuracy_interval(value, decimals):
    if decimals is None:
        return None
    try:
        accuracy = Decimal(str(decimals))
    except InvalidOperation:
        return None
    if accuracy.is_infinite() and not accuracy.is_signed():
        return value, value, accuracy
    if not accuracy.is_finite() or accuracy != accuracy.to_integral_value() or abs(accuracy) > 1000:
        return None
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

    def __add__(self, other):
        return calculate_weighted_total([(1, self), (1, other)])

    def __radd__(self, other):
        return None if other is None else NotImplemented

    def __rsub__(self, other):
        return None if other is None else NotImplemented

    def __sub__(self, other):
        return calculate_weighted_total([(1, self), (-1, other)])


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
                return None
            weight = Decimal(weight)
            value += weight * amount.value
            if weight >= 0:
                lower += weight * amount.lower
                upper += weight * amount.upper
            else:
                lower += weight * amount.upper
                upper += weight * amount.lower
        value = decimal_value(value)
    if value is None:
        return None
    return Amount(value, unit, period, lower, upper)


def overlaps(left, right):
    return (left.unit == right.unit and left.period == right.period
            and max(left.lower, right.lower) <= min(left.upper, right.upper))


# Assume SEC-compliant duplicates (Guide 9.10); retain the first reported value.
def reported_selection(matches, concept, period_end):
    units = {row.get('unit_ref') for row in matches}
    if len(units) != 1 or not all(units):
        return None
    row = matches[0]
    value = decimal_value(row['value'])
    if value is None:
        return None
    interval = accuracy_interval(value, row.get('decimals'))
    if interval is None:
        return None
    lower, upper, _ = interval
    return value, lower, upper


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

    selected = reported_selection(numeric_facts, concept, period_end)
    if selected is None:
        return None
    value, lower, upper = selected
    period = (financial_data.cik, period_start, period_end)
    return Amount(value, selected_currency, period, lower, upper)


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

    names = set()
    for name, weight in children:
        if name in names:
            return False
        names.add(name)

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

        if parent == concept:
            # The target is the total: add its immediate children with filed weights.
            parts = []
            for child, weight in children:
                if is_blank_caption(financial_data, child, period_end, period_start):
                    continue
                amount = get_amount(
                    financial_data, child, period_end, period_start,
                    currency, trail, network,
                )
                if amount is None:
                    break
                parts.append((weight, amount))
            else:
                result = calculate_weighted_total(parts)
                if result is not None:
                    return result
        else:
            # The target is one unknown child. The total must be reported independently.
            total = get_reported_amount(
                financial_data, parent, period_end, period_start, currency,
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
                    currency, trail, network,
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
                    return result
    return None


def calculation_path(concept, trail):
    """Track amounts already being calculated so fallbacks cannot circle back."""
    if concept == 'us-gaap:CommitmentsAndContingencies' or concept in trail:
        return None
    if len(trail) > 30:
        return None
    return trail + (concept,)


def get_amount(financial_data, concept, period_end, period_start=None,
               currency=None, trail=(), role=None):
    """Look up a calculation component, using its metric rules when applicable."""

    # Named metric getters own both reported lookup and their accounting fallbacks.
    # This routing also makes those rules available to nested filed calculations.
    if concept == 'us-gaap:Assets':
        from value_retrieval.get_assets import get_asset_amount
        return get_asset_amount(
            financial_data, period_end, period_start, currency, trail, role,
        )
    if concept == 'us-gaap:Liabilities':
        from value_retrieval.get_liabilities import get_liability_amount
        return get_liability_amount(
            financial_data, period_end, period_start, currency, trail, role,
        )
    if concept in (
        'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
        'us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests',
    ):
        from value_retrieval.get_equity import get_equity_amount
        return get_equity_amount(
            financial_data, concept, period_end, period_start, currency, trail, role,
        )
    if concept in ('us-gaap:InterestExpense', 'us-gaap:InterestExpenseOperating'):
        from value_retrieval.get_interest_expense import get_interest_amount
        return get_interest_amount(
            financial_data, period_start, period_end, concept=concept,
            currency=currency, trail=trail, role=role,
        )

    reported = get_reported_amount(
        financial_data, concept, period_end, period_start, currency,
    )
    if reported is not None:
        return reported
    trail = calculation_path(concept, trail)
    if trail is None:
        return None
    return get_calculated_amount(
        financial_data, concept, period_end, period_start, currency, trail, role,
    )


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


def retrieve(financial_data, concept, period_end, period_start=None, *,
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


def get_value(financial_data, concept, period_end, period_start=None, *, currency=None):
    amount = retrieve(financial_data, concept, period_end, period_start,
                      currency=currency)
    if amount is None:
        return None
    return amount.value
