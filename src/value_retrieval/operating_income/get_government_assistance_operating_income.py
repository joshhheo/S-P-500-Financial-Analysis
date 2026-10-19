from value_retrieval.get_value import get_value


def get_government_assistance_operating_income(financial_data, period_start, period_end):
    operating = get_value(financial_data, 'us-gaap:GovernmentAssistanceOperatingIncome', period_end, period_start)
    if operating is not None:
        return operating
    total = get_value(financial_data, 'us-gaap:GovernmentAssistanceAmount', period_end, period_start)
    nonoperating = get_value(financial_data, 'us-gaap:GovernmentAssistanceNonoperatingIncome', period_end, period_start)
    if total is not None and nonoperating is not None:
        return total - nonoperating
    return None
