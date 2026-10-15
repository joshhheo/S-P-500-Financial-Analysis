
from decimal import localcontext
from value_retrieval.get_liabilities import get_liabilities
from value_retrieval.get_assets import get_assets


def calculate_debt_to_assets(financial_data, period_end):
    liabilities = get_liabilities(financial_data, period_end)
    assets = get_assets(financial_data, period_end)
    if liabilities is None or assets is None:
        return None
    if assets == 0:
        return None
    with localcontext() as context:
        context.prec = 28
        context.rounding = 'ROUND_HALF_EVEN'
        return liabilities / assets
