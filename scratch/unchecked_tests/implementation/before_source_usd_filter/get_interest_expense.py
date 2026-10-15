"""Total interest expense; net or nonoperating interest alone is not a substitute."""
from value_retrieval.get_value import (
    get_amount, get_value,
)


def get_interest_expense(financial_data, period_start, period_end):
    """Return this metric using the first successful supported fallback."""
    if period_start is None:
        return None
    return get_value(financial_data, 'us-gaap:InterestExpense', period_end, period_start)


def derive_interest(financial_data, period_start, period_end, *,
                        concept='us-gaap:InterestExpense'):
    """Total = operating + nonoperating; operating expense = income - net income."""
    # Every component must use this same company, dates and USD basis.
    def get_component(concept):
        return get_amount(
            financial_data, concept, period_end, period_start,
        )

    if concept == 'us-gaap:InterestExpense':
        operating_interest = get_component('us-gaap:InterestExpenseOperating')
        nonoperating_interest = get_component('us-gaap:InterestExpenseNonoperating')
        if operating_interest is not None and nonoperating_interest is not None:
            return operating_interest + nonoperating_interest
    else:
        operating_interest_income = get_component('us-gaap:InterestIncomeOperating')
        net_operating_interest = get_component('us-gaap:InterestIncomeExpenseNet')
        if operating_interest_income is not None and net_operating_interest is not None:
            return operating_interest_income - net_operating_interest
    return None
