"""Total liabilities and the reviewed liability branches of a balance sheet."""
from value_retrieval.get_value import calculate_weighted_total, add_amounts, subtract_amounts
from value_retrieval.get_equity import (
    COMBINED, INCLUSIVE, TEMPORARY, PARENT_TEMPORARY, REDEEMABLE, EQUITY_BRANCHES,
)

P = 'us-gaap:'
LIABILITIES = P + 'Liabilities'
CURRENT = P + 'LiabilitiesCurrent'
NONCURRENT = P + 'LiabilitiesNoncurrent'

LIABILITY_BRANCHES = {
    'Liabilities', 'LiabilitiesCurrent', 'LiabilitiesNoncurrent', 'LongTermDebtNoncurrent',
    'OperatingLeaseLiabilityNoncurrent', 'FinanceLeaseLiabilityNoncurrent',
    'DeferredIncomeTaxLiabilitiesNet', 'DeferredIncomeTaxesAndOtherLiabilitiesNoncurrent',
    'OtherLiabilitiesNoncurrent', 'AccountsPayableCurrent', 'DeferredRevenueNoncurrent',
}


# Extra components may participate in filed equations; they do not expand the
# separately reviewed balance-sheet branch partition above.
SUPPORTED_CONCEPTS = {P + name for name in LIABILITY_BRANCHES} | {
    'us-gaap:AccruedIncomeTaxesNoncurrent',
    'us-gaap:ContractWithCustomerLiabilityNoncurrent',
}


def get_liabilities(financial_data, fiscal_period_end, *, currency=None, issues=None):
    """Return this metric using the first successful supported fallback."""
    from value_retrieval.get_value import get_value
    return get_value(financial_data, LIABILITIES, fiscal_period_end, currency=currency, issues=issues)


def get_liability_amount(financial_data, period_end, period_start=None,
                                currency=None, trail=(), role=None, issues=None):
    """Read total liabilities, then try supported fallbacks in order."""
    from value_retrieval.get_value import get_amount, get_calculated_amount

    from value_retrieval.get_value import get_reported_amount, calculation_path

    if issues is None:
        issues = set()
    reported = get_reported_amount(
        financial_data, LIABILITIES, period_end, period_start, currency, issues,
    )
    if reported is not None:
        return reported
    trail = calculation_path(LIABILITIES, trail, issues)
    if trail is None:
        return None

    # Every component must use this same company, dates, currency and network.
    def get_component(concept):
        return get_amount(
            financial_data, concept, period_end, period_start, currency, trail, role, issues,
        )

    calculated = get_calculated_amount(
        financial_data, LIABILITIES, period_end, period_start, currency, trail, role, issues,
    )
    if calculated is not None:
        return calculated

    # This partition also comes from a filed linkbase, so it precedes identities.
    if role is None:
        liabilities = liabilities_from_balance_sheet(
            financial_data, period_end, period_start, currency, trail, issues,
        )
        if liabilities is not None:
            return liabilities

    current_liabilities = get_component(CURRENT)
    noncurrent_liabilities = get_component(NONCURRENT)
    if current_liabilities is not None and noncurrent_liabilities is not None:
        liabilities = add_amounts([current_liabilities, noncurrent_liabilities])
        return liabilities

    if role is not None:
        return None

    assets = get_component('us-gaap:Assets')
    equity = get_component(INCLUSIVE)
    temporary_equity = get_component(TEMPORARY)
    if assets is not None and equity is not None and temporary_equity is not None:
        liabilities = subtract_amounts(
            assets, [equity, temporary_equity],
        )
        return liabilities
    return None


def liabilities_from_balance_sheet(financial_data, period_end, period_start=None,
                                   currency=None, trail=(), issues=None):
    """Separate liability and equity branches in a complete combined-total equation."""
    from value_retrieval.get_value import (
        get_amount, get_reported_amount, calculation_applies, is_blank_caption,
    )

    if issues is None:
        issues = set()
    combined = get_reported_amount(
        financial_data, COMBINED, period_end, period_start, currency, issues,
    )
    if combined is None:
        return None

    for (role, parent), children in financial_data.equations.items():
        if parent != COMBINED:
            continue
        if not calculation_applies(
            financial_data, parent, children, period_end, period_start, currency, issues,
        ):
            continue
        names = {name for name, weight in children}
        if LIABILITIES in names:
            # The shared one-unknown calculation handles a Liabilities total child.
            continue

        # A subtotal and its components cannot both be counted as separate branches.
        if INCLUSIVE in names and names.intersection({P + 'StockholdersEquity', P + 'MinorityInterest'}):
            continue
        if TEMPORARY in names and names.intersection({PARENT_TEMPORARY, REDEEMABLE}):
            continue
        noncurrent_parts = set()
        for name in LIABILITY_BRANCHES:
            if name not in {'Liabilities', 'LiabilitiesCurrent', 'LiabilitiesNoncurrent', 'AccountsPayableCurrent'}:
                noncurrent_parts.add(P + name)
        if NONCURRENT in names and names.intersection(noncurrent_parts):
            issues.add('overlapping_liability_branches')
            continue
        if CURRENT in names and P + 'AccountsPayableCurrent' in names:
            issues.add('overlapping_liability_branches')
            continue

        liability_parts = []
        equity_parts = []
        for child, weight in children:
            if is_blank_caption(financial_data, child, period_end, period_start):
                continue
            name = child.removeprefix(P)
            if name not in LIABILITY_BRANCHES | EQUITY_BRANCHES or weight != 1:
                issues.add('unreviewed_balance_branch')
                break
            amount = get_amount(
                financial_data, child, period_end, period_start, currency, trail, role, issues,
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
