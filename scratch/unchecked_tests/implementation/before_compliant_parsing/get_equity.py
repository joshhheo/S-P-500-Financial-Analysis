"""Permanent and temporary equity definitions and balance-sheet scope checks."""
from decimal import Decimal, InvalidOperation, localcontext
from value_retrieval.get_value import (
    get_amount, get_reported_amount, get_value, get_reported_fact, decimal_value,
)

def get_equity(financial_data, fiscal_period_end):
    """Return permanent and temporary equity separately; missing is not zero."""

    equity = get_value(financial_data, 'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest', fiscal_period_end)
    temporary_equity = get_value(financial_data, 'us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests', fiscal_period_end)
    return equity, temporary_equity


def derive_equity(financial_data, concept, period_end, period_start=None,
                           currency=None, trail=(), role=None):
    # Every component must use this same company, dates, currency and network.
    def get_component(concept):
        return get_amount(
            financial_data, concept, period_end, period_start, currency, trail, role,
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


def equation_applies(financial_data, parent, children, period_end,
                     period_start=None, currency=None):
    """A combined balance total must cover disclosed noncontrolling/temporary equity."""

    if parent != 'us-gaap:LiabilitiesAndStockholdersEquity':
        return True
    names = {name for name, weight in children}
    if 'us-gaap:StockholdersEquity' in names and 'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest' not in names and 'us-gaap:MinorityInterest' not in names:
        minority = get_reported_amount(financial_data, 'us-gaap:MinorityInterest', period_end, period_start, currency)
        inclusive = reported_interval(financial_data, 'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest', period_end, period_start, currency)
        parent_equity = reported_interval(financial_data, 'us-gaap:StockholdersEquity', period_end, period_start, currency)
        if minority is not None and minority != 0:
            return False
        if inclusive is not None and parent_equity is not None:
            if max(inclusive[1], parent_equity[1]) > min(inclusive[2], parent_equity[2]):
                return False

    if not {'us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests', 'us-gaap:TemporaryEquityCarryingAmountAttributableToParent', 'us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount'}.intersection(names):
        for concept in ('us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests', 'us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount', 'us-gaap:TemporaryEquityCarryingAmountAttributableToParent'):
            amount = get_reported_amount(financial_data, concept, period_end, period_start, currency)
            if amount is not None and amount != 0:
                return False
    return True


def accuracy_interval(value, decimals):
    if decimals is None:
        return None
    try:
        accuracy = Decimal(str(decimals))
    except InvalidOperation:
        return None
    if accuracy.is_infinite() and not accuracy.is_signed():
        return value, value, accuracy
    if not accuracy.is_finite() or accuracy != accuracy.to_integral_value() or abs(accuracy) > 1000:
        return None
    with localcontext() as context:
        context.prec = 2200
        radius = Decimal(10) ** (-accuracy) / 2
        return value - radius, value + radius, accuracy


def reported_interval(financial_data, concept, period_end, period_start, currency):
    """Rounding matters only when comparing the two reported equity scopes."""
    fact = get_reported_fact(financial_data, concept, period_end, period_start, currency)
    if fact is None:
        return None
    value = decimal_value(fact['value'])
    if value is None:
        return None
    interval = accuracy_interval(value, fact['decimals'])
    if interval is None:
        return None
    lower, upper, _ = interval
    return value, lower, upper
