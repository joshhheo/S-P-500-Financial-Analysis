"""Operating income or loss; use the reported concept or its filed calculation."""
OPERATING_INCOME = 'us-gaap:OperatingIncomeLoss'


# These are duration concepts usable through a complete filed equation only.
# Pretax, investment and nonoperating amounts are not operating-income aliases.
SUPPORTED_CONCEPTS = {OPERATING_INCOME} | {
    'us-gaap:Revenues',
    'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax',
    'us-gaap:CostOfRevenue',
    'us-gaap:GrossProfit',
    'us-gaap:OperatingExpenses',
    'us-gaap:GeneralAndAdministrativeExpense',
    'us-gaap:ResearchAndDevelopmentExpense',
    'us-gaap:SellingAndMarketingExpense',
    'us-gaap:NonoperatingIncomeExpense',
    'us-gaap:OtherNonoperatingIncomeExpense',
    'us-gaap:ForeignCurrencyTransactionGainLossBeforeTax',
    'us-gaap:GainLossOnDerivativeInstrumentsNetPretax',
    'us-gaap:GainLossOnInvestments',
    'us-gaap:InvestmentIncomeInterestAndDividend',
    'us-gaap:InvestmentIncomeNet',
    'us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest',
    'us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments',
}


def get_operating_income(financial_data, period_start, period_end, *, currency=None, audit=None):
    """Return this metric's independently validated value; optionally retain evidence."""
    from value_retrieval.get_value import get_value
    if period_start is None:
        from value_retrieval.amount import SelectionError
        raise SelectionError('Required annual start not established', 'ambiguous_period')
    return get_value(financial_data, OPERATING_INCOME, period_end, period_start, currency=currency, audit=audit)


def get_operating_income_amount(financial_data, period_start, period_end, currency=None, issues=None):
    """The operating-income concept needs no additional accounting substitution."""
    from value_retrieval.get_value import get_amount
    return get_amount(
        financial_data, OPERATING_INCOME, period_end, period_start, currency, issues=issues,
    )
