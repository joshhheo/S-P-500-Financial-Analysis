from value_retrieval.get_value import get_value
from value_retrieval.operating_income.get_gross_profit import get_gross_profit
from value_retrieval.operating_income.get_operating_expenses import get_operating_expenses
from value_retrieval.operating_income.get_operating_revenue import get_operating_revenue
from value_retrieval.operating_income.get_government_assistance_operating_income import get_government_assistance_operating_income


def get_operating_income(financial_data, period_start, period_end):
    if period_start is None:
        return None
    income = get_value(financial_data, 'us-gaap:OperatingIncomeLoss', period_end, period_start)
    if income is not None:
        return income

    other = get_value(financial_data, 'us-gaap:OtherOperatingIncomeExpenseNet', period_end, period_start)
    assistance = get_government_assistance_operating_income(financial_data, period_start, period_end)
    if other != 0 or assistance != 0:
        return None

    gross_profit = get_value(financial_data, 'us-gaap:GrossProfit', period_end, period_start)
    expenses = get_value(financial_data, 'us-gaap:OperatingExpenses', period_end, period_start)
    if gross_profit is not None and expenses is not None:
        return gross_profit - expenses

    revenue = get_value(financial_data, 'us-gaap:Revenues', period_end, period_start)
    costs = get_value(financial_data, 'us-gaap:CostsAndExpenses', period_end, period_start)
    if revenue is not None and costs is not None:
        return revenue - costs

    gross_profit = get_gross_profit(financial_data, period_start, period_end)
    expenses = get_operating_expenses(financial_data, period_start, period_end)
    if gross_profit is not None and expenses is not None:
        return gross_profit - expenses
    revenue = get_operating_revenue(financial_data, period_start, period_end)
    if revenue is not None and costs is not None:
        return revenue - costs
    return None
