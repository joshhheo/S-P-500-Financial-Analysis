"""Helpers retained only for historical audit entry points."""
from value_retrieval.get_value import (
    get_calculated_amount, get_value, get_reported_amount, available_currencies,
)
from value_retrieval.get_assets import get_assets
from value_retrieval.get_liabilities import get_liabilities, liabilities_from_balance_sheet as balance_liabilities
from value_retrieval.get_equity import get_equity
from value_retrieval.get_interest_expense import get_interest_expense
from value_retrieval.get_operating_income import get_operating_income
from value_retrieval.get_value import decimal_value
from calculations.debt_to_asset_ratio import calculate_debt_to_assets as debt_formula
from calculations.interest_coverage_ratio import calculate_interest_coverage as interest_formula


def liabilities_from_balance_sheet(financial_data, period_end):
    if financial_data is None:
        return None
    source = financial_data
    currencies = available_currencies(source, period_end)
    if currencies is None:
        return None
    amounts = []
    for currency in currencies:
        amount = get_calculated_amount(source, 'us-gaap:Liabilities', period_end, currency=currency, trail=('us-gaap:Liabilities',))
        if amount is None:
            amount = balance_liabilities(source, period_end, currency=currency, trail=('us-gaap:Liabilities',))
        if amount is not None:
            amounts.append(amount)
    if len(amounts) > 1:
        return None
    return amounts[0] if amounts else None


def select_reported_amount(matches, concept, period_end):
    rows = matches.to_dict('records')
    for row in rows:
        row['value'] = row.get('exact_value', row['numeric_value'])
    if not rows or len({row.get('unit_ref') for row in rows}) != 1:
        return None
    return decimal_value(rows[0]['value'])


# Historical scalar tests use the pipeline's currency selection boundary.
from table_data.generate_ratios import filing_ratio

def calculate_debt_to_assets(source, end):
    return filing_ratio(debt_formula, source, end)[0]


def calculate_interest_coverage(source, start, end):
    return filing_ratio(interest_formula, source, start, end)[0]


def normalize_concept_name(concept):
    return concept.replace('us-gaap_', 'us-gaap:', 1)


def get_reported_value(source, concept, end, start=None):
    if source is None:
        return None
    amounts = []
    for currency in available_currencies(source, end, start) or []:
        amount = get_reported_amount(source, concept, end, start, currency)
        if amount is not None:
            amounts.append(amount)
    if len(amounts) > 1:
        return None
    return amounts[0] if amounts else None
