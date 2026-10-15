"""Total assets: reported, then defined accounting partitions."""
from value_retrieval.get_value import (
    get_amount, get_value,
)


def get_assets(financial_data, fiscal_period_end):
    """Return this metric using the first successful supported fallback."""
    return get_value(financial_data, 'us-gaap:Assets', fiscal_period_end)


def derive_assets(financial_data, period_end, period_start=None,
                           trail=()):
    """Accounting fallbacks after reported retrieval failed."""
    # Every component must use this same company, dates and USD basis.
    def get_component(concept):
        return get_amount(
            financial_data, concept, period_end, period_start, trail,
        )

    current_assets = get_component('us-gaap:AssetsCurrent')
    noncurrent_assets = get_component('us-gaap:AssetsNoncurrent')
    if current_assets is not None and noncurrent_assets is not None:
        return current_assets + noncurrent_assets

    combined = get_component('us-gaap:LiabilitiesAndStockholdersEquity')
    if combined is not None:
        return combined

    liabilities = get_component('us-gaap:Liabilities')
    equity = get_component('us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest')
    temporary_equity = get_component('us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests')
    if liabilities is not None and equity is not None and temporary_equity is not None:
        return liabilities + equity + temporary_equity

    return None
