"""Operating income or loss; use the reported concept."""
from value_retrieval.get_value import (
    get_value,
)


def get_operating_income(financial_data, period_start, period_end):
    """Return this metric using the first successful supported fallback."""
    if period_start is None:
        return None
    return get_value(financial_data, 'us-gaap:OperatingIncomeLoss', period_end, period_start)
