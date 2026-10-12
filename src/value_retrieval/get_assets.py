from value_retrieval.get_value import get_instant_value
from value_retrieval.get_equity import get_equity
from value_retrieval.get_liabilities import get_liabilities_before_equity

# retrieve assets without depending on liabilities, preventing fallback cycles
def get_assets_before_equity(financial_data, fiscal_period_end):
    assets = get_instant_value(financial_data, "us-gaap:Assets", fiscal_period_end)
    if assets is None:
        current = get_instant_value(financial_data, "us-gaap:AssetsCurrent", fiscal_period_end)
        noncurrent = get_instant_value(financial_data, "us-gaap:AssetsNoncurrent", fiscal_period_end)
        if current is not None and noncurrent is not None:
            assets = current + noncurrent
    if assets is None:
        assets = get_instant_value(
            financial_data, "us-gaap:LiabilitiesAndStockholdersEquity", fiscal_period_end
        )
    return assets


def get_assets(financial_data, fiscal_period_end):
    assets = get_assets_before_equity(financial_data, fiscal_period_end)
    if assets is None:
        liabilities = get_liabilities_before_equity(financial_data, fiscal_period_end)
        equity_values = get_equity(financial_data, fiscal_period_end)
        equity = equity_values[0]
        temporary_equity = equity_values[1]
        if liabilities is not None and equity is not None and temporary_equity is not None:
            assets = liabilities + equity + temporary_equity
    return assets
