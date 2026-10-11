from quick_setup.get_operating_income_interest_expense import (
    get_operating_income_interest_expense,
)


def calculate_interest_coverage(financial_data, period_start, period_end):
    values = get_operating_income_interest_expense(
        financial_data, period_start, period_end
    )

    operating_income = values["operating_income"]
    interest_expense = values["interest_expense"]

    if operating_income is None or interest_expense is None:
        return None

    if interest_expense == 0:
        return None

    return operating_income / interest_expense
