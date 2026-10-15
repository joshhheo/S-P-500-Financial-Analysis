"""Total assets: reported or filed calculations, then defined accounting partitions."""
from value_retrieval.get_value import (
    calculation_path, get_amount, get_calculated_amount, get_reported_amount, get_value,
)


def get_assets(financial_data, fiscal_period_end, *, currency=None, issues=None):
    """Return this metric using the first successful supported fallback."""
    return get_value(financial_data, 'us-gaap:Assets', fiscal_period_end, currency=currency, issues=issues)


def get_asset_amount(financial_data, period_end, period_start=None,
                           currency=None, trail=(), role=None, issues=None):
    """Read total assets, then try supported fallbacks in order."""
    if issues is None:
        issues = set()
    reported = get_reported_amount(
        financial_data, 'us-gaap:Assets', period_end, period_start, currency, issues,
    )
    if reported is not None:
        return reported
    trail = calculation_path('us-gaap:Assets', trail, issues)
    if trail is None:
        return None

    # Every component must use this same company, dates, currency and network.
    def get_component(concept):
        return get_amount(
            financial_data, concept, period_end, period_start, currency, trail, role, issues,
        )

    calculated = get_calculated_amount(
        financial_data, 'us-gaap:Assets', period_end, period_start, currency, trail, role, issues,
    )
    if calculated is not None:
        return calculated

    current_assets = get_component('us-gaap:AssetsCurrent')
    noncurrent_assets = get_component('us-gaap:AssetsNoncurrent')
    if current_assets is not None and noncurrent_assets is not None:
        assets = current_assets + noncurrent_assets
        return assets

    # Inside a filed network, stay within that network's components.
    if role is not None:
        return None

    combined = get_component('us-gaap:LiabilitiesAndStockholdersEquity')
    if combined is not None:
        return combined

    liabilities = get_component('us-gaap:Liabilities')
    equity = get_component('us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest')
    temporary_equity = get_component('us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests')
    if liabilities is not None and equity is not None and temporary_equity is not None:
        assets = liabilities + equity + temporary_equity
        return assets

    return None
