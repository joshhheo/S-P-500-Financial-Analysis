"""Permanent and temporary equity definitions and balance-sheet scope checks."""
from value_retrieval.amount import add_amounts, overlaps, select_consistent_amount

INCLUSIVE = 'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'
TEMPORARY = 'us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests'
PARENT_TEMPORARY = 'us-gaap:TemporaryEquityCarryingAmountAttributableToParent'
REDEEMABLE = 'us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount'
COMBINED = 'us-gaap:LiabilitiesAndStockholdersEquity'
CAPTION = 'us-gaap:CommitmentsAndContingencies'
PARENT = 'us-gaap:StockholdersEquity'
MINORITY = 'us-gaap:MinorityInterest'

EQUITY_BRANCHES = {name.removeprefix('us-gaap:') for name in
                   (PARENT, MINORITY, INCLUSIVE, TEMPORARY, PARENT_TEMPORARY, REDEEMABLE)}


SUPPORTED_CONCEPTS = {
    INCLUSIVE, TEMPORARY, PARENT_TEMPORARY, REDEEMABLE, COMBINED, CAPTION,
    PARENT, MINORITY,
}


def get_equity(financial_data, fiscal_period_end):
    """Return permanent and temporary equity separately; missing is not zero."""
    from value_retrieval.get_value import get_instant_value

    equity = get_instant_value(financial_data, INCLUSIVE, fiscal_period_end)
    temporary_equity = get_instant_value(financial_data, TEMPORARY, fiscal_period_end)
    return equity, temporary_equity


def get_equity_amount(financial_data, concept, period_end, period_start=None,
                           currency=None, trail=(), role=None, issues=None):
    from value_retrieval.get_value import get_amount, get_calculated_amounts

    from value_retrieval.get_value import get_reported_amount, calculation_path

    if issues is None:
        issues = set()
    reported = get_reported_amount(
        financial_data, concept, period_end, period_start, currency, issues,
    )
    if reported is not None:
        return reported
    trail = calculation_path(concept, trail, issues)
    if trail is None:
        return None

    # Every component must use this same company, dates, currency and network.
    def get_component(concept):
        return get_amount(
            financial_data, concept, period_end, period_start, currency, trail, role, issues,
        )

    candidates = get_calculated_amounts(
        financial_data, concept, period_end, period_start, currency, trail, role, issues,
    )
    if concept == INCLUSIVE:
        parent_equity = get_component(PARENT)
        noncontrolling_equity = get_component(MINORITY)
        if parent_equity is not None and noncontrolling_equity is not None:
            equity = add_amounts(
                [parent_equity, noncontrolling_equity],
                dict(kind='defined_partition', target=concept),
            )
            candidates.append(equity)
    else:
        parent_temporary_equity = get_component(PARENT_TEMPORARY)
        redeemable_noncontrolling_equity = get_component(REDEEMABLE)
        if parent_temporary_equity is not None and redeemable_noncontrolling_equity is not None:
            temporary_equity = add_amounts(
                [parent_temporary_equity, redeemable_noncontrolling_equity],
                dict(kind='defined_partition', target=concept),
            )
            candidates.append(temporary_equity)
    return select_consistent_amount(candidates, concept)


def equation_applies(financial_data, parent, children, period_end,
                     period_start=None, currency=None, issues=None):
    """A combined balance total must cover disclosed noncontrolling/temporary equity."""
    from value_retrieval.get_value import get_reported_amount

    if parent != COMBINED:
        return True
    if issues is None:
        issues = set()
    names = {name for name, weight in children}
    if PARENT in names and INCLUSIVE not in names and MINORITY not in names:
        minority = get_reported_amount(financial_data, MINORITY, period_end, period_start, currency, issues)
        inclusive = get_reported_amount(financial_data, INCLUSIVE, period_end, period_start, currency, issues)
        parent_equity = get_reported_amount(financial_data, PARENT, period_end, period_start, currency, issues)
        if minority is not None and minority.value != 0:
            issues.add('inapplicable_parent_equity_equation')
            return False
        if inclusive is not None and parent_equity is not None:
            if not overlaps(inclusive, parent_equity):
                issues.add('inapplicable_parent_equity_equation')
                return False

    if not {TEMPORARY, PARENT_TEMPORARY, REDEEMABLE}.intersection(names):
        amounts = []
        for concept in (TEMPORARY, REDEEMABLE, PARENT_TEMPORARY):
            amount = get_reported_amount(financial_data, concept, period_end, period_start, currency, issues)
            amounts.append(amount)
        for amount in amounts:
            if amount is not None and amount.value != 0:
                issues.add('inapplicable_temporary_equity_equation')
                return False
    return True
