from value_retrieval.get_value import get_value
from value_retrieval.interest_expense.get_operating_interest_expense import get_operating_interest_expense
from value_retrieval.interest_expense.get_capitalized_interest import get_capitalized_interest
from value_retrieval.interest_expense.get_net_interest import get_net_interest
from value_retrieval.interest_expense.get_nonoperating_interest_expense import get_nonoperating_interest_expense


def get_interest_expense(financial_data, period_start, period_end):
    if period_start is None:
        return None
    total = get_value(financial_data, 'us-gaap:InterestExpense', period_end, period_start)
    if total is not None:
        return total

    operating = get_operating_interest_expense(financial_data, period_start, period_end)
    nonoperating = get_value(financial_data, 'us-gaap:InterestExpenseNonoperating', period_end, period_start)
    if operating is not None and nonoperating is not None:
        return operating + nonoperating

    total_income = get_value(financial_data, 'us-gaap:InterestIncomeOperatingAndNonoperating', period_end, period_start)
    total_net = get_value(financial_data, 'us-gaap:InterestRevenueExpenseNet', period_end, period_start)
    if total_income is not None and total_net is not None:
        return total_income - total_net

    incurred = get_value(financial_data, 'us-gaap:InterestCostsIncurred', period_end, period_start)
    capitalized = get_capitalized_interest(financial_data, period_start, period_end)
    if incurred is not None and capitalized is not None:
        return incurred - capitalized

    net = get_net_interest(financial_data, period_start, period_end)
    if total_income is not None and net is not None:
        return total_income - net
    nonoperating = get_nonoperating_interest_expense(financial_data, period_start, period_end)
    if operating is not None and nonoperating is not None:
        return operating + nonoperating
    return None
