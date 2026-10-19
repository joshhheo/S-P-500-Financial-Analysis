from value_retrieval.get_value import get_value
from value_retrieval.assets_and_liabilities.get_equity import get_equity
from value_retrieval.assets_and_liabilities.get_temporary_equity import get_temporary_equity

# stops feedback loop of assets and liabilities
def get_liabilities_before_equity(financial_data, period_end):
    liabilities = get_value(financial_data, 'us-gaap:Liabilities', period_end)
    if liabilities is not None:
        return liabilities
    current = get_value(financial_data, 'us-gaap:LiabilitiesCurrent', period_end)
    noncurrent = get_value(financial_data, 'us-gaap:LiabilitiesNoncurrent', period_end)
    if current is not None and noncurrent is not None:
        return current + noncurrent
    return None


def get_liabilities(financial_data, period_end):
    from value_retrieval.get_assets import get_assets_before_equity

    liabilities = get_liabilities_before_equity(financial_data, period_end)
    if liabilities is not None:
        return liabilities
    assets = get_assets_before_equity(financial_data, period_end)
    net_assets = get_value(financial_data, 'us-gaap:AssetsNet', period_end)
    if assets is not None and net_assets is not None:
        return assets - net_assets
    equity = get_equity(financial_data, period_end)
    temporary = get_temporary_equity(financial_data, period_end)
    if assets is not None and equity is not None and temporary is not None:
        return assets - equity - temporary
    return None
