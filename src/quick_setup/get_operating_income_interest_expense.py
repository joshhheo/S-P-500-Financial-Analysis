from quick_setup.get_calculated_value import get_value


def get_annual_value(financial_data, concept_name, period_start, period_end):
    if period_start is None or period_end is None:
        return None
    return get_value(financial_data, concept_name, period_end, period_start)


def get_operating_income_interest_expense(
    financial_data, period_start, period_end
):
    operating_income = get_annual_value(
        financial_data,
        "us-gaap:OperatingIncomeLoss",
        period_start,
        period_end,
    )

    interest_expense = get_annual_value(
        financial_data,
        "us-gaap:InterestExpense",
        period_start,
        period_end,
    )

    if interest_expense is None:
        operating_interest = get_annual_value(
            financial_data,
            "us-gaap:InterestExpenseOperating",
            period_start,
            period_end,
        )

        if operating_interest is None:
            operating_interest_income = get_annual_value(
                financial_data,
                "us-gaap:InterestIncomeOperating",
                period_start,
                period_end,
            )

            net_operating_interest = get_annual_value(
                financial_data,
                "us-gaap:InterestIncomeExpenseNet",
                period_start,
                period_end,
            )

            if (
                operating_interest_income is not None
                and net_operating_interest is not None
            ):
                operating_interest = (
                    operating_interest_income - net_operating_interest
                )

        nonoperating_interest = get_annual_value(
            financial_data,
            "us-gaap:InterestExpenseNonoperating",
            period_start,
            period_end,
        )

        if operating_interest is not None and nonoperating_interest is not None:
            interest_expense = operating_interest + nonoperating_interest

    return {
        "operating_income": operating_income,
        "interest_expense": interest_expense,
    }
