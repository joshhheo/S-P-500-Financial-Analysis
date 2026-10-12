from value_retrieval.get_assets import get_assets
from value_retrieval.get_liabilities import get_liabilities


def calculate_debt_to_assets(financial_data, fiscal_period_end):
    assets = get_assets(financial_data, fiscal_period_end)
    liabilities = get_liabilities(financial_data, fiscal_period_end)

    if assets is None or liabilities is None:
        return None

    if assets == 0:
        return None

    return liabilities / assets
