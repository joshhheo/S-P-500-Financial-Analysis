"""Read annual filings and save ratios; missing values stay blank with a status."""
from pathlib import Path
import pandas as pd
from edgar import Company

from calculations.debt_to_asset_ratio import calculate_debt_to_assets
from calculations.interest_coverage_ratio import calculate_interest_coverage
from setup_sec_identity import setup_sec_identity
from value_retrieval.get_value import SelectionError
from value_retrieval.get_value import available_currencies
from value_retrieval.source import from_filing

COLUMNS = ['ticker', 'fiscal_period_end', 'cik', 'accession', 'fiscal_period_start',
           'debt_to_assets_ratio', 'interest_coverage_ratio',
           'debt_to_assets_status', 'interest_coverage_status']


def filing_ratio(calculate, source, *dates):
    """Try disclosed currencies; accept exactly one complete basis."""
    candidates, issues = [], set()
    try:
        currencies = available_currencies(source, dates[-1], dates[0] if len(dates) == 2 else None,
                                          duration=len(dates) == 2)
        for currency in currencies:
            try:
                value = calculate(source, *dates, currency=currency, issues=issues)
            except SelectionError as error:
                if error.code != 'zero_denominator':
                    raise
                candidates.append((None, error.code))
            else:
                if value is not None:
                    candidates.append((value, 'available'))
    except SelectionError as error:
        return None, error.code
    if len(candidates) > 1:
        return None, 'ambiguous_currency'
    if candidates:
        return candidates[0]
    return None, 'incomplete_standard_coverage' if issues else 'missing_required_amount'


def save_csv(rows, path):
    temporary = path.with_suffix('.tmp')
    pd.DataFrame(rows, columns=COLUMNS).to_csv(temporary, index=False)
    temporary.replace(path)


def generate_ratios():
    setup_sec_identity()
    companies = pd.read_csv('data/company_status.csv')
    results = []
    checkpoint = Path('data/financial_ratios.partial.csv')
    save_csv(results, checkpoint)
    for company in companies.to_dict('records'):
        ticker, cik = company['ticker'], int(company['cik'])
        periods = set()
        for filing in Company(cik).get_filings(form='10-K', amendments=False):
            if not filing.period_of_report:
                continue
            end = str(filing.period_of_report)[:10]
            if end in periods:
                continue
            periods.add(end)
            start = None
            try:
                source = from_filing(filing, cik)
            except SelectionError as error:
                debt, debt_status = coverage, coverage_status = None, error.code
            else:
                debt, debt_status = filing_ratio(calculate_debt_to_assets, source, end)
                try:
                    start = source.annual_start(end)
                except SelectionError as error:
                    coverage, coverage_status = None, error.code
                else:
                    coverage, coverage_status = filing_ratio(calculate_interest_coverage, source, start, end)
            results.append(dict(ticker=ticker, cik=str(cik), accession=filing.accession_no,
                fiscal_period_end=end, fiscal_period_start=start,
                debt_to_assets_ratio=debt, interest_coverage_ratio=coverage,
                debt_to_assets_status=debt_status, interest_coverage_status=coverage_status))
            if len(periods) == 5:
                break
        save_csv(results, checkpoint)
        print(f'{ticker}: saved {len(periods)} periods', flush=True)
    if not results:
        raise ValueError('No financial rows; completed CSV was not replaced')
    save_csv(results, Path('data/financial_ratios.csv'))


if __name__ == '__main__':
    generate_ratios()
