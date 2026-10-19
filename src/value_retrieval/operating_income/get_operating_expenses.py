from value_retrieval.get_value import get_value


def get_operating_expenses(financial_data, period_start, period_end):
    expenses = get_value(financial_data, 'us-gaap:OperatingExpenses', period_end, period_start)
    if expenses is not None:
        return expenses
    total = get_value(financial_data, 'us-gaap:CostsAndExpenses', period_end, period_start)
    cost_of_revenue = get_value(financial_data, 'us-gaap:CostOfRevenue', period_end, period_start)
    if total is not None and cost_of_revenue is not None:
        return total - cost_of_revenue
    other_costs = get_value(financial_data, 'us-gaap:OperatingCostsAndExpenses', period_end, period_start)
    selling_general_administrative = get_value(financial_data, 'us-gaap:SellingGeneralAndAdministrativeExpense', period_end, period_start)
    if other_costs is not None and selling_general_administrative is not None:
        return other_costs + selling_general_administrative
    return None
