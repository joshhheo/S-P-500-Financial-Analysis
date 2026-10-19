from value_retrieval.get_value import get_value
from value_retrieval.operating_income.get_operating_revenue import get_operating_revenue


def get_gross_profit(financial_data, period_start, period_end):
    profit = get_value(financial_data, 'us-gaap:GrossProfit', period_end, period_start)
    if profit is not None:
        return profit
    revenue = get_operating_revenue(financial_data, period_start, period_end)
    costs = get_value(financial_data, 'us-gaap:CostOfRevenue', period_end, period_start)
    if revenue is not None and costs is not None:
        return revenue - costs
    return None
