"""Total assets: reported or filed calculations, then defined accounting partitions."""
from value_retrieval.get_value import add_amounts
from value_retrieval.get_equity import COMBINED, INCLUSIVE, TEMPORARY

ASSETS = 'us-gaap:Assets'
CURRENT = 'us-gaap:AssetsCurrent'
NONCURRENT = 'us-gaap:AssetsNoncurrent'


# Reviewed monetary instant concepts. Component tags require a filed equation;
# this list is not a formula and its members must never simply be summed.
SUPPORTED_CONCEPTS = {ASSETS, CURRENT, NONCURRENT} | {
    'us-gaap:Cash',
    'us-gaap:CashAndCashEquivalentsAtCarryingValue',
    'us-gaap:AccountsReceivableNetCurrent',
    'us-gaap:DeferredIncomeTaxAssetsNet',
    'us-gaap:EquityMethodInvestments',
    'us-gaap:FinanceLeaseRightOfUseAsset',
    'us-gaap:FiniteLivedIntangibleAssetsNet',
    'us-gaap:Goodwill',
    'us-gaap:IntangibleAssetsNetExcludingGoodwill',
    'us-gaap:LongTermInvestments',
    'us-gaap:OperatingLeaseRightOfUseAsset',
    'us-gaap:OtherAssetsNoncurrent',
    'us-gaap:PropertyPlantAndEquipmentNet',
}


def get_assets(financial_data, fiscal_period_end, *, currency=None, issues=None):
    """Return this metric using the first successful supported fallback."""
    from value_retrieval.get_value import get_value
    return get_value(financial_data, ASSETS, fiscal_period_end, currency=currency, issues=issues)


def get_asset_amount(financial_data, period_end, period_start=None,
                           currency=None, trail=(), role=None, issues=None):
    """Read total assets, then try supported fallbacks in order."""
    from value_retrieval.get_value import get_amount, get_calculated_amount

    from value_retrieval.get_value import get_reported_amount, calculation_path

    if issues is None:
        issues = set()
    reported = get_reported_amount(
        financial_data, ASSETS, period_end, period_start, currency, issues,
    )
    if reported is not None:
        return reported
    trail = calculation_path(ASSETS, trail, issues)
    if trail is None:
        return None

    # Every component must use this same company, dates, currency and network.
    def get_component(concept):
        return get_amount(
            financial_data, concept, period_end, period_start, currency, trail, role, issues,
        )

    calculated = get_calculated_amount(
        financial_data, ASSETS, period_end, period_start, currency, trail, role, issues,
    )
    if calculated is not None:
        return calculated

    current_assets = get_component(CURRENT)
    noncurrent_assets = get_component(NONCURRENT)
    if current_assets is not None and noncurrent_assets is not None:
        assets = add_amounts([current_assets, noncurrent_assets])
        return assets

    # Inside a filed network, stay within that network's components.
    if role is not None:
        return None

    combined = get_component(COMBINED)
    if combined is not None:
        return combined

    liabilities = get_component('us-gaap:Liabilities')
    equity = get_component(INCLUSIVE)
    temporary_equity = get_component(TEMPORARY)
    if liabilities is not None and equity is not None and temporary_equity is not None:
        assets = add_amounts([liabilities, equity, temporary_equity])
        return assets

    return None
