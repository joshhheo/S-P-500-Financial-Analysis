"""Calculate interest coverage from retrieved values."""
from decimal import localcontext
from value_retrieval.get_operating_income import get_operating_income
from value_retrieval.get_interest_expense import get_interest_expense
from value_retrieval.get_value import SelectionError


def calculate_interest_coverage(financial_data, period_start, period_end, *, currency, issues=None):
    income = get_operating_income(financial_data, period_start, period_end, currency=currency, issues=issues)
    interest = get_interest_expense(financial_data, period_start, period_end, currency=currency, issues=issues)
    if income is None or interest is None:
        return None
    if interest == 0:
        raise SelectionError('Division by zero', 'zero_denominator')
    with localcontext() as context:
        context.prec = 28
        context.rounding = 'ROUND_HALF_EVEN'
        return income / interest
