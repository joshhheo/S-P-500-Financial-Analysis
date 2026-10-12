from value_retrieval.get_value import get_duration_value


def get_interest_expense(financial_data, period_start, period_end):
    interest_expense = get_duration_value(
        financial_data,
        "us-gaap:InterestExpense",
        period_start,
        period_end,
    )

    if interest_expense is None:
        operating_interest = get_duration_value(
            financial_data,
            "us-gaap:InterestExpenseOperating",
            period_start,
            period_end,
        )

        if operating_interest is None:
            operating_interest_income = get_duration_value(
                financial_data,
                "us-gaap:InterestIncomeOperating",
                period_start,
                period_end,
            )

            net_operating_interest = get_duration_value(
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

        nonoperating_interest = get_duration_value(
            financial_data,
            "us-gaap:InterestExpenseNonoperating",
            period_start,
            period_end,
        )

        if operating_interest is not None and nonoperating_interest is not None:
            interest_expense = operating_interest + nonoperating_interest

    return interest_expense
