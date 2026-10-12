from value_retrieval.get_operating_income import get_operating_income
from value_retrieval.get_interest_expense import get_interest_expense


def calculate_interest_coverage(financial_data, period_start, period_end):
    operating_income = get_operating_income(financial_data, period_start, period_end)
    interest_expense = get_interest_expense(financial_data, period_start, period_end)

    if operating_income is None or interest_expense is None:
        return None

    if interest_expense == 0:
        return None

    return operating_income / interest_expense
