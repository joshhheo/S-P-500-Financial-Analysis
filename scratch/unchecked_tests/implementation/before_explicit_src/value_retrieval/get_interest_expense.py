"""Total interest expense; net or nonoperating interest alone is not a substitute."""
from value_retrieval.get_value import add_amounts, subtract_amounts

INTEREST_EXPENSE = 'us-gaap:InterestExpense'
OPERATING = 'us-gaap:InterestExpenseOperating'
NONOPERATING = 'us-gaap:InterestExpenseNonoperating'
INTEREST_INCOME = 'us-gaap:InterestIncomeOperating'
NET_INTEREST = 'us-gaap:InterestIncomeExpenseNet'


# The operating/nonoperating expense concepts first appear in US GAAP 2024.
CONCEPTS_FROM_2024 = {OPERATING, NONOPERATING}
SUPPORTED_CONCEPTS = {
    INTEREST_EXPENSE, OPERATING, NONOPERATING, INTEREST_INCOME, NET_INTEREST,
    'us-gaap:FinanceLeaseInterestExpense',
    'us-gaap:InterestCostsIncurred',
    'us-gaap:InterestCostsCapitalized',
}


def get_interest_expense(financial_data, period_start, period_end, *, currency=None, issues=None):
    """Return this metric using the first successful supported fallback."""
    from value_retrieval.get_value import get_value
    if period_start is None:
        from value_retrieval.get_value import SelectionError
        raise SelectionError('Required annual start not established', 'ambiguous_period')
    return get_value(financial_data, INTEREST_EXPENSE, period_end, period_start, currency=currency, issues=issues)


def get_interest_amount(financial_data, period_start, period_end, *,
                        concept=INTEREST_EXPENSE, currency=None, trail=(), role=None, issues=None):
    """Total = operating + nonoperating; operating expense = income - net income."""
    from value_retrieval.get_value import get_amount, get_calculated_amount

    from value_retrieval.get_value import get_reported_amount, calculation_path

    if issues is None:
        issues = set()
    reported = get_reported_amount(
        financial_data, concept, period_end, period_start, currency, issues,
    )
    if reported is not None:
        return reported
    trail = calculation_path(concept, trail, issues)
    if trail is None:
        return None

    # Every component must use this same company, dates, currency and network.
    def get_component(concept):
        return get_amount(
            financial_data, concept, period_end, period_start, currency, trail, role, issues,
        )

    calculated = get_calculated_amount(
        financial_data, concept, period_end, period_start, currency, trail, role, issues,
    )
    if calculated is not None:
        return calculated

    if concept == INTEREST_EXPENSE:
        operating_interest = get_component(OPERATING)
        nonoperating_interest = get_component(NONOPERATING)
        if operating_interest is not None and nonoperating_interest is not None:
            interest_expense = add_amounts([operating_interest, nonoperating_interest])
            return interest_expense
    else:
        operating_interest_income = get_component(INTEREST_INCOME)
        net_operating_interest = get_component(NET_INTEREST)
        if operating_interest_income is not None and net_operating_interest is not None:
            operating_interest = subtract_amounts(
                operating_interest_income, [net_operating_interest],
            )
            return operating_interest
    return None
