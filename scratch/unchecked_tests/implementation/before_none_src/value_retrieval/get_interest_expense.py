"""Total interest expense; net or nonoperating interest alone is not a substitute."""
from value_retrieval.get_value import (
    SelectionError, calculation_path, get_amount, get_calculated_amount, get_reported_amount, get_value,
)


def get_interest_expense(financial_data, period_start, period_end, *, currency=None, issues=None):
    """Return this metric using the first successful supported fallback."""
    if period_start is None:
        raise SelectionError('Required annual start not established', 'ambiguous_period')
    return get_value(financial_data, 'us-gaap:InterestExpense', period_end, period_start, currency=currency, issues=issues)


def get_interest_amount(financial_data, period_start, period_end, *,
                        concept='us-gaap:InterestExpense', currency=None, trail=(), role=None, issues=None):
    """Total = operating + nonoperating; operating expense = income - net income."""


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

    if concept == 'us-gaap:InterestExpense':
        operating_interest = get_component('us-gaap:InterestExpenseOperating')
        nonoperating_interest = get_component('us-gaap:InterestExpenseNonoperating')
        if operating_interest is not None and nonoperating_interest is not None:
            interest_expense = operating_interest + nonoperating_interest
            return interest_expense
    else:
        operating_interest_income = get_component('us-gaap:InterestIncomeOperating')
        net_operating_interest = get_component('us-gaap:InterestIncomeExpenseNet')
        if operating_interest_income is not None and net_operating_interest is not None:
            operating_interest = operating_interest_income - net_operating_interest
            return operating_interest
    return None
