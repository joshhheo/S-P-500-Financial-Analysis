from quick_setup.get_assets_liabilities import get_assets_liabilities


def calculate_debt_to_assets(financial_data, fiscal_period_end):
    values = get_assets_liabilities(financial_data, fiscal_period_end)

    assets = values["assets"]
    liabilities = values["liabilities"]

    if assets is None or liabilities is None:
        return None

    if assets == 0:
        return None

    return liabilities / assets
