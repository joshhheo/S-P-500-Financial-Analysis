from value_retrieval.get_value import get_value


def get_operating_net_interest(financial_data, period_start, period_end):
    net = get_value(financial_data, 'us-gaap:InterestIncomeExpenseNet', period_end, period_start)
    if net is not None:
        return net
    total = get_value(financial_data, 'us-gaap:InterestRevenueExpenseNet', period_end, period_start)
    nonoperating = get_value(financial_data, 'us-gaap:InterestIncomeExpenseNonoperatingNet', period_end, period_start)
    if total is not None and nonoperating is not None:
        return total - nonoperating
    return None
