from value_retrieval.get_value import get_value


def get_partners_equity(financial_data, period_end):
    total = get_value(financial_data, 'us-gaap:PartnersCapitalIncludingPortionAttributableToNoncontrollingInterest', period_end)
    if total is not None:
        return total
    parent = get_value(financial_data, 'us-gaap:PartnersCapital', period_end)
    noncontrolling = get_value(financial_data, 'us-gaap:PartnersCapitalAttributableToNoncontrollingInterest', period_end)
    if parent is not None and noncontrolling is not None:
        return parent + noncontrolling
    return None
