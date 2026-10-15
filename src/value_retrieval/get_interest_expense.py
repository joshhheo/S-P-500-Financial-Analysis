from value_retrieval.get_value import get_value


def get_interest_expense(financial_data, period_start, period_end):
    if period_start is None:
        return None
    total = get_value(financial_data, 'us-gaap:InterestExpense', period_end, period_start)
    if total is not None:
        return total
    operating = get_value(financial_data, 'us-gaap:InterestExpenseOperating', period_end, period_start)
    if operating is None:
        income = get_value(financial_data, 'us-gaap:InterestIncomeOperating', period_end, period_start)
        net = get_value(financial_data, 'us-gaap:InterestIncomeExpenseNet', period_end, period_start)
        if income is not None and net is not None:
            operating = income - net
    nonoperating = get_value(financial_data, 'us-gaap:InterestExpenseNonoperating', period_end, period_start)
    if operating is not None and nonoperating is not None:
        return operating + nonoperating
    return None
