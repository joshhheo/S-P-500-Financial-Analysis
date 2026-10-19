from value_retrieval.get_value import get_value


def get_operating_interest_income(financial_data, period_start, period_end):
    income = get_value(financial_data, 'us-gaap:InterestIncomeOperating', period_end, period_start)
    if income is not None:
        return income
    combined = get_value(financial_data, 'us-gaap:InterestAndDividendIncomeOperating', period_end, period_start)
    dividends = get_value(financial_data, 'us-gaap:DividendIncomeOperating', period_end, period_start)
    if combined is not None and dividends is not None:
        return combined - dividends
    return None
