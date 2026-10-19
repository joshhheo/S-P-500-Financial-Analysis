from value_retrieval.get_value import get_value


def get_members_equity(financial_data, period_end):
    equity = get_value(financial_data, 'us-gaap:LimitedLiabilityCompanyLlcMembersEquityIncludingPortionAttributableToNoncontrollingInterest', period_end)
    if equity is not None:
        return equity
    parent = get_value(financial_data, 'us-gaap:MembersEquity', period_end)
    noncontrolling = get_value(financial_data, 'us-gaap:MembersEquityAttributableToNoncontrollingInterest', period_end)
    if parent is not None and noncontrolling is not None:
        return parent + noncontrolling
    return None
