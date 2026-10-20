from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from edgar import Company

from calculations.debt_to_asset_ratio import calculate_debt_to_assets
from calculations.interest_coverage_ratio import calculate_interest_coverage
from setup_sec_identity import setup_sec_identity
from value_retrieval.get_value import get_annual_start

COLUMNS = ['ticker', 'fiscal_period_start', 'fiscal_period_end',
           'debt_to_assets_ratio', 'interest_coverage_ratio']


def get_company_ratios(company):
    results = []
    ticker = company['ticker']
    cik = int(company['cik'])
    periods = []
    for filing in Company(cik).get_filings(form='10-K', amendments=False):
        if not filing.period_of_report:
            continue
        end = str(filing.period_of_report)[:10]
        if end in periods:
            continue
        periods.append(end)
        report = filing.obj()
        if report is not None:
            financials = report.financials
        else:
            financials = None

        if financials is not None:
            source = financials.xb
        else:
            source = None
        start = get_annual_start(source, end)
        debt = calculate_debt_to_assets(source, end)
        coverage = calculate_interest_coverage(source, start, end)
        results.append(dict(ticker=ticker,
            fiscal_period_start=start, fiscal_period_end=end,
            debt_to_assets_ratio=debt, interest_coverage_ratio=coverage))
        if len(periods) == 5:
            break
    print(f'{ticker}: processed {len(periods)} periods', flush=True)
    return results


def generate_ratios():
    setup_sec_identity()
    companies = pd.read_csv('data/company_status.csv')
    results = []
    # rate limit shared with all threads enforced by edgartools HTTP manager
    with ThreadPoolExecutor(max_workers = 3) as executor:
        # get_company_ratios is called by workers, not main thread
        # second parameter is input for the first parameter
        # second parameter is automattically iterated by .map
        # pandas records converts to list of dictionaries
        for company_results in executor.map(get_company_ratios, companies.to_dict('records')):
            # extend adds elements instead of adding a list as a single element
            results.extend(company_results)
    if not results:
        return None
    pd.DataFrame(results, columns=COLUMNS).to_csv('data/financial_ratios.csv', index=False)


if __name__ == '__main__':
    generate_ratios()
