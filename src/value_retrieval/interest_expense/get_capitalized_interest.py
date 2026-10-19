from value_retrieval.get_value import get_value


def get_capitalized_interest(financial_data, period_start, period_end):
    capitalized = get_value(financial_data, 'us-gaap:InterestCostsCapitalized', period_end, period_start)
    if capitalized is not None:
        return capitalized
    return get_value(financial_data, 'us-gaap:InterestCostsCapitalizedAdjustment', period_end, period_start)
