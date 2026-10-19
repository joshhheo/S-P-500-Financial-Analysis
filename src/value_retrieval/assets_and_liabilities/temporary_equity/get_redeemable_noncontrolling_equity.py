from value_retrieval.get_value import get_value


def get_redeemable_noncontrolling_equity(financial_data, period_end):
    total = get_value(financial_data, 'us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount', period_end)
    if total is not None:
        return total
    common = get_value(financial_data, 'us-gaap:RedeemableNoncontrollingInterestEquityCommonCarryingAmount', period_end)
    preferred = get_value(financial_data, 'us-gaap:RedeemableNoncontrollingInterestEquityPreferredCarryingAmount', period_end)
    other = get_value(financial_data, 'us-gaap:RedeemableNoncontrollingInterestEquityOtherCarryingAmount', period_end)
    if common is not None and preferred is not None and other is not None:
        return common + preferred + other
    return None
