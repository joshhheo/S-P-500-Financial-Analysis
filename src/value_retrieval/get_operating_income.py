from value_retrieval.get_value import get_duration_value


def get_operating_income(financial_data, period_start, period_end):
    return get_duration_value(
        financial_data, "us-gaap:OperatingIncomeLoss", period_start, period_end
    )
