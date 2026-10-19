from value_retrieval.get_value import get_value
from value_retrieval.interest_expense.get_operating_net_interest import get_operating_net_interest


def get_net_interest(financial_data, period_start, period_end):
    total = get_value(financial_data, 'us-gaap:InterestRevenueExpenseNet', period_end, period_start)
    if total is not None:
        return total
    operating = get_operating_net_interest(financial_data, period_start, period_end)
    nonoperating = get_value(financial_data, 'us-gaap:InterestIncomeExpenseNonoperatingNet', period_end, period_start)
    if operating is not None and nonoperating is not None:
        return operating + nonoperating
    return None
