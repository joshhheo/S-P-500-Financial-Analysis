"""Calculate debt/assets from independently retrieved metric values."""
from decimal import localcontext
from value_retrieval.amount import RatioResult, SelectionError
from value_retrieval.get_liabilities import get_liabilities, LIABILITIES
from value_retrieval.get_assets import get_assets, ASSETS
from value_retrieval.get_value import available_currencies


def evaluate_debt_to_assets(financial_data, period_end):
    try:
        currencies = available_currencies(financial_data, period_end, None, duration=False)
        candidates, availability, issues = [], [], set()
        for currency in currencies:
            audit = {}
            liabilities = get_liabilities(financial_data, period_end, currency=currency, audit=audit)
            assets = get_assets(financial_data, period_end, currency=currency, audit=audit)
            issues.update(audit['issues'])
            availability.append(dict(currency=currency,
                numerator_present=liabilities is not None, denominator_present=assets is not None))
            if liabilities is None or assets is None:
                continue
            numerator = audit['amounts'][LIABILITIES]
            denominator = audit['amounts'][ASSETS]
            if (numerator['currency'], numerator['period']) != (denominator['currency'], denominator['period']):
                raise SelectionError('Ratio operands have incompatible currencies or periods', 'incompatible_basis')
            evidence = dict(numerator=numerator, denominator=denominator,
                accession=financial_data.accession, taxonomy=financial_data.namespace,
                documents=financial_data.documents, reconciliation=audit['checks'], coverage_notes=sorted(issues),
                ratio_policy='28 significant decimal digits, ROUND_HALF_EVEN, disclosed point amounts')
            if assets == 0:
                candidates.append(RatioResult(None, 'zero_denominator',
                    'Division by disclosed zero is undefined', evidence))
                continue
            with localcontext() as context:
                context.prec = 28
                context.rounding = 'ROUND_HALF_EVEN'
                ratio = liabilities / assets
            candidates.append(RatioResult(ratio, 'available', evidence=evidence))
        if len(candidates) > 1:
            return RatioResult(None, 'ambiguous_currency',
                'Multiple complete currency bases without a reporting-currency selection')
        if candidates:
            return candidates[0]
        evidence = dict(accession=financial_data.accession, taxonomy=financial_data.namespace,
            documents=financial_data.documents, currencies_considered=currencies,
            coverage_notes=sorted(issues), numerator_requested=LIABILITIES,
            denominator_requested=ASSETS, availability=availability)
        status = 'incomplete_standard_coverage' if issues else 'missing_required_amount'
        return RatioResult(None, status, 'Required same-basis amounts were not established', evidence)
    except SelectionError as error:
        evidence = {}
        if financial_data is not None and error.code not in ('missing_source', 'ambiguous_period'):
            evidence = dict(accession=financial_data.accession, taxonomy=financial_data.namespace,
                            documents=financial_data.documents)
        return RatioResult(None, error.code, str(error), evidence)


def calculate_debt_to_assets(financial_data, period_end):
    result = evaluate_debt_to_assets(financial_data, period_end)
    if result.value is None and result.reason:
        print(f'Debt/assets unavailable: {result.reason}', flush=True)
    return result.value
