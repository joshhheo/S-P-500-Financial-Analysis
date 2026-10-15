"""Operating income or loss; use the reported concept or its filed calculation."""
from value_retrieval.get_value import (
    SelectionError, get_amount, get_value,
)


def get_operating_income(financial_data, period_start, period_end, *, currency=None, issues=None):
    """Return this metric using the first successful supported fallback."""
    if period_start is None:
        raise SelectionError('Required annual start not established', 'ambiguous_period')
    return get_value(financial_data, 'us-gaap:OperatingIncomeLoss', period_end, period_start, currency=currency, issues=issues)


def get_operating_income_amount(financial_data, period_start, period_end, currency=None, issues=None):
    """The operating-income concept needs no additional accounting substitution."""
    return get_amount(
        financial_data, 'us-gaap:OperatingIncomeLoss', period_end, period_start, currency, issues=issues,
    )
