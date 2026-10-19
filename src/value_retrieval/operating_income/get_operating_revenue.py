from value_retrieval.get_value import get_value


def get_operating_revenue(financial_data, period_start, period_end):
    revenue = get_value(financial_data, 'us-gaap:Revenues', period_end, period_start)
    if revenue is not None:
        return revenue
    revenue = get_value(financial_data, 'us-gaap:RegulatedAndUnregulatedOperatingRevenue', period_end, period_start)
    if revenue is not None:
        return revenue
    regulated = get_value(financial_data, 'us-gaap:RegulatedOperatingRevenue', period_end, period_start)
    unregulated = get_value(financial_data, 'us-gaap:UnregulatedOperatingRevenue', period_end, period_start)
    if regulated is not None and unregulated is not None:
        return regulated + unregulated
    return None
