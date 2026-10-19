from value_retrieval.get_value import get_value
from value_retrieval.assets_and_liabilities.temporary_equity.get_redeemable_noncontrolling_equity import get_redeemable_noncontrolling_equity


def get_temporary_equity(financial_data, period_end):
    total = get_value(financial_data, 'us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests', period_end)
    if total is not None:
        return total
    parent = get_value(financial_data, 'us-gaap:TemporaryEquityCarryingAmountAttributableToParent', period_end)
    noncontrolling = get_redeemable_noncontrolling_equity(financial_data, period_end)
    if parent is not None and noncontrolling is not None:
        return parent + noncontrolling
    return None
