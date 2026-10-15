"""Calculate interest coverage from independently retrieved metric values."""
from decimal import localcontext
from value_retrieval.amount import RatioResult, SelectionError
from value_retrieval.get_operating_income import get_operating_income, OPERATING_INCOME
from value_retrieval.get_interest_expense import get_interest_expense, INTEREST_EXPENSE
from value_retrieval.get_value import available_currencies


def evaluate_interest_coverage(financial_data, period_start, period_end):
    try:
        currencies = available_currencies(financial_data, period_end, period_start, duration=True)
        candidates, availability, issues = [], [], set()
        for currency in currencies:
            audit = {}
            operating_income = get_operating_income(financial_data, period_start, period_end, currency=currency, audit=audit)
            interest_expense = get_interest_expense(financial_data, period_start, period_end, currency=currency, audit=audit)
            issues.update(audit['issues'])
            availability.append(dict(currency=currency,
                numerator_present=operating_income is not None, denominator_present=interest_expense is not None))
            if operating_income is None or interest_expense is None:
                continue
            numerator = audit['amounts'][OPERATING_INCOME]
            denominator = audit['amounts'][INTEREST_EXPENSE]
            if (numerator['currency'], numerator['period']) != (denominator['currency'], denominator['period']):
                raise SelectionError('Ratio operands have incompatible currencies or periods', 'incompatible_basis')
            evidence = dict(numerator=numerator, denominator=denominator,
                accession=financial_data.accession, taxonomy=financial_data.namespace,
                documents=financial_data.documents, reconciliation=audit['checks'], coverage_notes=sorted(issues),
                ratio_policy='28 significant decimal digits, ROUND_HALF_EVEN, disclosed point amounts')
            if interest_expense == 0:
                candidates.append(RatioResult(None, 'zero_denominator',
                    'Division by disclosed zero is undefined', evidence))
                continue
            with localcontext() as context:
                context.prec = 28
                context.rounding = 'ROUND_HALF_EVEN'
                ratio = operating_income / interest_expense
            candidates.append(RatioResult(ratio, 'available', evidence=evidence))
        if len(candidates) > 1:
            return RatioResult(None, 'ambiguous_currency',
                'Multiple complete currency bases without a reporting-currency selection')
        if candidates:
            return candidates[0]
        evidence = dict(accession=financial_data.accession, taxonomy=financial_data.namespace,
            documents=financial_data.documents, currencies_considered=currencies,
            coverage_notes=sorted(issues), numerator_requested=OPERATING_INCOME,
            denominator_requested=INTEREST_EXPENSE, availability=availability)
        status = 'incomplete_standard_coverage' if issues else 'missing_required_amount'
        return RatioResult(None, status, 'Required same-basis amounts were not established', evidence)
    except SelectionError as error:
        evidence = {}
        if financial_data is not None and error.code not in ('missing_source', 'ambiguous_period'):
            evidence = dict(accession=financial_data.accession, taxonomy=financial_data.namespace,
                            documents=financial_data.documents)
        return RatioResult(None, error.code, str(error), evidence)


def calculate_interest_coverage(financial_data, period_start, period_end):
    result = evaluate_interest_coverage(financial_data, period_start, period_end)
    if result.value is None and result.reason:
        print(f'Interest coverage unavailable: {result.reason}', flush=True)
    return result.value
