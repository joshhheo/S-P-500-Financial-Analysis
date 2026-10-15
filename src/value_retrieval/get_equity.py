from value_retrieval.get_value import get_value


def get_equity(financial_data, period_end):
    equity = get_value(financial_data, 'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest', period_end)
    if equity is None:
        parent = get_value(financial_data, 'us-gaap:StockholdersEquity', period_end)
        noncontrolling = get_value(financial_data, 'us-gaap:MinorityInterest', period_end)
        if parent is not None and noncontrolling is not None:
            equity = parent + noncontrolling

    temporary = get_value(financial_data, 'us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests', period_end)
    if temporary is None:
        parent = get_value(financial_data, 'us-gaap:TemporaryEquityCarryingAmountAttributableToParent', period_end)
        noncontrolling = get_value(financial_data, 'us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount', period_end)
        if parent is not None and noncontrolling is not None:
            temporary = parent + noncontrolling
    return equity, temporary
