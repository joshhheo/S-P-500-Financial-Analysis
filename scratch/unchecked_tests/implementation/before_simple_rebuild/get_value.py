"""Select reported facts, then use explicit accounting formulas.

Public get_*_value functions return Decimal or None, as in the original code.
All arithmetic uses values fetched with the same USD basis and dates.
"""


from decimal import Decimal, localcontext


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


def get_reported_amount(financial_data, concept, period_end, period_start=None):
    from value_retrieval.source import period_type
    expected_period = 'instant' if period_start is None else 'duration'
    if period_type(concept) != expected_period:
        return None

    matches = matching_facts(financial_data, concept, period_end, period_start)
    if any(fact.get('nil') for fact in matches):
        return None
    # Compliant duplicates agree or differ only in rounding; keep the first.
    for fact in matches:
        if fact['value'] != '':
            return Decimal(fact['value'])
    return None


def get_value(financial_data, concept, period_end, period_start=None,
               trail=()):
    """Retrieve a concept, preventing circular accounting fallbacks."""

    if financial_data is None:
        return None
    from value_retrieval.source import period_type
    if period_type(concept) == 'duration' and period_start is None:
        return None

    with localcontext() as context:
        context.prec = 2200
        reported = get_reported_amount(
            financial_data, concept, period_end, period_start,
        )
        if reported is not None:
            return reported
        if concept in trail:
            return None
        trail = trail + (concept,)
        # Reported facts precede explicit accounting formulas.
        if concept == 'us-gaap:Assets':
            from value_retrieval.get_assets import derive_assets
            return derive_assets(
                financial_data, period_end, period_start, trail,
            )
        if concept == 'us-gaap:Liabilities':
            from value_retrieval.get_liabilities import derive_liabilities
            return derive_liabilities(
                financial_data, period_end, period_start, trail,
            )
        if concept in (
            'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
            'us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests',
        ):
            from value_retrieval.get_equity import derive_equity
            return derive_equity(
                financial_data, concept, period_end, period_start,
            )
        if concept in ('us-gaap:InterestExpense', 'us-gaap:InterestExpenseOperating'):
            from value_retrieval.get_interest_expense import derive_interest
            return derive_interest(
                financial_data, period_start, period_end, concept=concept,
            )

        return None
