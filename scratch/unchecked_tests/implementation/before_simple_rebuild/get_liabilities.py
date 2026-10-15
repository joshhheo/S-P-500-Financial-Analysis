"""Total liabilities and the reviewed liability branches of a balance sheet."""
from value_retrieval.get_value import (
    get_value,
)
def get_liabilities(financial_data, fiscal_period_end):
    """Return this metric using the first successful supported fallback."""
    return get_value(financial_data, 'us-gaap:Liabilities', fiscal_period_end)


def derive_liabilities(financial_data, period_end, period_start=None,
                                trail=()):
    """Explicit accounting identities with all inputs required."""
    # Every component must use this same company, dates and USD basis.
    def get_component(concept):
        return get_value(
            financial_data, concept, period_end, period_start, trail,
        )

    current_liabilities = get_component('us-gaap:LiabilitiesCurrent')
    noncurrent_liabilities = get_component('us-gaap:LiabilitiesNoncurrent')
    if current_liabilities is not None and noncurrent_liabilities is not None:
        return current_liabilities + noncurrent_liabilities

    assets = get_component('us-gaap:Assets')
    equity = get_component('us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest')
    temporary_equity = get_component('us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests')
    if assets is not None and equity is not None and temporary_equity is not None:
        return assets - equity - temporary_equity
    return None
