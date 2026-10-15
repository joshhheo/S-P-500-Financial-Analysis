"""Permanent and temporary equity definitions and balance-sheet scope checks."""
from value_retrieval.get_value import (
    calculation_path, get_amount, get_calculated_amount, get_reported_amount, get_value, overlaps,
)

def get_equity(financial_data, fiscal_period_end):
    """Return permanent and temporary equity separately; missing is not zero."""

    equity = get_value(financial_data, 'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest', fiscal_period_end)
    temporary_equity = get_value(financial_data, 'us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests', fiscal_period_end)
    return equity, temporary_equity


def get_equity_amount(financial_data, concept, period_end, period_start=None,
                           currency=None, trail=(), role=None):


    reported = get_reported_amount(
        financial_data, concept, period_end, period_start, currency,
    )
    if reported is not None:
        return reported
    trail = calculation_path(concept, trail)
    if trail is None:
        return None

    # Every component must use this same company, dates, currency and network.
    def get_component(concept):
        return get_amount(
            financial_data, concept, period_end, period_start, currency, trail, role,
        )

    calculated = get_calculated_amount(
        financial_data, concept, period_end, period_start, currency, trail, role,
    )
    if calculated is not None:
        return calculated

    if concept == 'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest':
        parent_equity = get_component('us-gaap:StockholdersEquity')
        noncontrolling_equity = get_component('us-gaap:MinorityInterest')
        if parent_equity is not None and noncontrolling_equity is not None:
            equity = parent_equity + noncontrolling_equity
            return equity
    else:
        parent_temporary_equity = get_component('us-gaap:TemporaryEquityCarryingAmountAttributableToParent')
        redeemable_noncontrolling_equity = get_component('us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount')
        if parent_temporary_equity is not None and redeemable_noncontrolling_equity is not None:
            temporary_equity = parent_temporary_equity + redeemable_noncontrolling_equity
            return temporary_equity
    return None


def equation_applies(financial_data, parent, children, period_end,
                     period_start=None, currency=None):
    """A combined balance total must cover disclosed noncontrolling/temporary equity."""

    if parent != 'us-gaap:LiabilitiesAndStockholdersEquity':
        return True
    names = {name for name, weight in children}
    if 'us-gaap:StockholdersEquity' in names and 'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest' not in names and 'us-gaap:MinorityInterest' not in names:
        minority = get_reported_amount(financial_data, 'us-gaap:MinorityInterest', period_end, period_start, currency)
        inclusive = get_reported_amount(financial_data, 'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest', period_end, period_start, currency)
        parent_equity = get_reported_amount(financial_data, 'us-gaap:StockholdersEquity', period_end, period_start, currency)
        if minority is not None and minority.value != 0:
            return False
        if inclusive is not None and parent_equity is not None:
            if not overlaps(inclusive, parent_equity):
                return False

    if not {'us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests', 'us-gaap:TemporaryEquityCarryingAmountAttributableToParent', 'us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount'}.intersection(names):
        amounts = []
        for concept in ('us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests', 'us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount', 'us-gaap:TemporaryEquityCarryingAmountAttributableToParent'):
            amount = get_reported_amount(financial_data, concept, period_end, period_start, currency)
            amounts.append(amount)
        for amount in amounts:
            if amount is not None and amount.value != 0:
                return False
    return True
