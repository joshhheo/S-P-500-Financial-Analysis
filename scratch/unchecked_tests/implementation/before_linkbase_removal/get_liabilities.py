"""Total liabilities and the reviewed liability branches of a balance sheet."""
from value_retrieval.get_value import (
    calculate_weighted_total, calculation_applies, get_amount, get_reported_amount, get_value, is_blank_caption,
)
P = 'us-gaap:'

LIABILITY_BRANCHES = {
    'Liabilities', 'LiabilitiesCurrent', 'LiabilitiesNoncurrent', 'LongTermDebtNoncurrent',
    'OperatingLeaseLiabilityNoncurrent', 'FinanceLeaseLiabilityNoncurrent',
    'DeferredIncomeTaxLiabilitiesNet', 'DeferredIncomeTaxesAndOtherLiabilitiesNoncurrent',
    'OtherLiabilitiesNoncurrent', 'AccountsPayableCurrent', 'DeferredRevenueNoncurrent',
}

# Classification for filed balance-sheet branches, not an accounting formula.
EQUITY_BRANCHES = {
    'StockholdersEquity', 'MinorityInterest',
    'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
    'TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests',
    'TemporaryEquityCarryingAmountAttributableToParent',
    'RedeemableNoncontrollingInterestEquityCarryingAmount',
}


def get_liabilities(financial_data, fiscal_period_end, *, currency=None):
    """Return this metric using the first successful supported fallback."""
    return get_value(financial_data, 'us-gaap:Liabilities', fiscal_period_end, currency=currency)


def derive_liabilities(financial_data, period_end, period_start=None,
                                currency=None, trail=(), role=None):
    """Filed balance-sheet partitions, then accounting fallbacks."""
    # Every component must use this same company, dates, currency and network.
    def get_component(concept):
        return get_amount(
            financial_data, concept, period_end, period_start, currency, trail, role,
        )

    # This partition also comes from a filed linkbase, so it precedes identities.
    if role is None:
        liabilities = liabilities_from_balance_sheet(
            financial_data, period_end, period_start, currency, trail,
        )
        if liabilities is not None:
            return liabilities

    current_liabilities = get_component('us-gaap:LiabilitiesCurrent')
    noncurrent_liabilities = get_component('us-gaap:LiabilitiesNoncurrent')
    if current_liabilities is not None and noncurrent_liabilities is not None:
        return current_liabilities + noncurrent_liabilities

    if role is not None:
        return None

    assets = get_component('us-gaap:Assets')
    equity = get_component('us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest')
    temporary_equity = get_component('us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests')
    if assets is not None and equity is not None and temporary_equity is not None:
        return assets - equity - temporary_equity
    return None


def liabilities_from_balance_sheet(financial_data, period_end, period_start=None,
                                   currency=None, trail=()):
    """Separate liability and equity branches in a complete combined-total equation."""

    combined = get_reported_amount(
        financial_data, 'us-gaap:LiabilitiesAndStockholdersEquity', period_end, period_start, currency,
    )
    if combined is None:
        return None

    for (role, parent), children in financial_data.equations.items():
        if parent != 'us-gaap:LiabilitiesAndStockholdersEquity':
            continue
        if not calculation_applies(
            financial_data, parent, children, period_end, period_start, currency,
        ):
            continue
        names = {name for name, weight in children}
        if 'us-gaap:Liabilities' in names:
            # The shared one-unknown calculation handles a Liabilities total child.
            continue

        # A subtotal and its components cannot both be counted as separate branches.
        if 'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest' in names and names.intersection({P + 'StockholdersEquity', P + 'MinorityInterest'}):
            continue
        if 'us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests' in names and names.intersection({'us-gaap:TemporaryEquityCarryingAmountAttributableToParent', 'us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount'}):
            continue
        noncurrent_parts = set()
        for name in LIABILITY_BRANCHES:
            if name not in {'Liabilities', 'LiabilitiesCurrent', 'LiabilitiesNoncurrent', 'AccountsPayableCurrent'}:
                noncurrent_parts.add(P + name)
        if 'us-gaap:LiabilitiesNoncurrent' in names and names.intersection(noncurrent_parts):
            continue
        if 'us-gaap:LiabilitiesCurrent' in names and P + 'AccountsPayableCurrent' in names:
            continue

        liability_parts = []
        equity_parts = []
        for child, weight in children:
            if is_blank_caption(financial_data, child, period_end, period_start):
                continue
            name = child.removeprefix(P)
            if name not in LIABILITY_BRANCHES | EQUITY_BRANCHES or weight != 1:
                break
            amount = get_amount(
                financial_data, child, period_end, period_start, currency, trail, role,
            )
            if amount is None:
                break
            if name in LIABILITY_BRANCHES:
                liability_parts.append((weight, amount))
            else:
                equity_parts.append((weight, amount))
        else:
            if not liability_parts or not equity_parts:
                continue
            return calculate_weighted_total(liability_parts)
    return None
