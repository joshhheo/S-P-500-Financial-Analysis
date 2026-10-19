from value_retrieval.get_value import get_value
from value_retrieval.interest_expense.get_operating_interest_income import get_operating_interest_income
from value_retrieval.interest_expense.get_operating_net_interest import get_operating_net_interest


def get_operating_interest_expense(financial_data, period_start, period_end):
    expense = get_value(financial_data, 'us-gaap:InterestExpenseOperating', period_end, period_start)
    if expense is not None:
        return expense
    income = get_operating_interest_income(financial_data, period_start, period_end)
    net = get_operating_net_interest(financial_data, period_start, period_end)
    if income is not None and net is not None:
        return income - net
    return None
