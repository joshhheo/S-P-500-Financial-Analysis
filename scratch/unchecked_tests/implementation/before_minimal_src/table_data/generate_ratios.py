"""Extract up to five original annual periods per company, with atomic CSV saves."""
import json
from pathlib import Path

import pandas as pd
from edgar import Company

from value_retrieval.amount import RatioResult
from calculations.debt_to_asset_ratio import evaluate_debt_to_assets
from calculations.interest_coverage_ratio import evaluate_interest_coverage
from setup_sec_identity import setup_sec_identity
from table_data.checks import check_ratios
from value_retrieval.amount import SelectionError
from value_retrieval.source import from_filing

COLUMNS = [
    'ticker', 'fiscal_period_end', 'cik', 'accession', 'fiscal_period_start',
    'debt_to_assets_ratio', 'interest_coverage_ratio',
    'debt_to_assets_status', 'interest_coverage_status', 'extraction_evidence',
]


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

    for index, company in companies.iterrows():
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
                debt = coverage = RatioResult(None, error.code, str(error),
                    dict(accession=filing.accession_no, cik=str(cik)))
            else:
                debt = evaluate_debt_to_assets(source, end)
                try:
                    start = source.annual_start(end)
                except SelectionError as error:
                    coverage = RatioResult(None, error.code, str(error),
                        dict(accession=filing.accession_no, documents=source.documents))
                else:
                    coverage = evaluate_interest_coverage(source, start, end)

            results.append(dict(
                ticker=ticker, fiscal_period_end=end, cik=str(cik),
                accession=filing.accession_no, fiscal_period_start=start,
                debt_to_assets_ratio=debt.value, interest_coverage_ratio=coverage.value,
                debt_to_assets_status=debt.status, interest_coverage_status=coverage.status,
                extraction_evidence=json.dumps(dict(debt_to_assets=debt.serializable(),
                    interest_coverage=coverage.serializable()), separators=(',', ':')),
            ))
            print(f'{ticker} {end}: debt/assets={debt.status}; interest={coverage.status}', flush=True)
            if len(periods) == 5:
                break

        save_csv(results, checkpoint)
        print(f'{index + 1}/{len(companies)} {ticker}: {len(periods)} periods; checkpoint saved', flush=True)

    if not results:
        raise ValueError('No financial rows extracted; completed CSV was not replaced')
    check_ratios(pd.DataFrame(results))
    save_csv(results, Path('data/financial_ratios.csv'))
    print(f'Saved {len(results)} financial rows', flush=True)


if __name__ == '__main__':
    generate_ratios()
