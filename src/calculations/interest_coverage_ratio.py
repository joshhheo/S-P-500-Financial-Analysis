from value_retrieval.get_operating_income import get_operating_income
from value_retrieval.get_interest_expense import get_interest_expense


def calculate_interest_coverage(financial_data, period_start, period_end):
    income = get_operating_income(financial_data, period_start, period_end)
    interest = get_interest_expense(financial_data, period_start, period_end)
    if income is None or interest is None:
        return None
    if interest == 0:
        return None
    return income / interest
