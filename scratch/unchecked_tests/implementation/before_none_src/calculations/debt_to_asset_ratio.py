"""Calculate debt to assets from retrieved values."""
from decimal import localcontext
from value_retrieval.get_liabilities import get_liabilities
from value_retrieval.get_assets import get_assets
from value_retrieval.get_value import SelectionError


def calculate_debt_to_assets(financial_data, period_end, *, currency, issues=None):
    liabilities = get_liabilities(financial_data, period_end, currency=currency, issues=issues)
    assets = get_assets(financial_data, period_end, currency=currency, issues=issues)
    if liabilities is None or assets is None:
        return None
    if assets == 0:
        raise SelectionError('Division by zero', 'zero_denominator')
    with localcontext() as context:
        context.prec = 28
        context.rounding = 'ROUND_HALF_EVEN'
        return liabilities / assets
