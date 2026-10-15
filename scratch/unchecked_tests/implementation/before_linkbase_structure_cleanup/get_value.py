"""Select reported facts, then use explicit accounting formulas.

Public get_*_value functions return Decimal or None, as in the original code.
All arithmetic uses values fetched with the same explicit currency and dates.
"""


from decimal import Decimal, localcontext


def decimal_value(value):
    """Convert a compliant numeric fact; missing values stay missing."""
    return None if value is None else Decimal(str(value))


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


def get_amount(financial_data, concept, period_end, period_start=None,
               currency=None, trail=()):
    """Retrieve a concept, preventing circular accounting fallbacks."""

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
        # Reported facts precede explicit accounting formulas.
        if concept == 'us-gaap:Assets':
            from value_retrieval.get_assets import derive_assets
            return derive_assets(
                financial_data, period_end, period_start, currency, trail,
            )
        if concept == 'us-gaap:Liabilities':
            from value_retrieval.get_liabilities import derive_liabilities
            return derive_liabilities(
                financial_data, period_end, period_start, currency, trail,
            )
        if concept in (
            'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
            'us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests',
        ):
            from value_retrieval.get_equity import derive_equity
            return derive_equity(
                financial_data, concept, period_end, period_start, currency, trail,
            )
        if concept in ('us-gaap:InterestExpense', 'us-gaap:InterestExpenseOperating'):
            from value_retrieval.get_interest_expense import derive_interest
            return derive_interest(
                financial_data, period_start, period_end, concept=concept,
                currency=currency, trail=trail,
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

