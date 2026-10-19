from value_retrieval.get_value import get_value


def get_treasury_stock(financial_data, period_end):
    total = get_value(financial_data, 'us-gaap:TreasuryStockValue', period_end)
    if total is not None:
        return total
    common = get_value(financial_data, 'us-gaap:TreasuryStockCommonValue', period_end)
    preferred = get_value(financial_data, 'us-gaap:TreasuryStockPreferredValue', period_end)
    if common is not None and preferred is not None:
        return common + preferred
    return None
