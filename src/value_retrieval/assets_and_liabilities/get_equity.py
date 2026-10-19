from value_retrieval.get_value import get_value
from value_retrieval.assets_and_liabilities.equity.get_partners_equity import get_partners_equity
from value_retrieval.assets_and_liabilities.equity.get_treasury_stock import get_treasury_stock
from value_retrieval.assets_and_liabilities.equity.get_members_equity import get_members_equity


def get_equity(financial_data, period_end):
    equity = get_value(financial_data, 'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest', period_end)
    if equity is not None:
        return equity
    partners = get_value(financial_data, 'us-gaap:PartnersCapitalIncludingPortionAttributableToNoncontrollingInterest', period_end)
    if partners is not None:
        return partners
    members = get_value(financial_data, 'us-gaap:LimitedLiabilityCompanyLlcMembersEquityIncludingPortionAttributableToNoncontrollingInterest', period_end)
    if members is not None:
        return members
    parent = get_value(financial_data, 'us-gaap:StockholdersEquity', period_end)
    noncontrolling = get_value(financial_data, 'us-gaap:MinorityInterest', period_end)
    if parent is not None and noncontrolling is not None:
        return parent + noncontrolling
    partners = get_partners_equity(financial_data, period_end)
    if partners is not None:
        return partners
    # This standard subtotal already includes noncontrolling interests.
    before_treasury = get_value(financial_data, 'us-gaap:StockholdersEquityBeforeTreasuryStock', period_end)
    treasury = get_treasury_stock(financial_data, period_end)
    if before_treasury is not None and treasury is not None:
        return before_treasury - treasury
    return get_members_equity(financial_data, period_end)
