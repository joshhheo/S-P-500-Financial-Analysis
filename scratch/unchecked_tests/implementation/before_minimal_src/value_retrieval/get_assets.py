"""Total assets: reported or filed calculations, then defined accounting partitions."""
from value_retrieval.amount import SelectionError, add_amounts, select_consistent_amount
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


def get_assets(financial_data, fiscal_period_end, *, currency=None, audit=None):
    """Return this metric's independently validated value; optionally retain evidence."""
    from value_retrieval.get_value import get_value
    return get_value(financial_data, ASSETS, fiscal_period_end, currency=currency, audit=audit)


def get_asset_amount(financial_data, period_end, period_start=None,
                           currency=None, trail=(), role=None, issues=None):
    """Read total assets, then compare the complete supported fallback results."""
    from value_retrieval.get_value import get_amount, get_calculated_amounts

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

    candidates = get_calculated_amounts(
        financial_data, ASSETS, period_end, period_start, currency, trail, role, issues,
    )

    current_assets = get_component(CURRENT)
    noncurrent_assets = get_component(NONCURRENT)
    if current_assets is not None and noncurrent_assets is not None:
        assets = add_amounts(
            [current_assets, noncurrent_assets],
            dict(kind='defined_partition', target=ASSETS),
        )
        candidates.append(assets)

    # Inside a filed network, stay within that network's components.
    if role is not None:
        return select_consistent_amount(candidates, ASSETS)

    combined = get_reported_amount(
        financial_data, COMBINED, period_end, period_start, currency, issues,
    )
    if combined is None:
        calculated_combined = get_component(COMBINED)
        if calculated_combined is not None:
            candidates.append(calculated_combined)

    liabilities = get_component('us-gaap:Liabilities')
    equity = get_component(INCLUSIVE)
    temporary_equity = get_component(TEMPORARY)
    if liabilities is not None and equity is not None and temporary_equity is not None:
        assets = add_amounts(
            [liabilities, equity, temporary_equity],
            'assets_equals_liabilities_plus_permanent_and_temporary_equity',
        )
        candidates.append(assets)

    # Compare all available derivations; the first result is not necessarily safe.
    return select_consistent_amount(candidates, ASSETS, combined)


def check_balance(financial_data, assets, period_end, currency=None, issues=None):
    from value_retrieval.amount import add_amounts, overlaps, uses_reported
    from value_retrieval.get_value import get_amount, get_reported_amount
    from value_retrieval.get_equity import COMBINED, INCLUSIVE, TEMPORARY

    checks = []
    combined = get_reported_amount(financial_data, COMBINED, period_end, currency=currency, issues=issues)
    if combined is not None and not uses_reported(assets, COMBINED):
        if not overlaps(assets, combined):
            raise SelectionError('Assets do not reconcile to reported liabilities and equity')
        checks.append(dict(check='assets_vs_combined', amount=combined.serializable()))

    liabilities = get_amount(financial_data, 'us-gaap:Liabilities', period_end, currency=currency, issues=issues)
    equity = get_amount(financial_data, INCLUSIVE, period_end, currency=currency, issues=issues)
    temporary_equity = get_amount(financial_data, TEMPORARY, period_end, currency=currency, issues=issues)
    if liabilities is not None and equity is not None and temporary_equity is not None:
        total = add_amounts(
            [liabilities, equity, temporary_equity],
            'independent_balance_identity',
        )
        if not uses_reported(total, ASSETS):
            if not overlaps(assets, total):
                raise SelectionError('Liabilities and equity do not reconcile to assets')
            checks.append(dict(check='balance_identity', amount=total.serializable()))
    return checks
