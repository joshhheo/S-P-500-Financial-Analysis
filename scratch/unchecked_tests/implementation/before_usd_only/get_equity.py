"""Retrieve permanent and temporary equity separately."""
from value_retrieval.get_value import (
    get_reported_amount, get_value,
)

def get_equity(financial_data, fiscal_period_end):
    """Return permanent and temporary equity separately; missing is not zero."""

    equity = get_value(financial_data, 'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest', fiscal_period_end)
    temporary_equity = get_value(financial_data, 'us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests', fiscal_period_end)
    return equity, temporary_equity


def derive_equity(financial_data, concept, period_end, period_start=None,
                           currency=None):
    # Every component must use this same company, dates and currency.
    def get_component(concept):
        return get_reported_amount(
            financial_data, concept, period_end, period_start, currency,
        )

    if concept == 'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest':
        parent_equity = get_component('us-gaap:StockholdersEquity')
        noncontrolling_equity = get_component('us-gaap:MinorityInterest')
        if parent_equity is not None and noncontrolling_equity is not None:
            return parent_equity + noncontrolling_equity
    else:
        parent_temporary_equity = get_component('us-gaap:TemporaryEquityCarryingAmountAttributableToParent')
        redeemable_noncontrolling_equity = get_component('us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount')
        if parent_temporary_equity is not None and redeemable_noncontrolling_equity is not None:
            return parent_temporary_equity + redeemable_noncontrolling_equity
    return None
