from value_retrieval.get_value import get_value
from value_retrieval.interest_expense.get_operating_interest_income import get_operating_interest_income


def get_nonoperating_interest_expense(financial_data, period_start, period_end):
    expense = get_value(financial_data, 'us-gaap:InterestExpenseNonoperating', period_end, period_start)
    if expense is not None:
        return expense
    total_income = get_value(financial_data, 'us-gaap:InterestIncomeOperatingAndNonoperating', period_end, period_start)
    operating_income = get_operating_interest_income(financial_data, period_start, period_end)
    net = get_value(financial_data, 'us-gaap:InterestIncomeExpenseNonoperatingNet', period_end, period_start)
    if total_income is not None and operating_income is not None and net is not None:
        return total_income - operating_income - net
    return None
