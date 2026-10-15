# unchecked test
from pathlib import Path
import sys

import httpx
from bs4 import BeautifulSoup
from edgar import Company

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from setup_sec_identity import setup_sec_identity
from legacy_api import get_reported_value


def main():
    setup_sec_identity()
    filing = Company(2488).get_filings(
        accession_number='0000002488-26-000018', form='10-K', amendments=False,
    )[0]
    financial_data = filing.obj().financials
    response = httpx.get(
        'https://ir.amd.com/financial-information/sec-filings/content/'
        '0000002488-26-000018/amd-20251227.htm',
        follow_redirects=True, timeout=60,
    )
    response.raise_for_status()
    html = BeautifulSoup(response.text, 'html.parser')

    # These are the liability rows reviewed in THIS filing, not a universal list.
    components = [
        'LiabilitiesCurrent', 'LongTermDebtNoncurrent',
        'OperatingLeaseLiabilityNoncurrent', 'DeferredIncomeTaxLiabilitiesNet',
        'OtherLiabilitiesNoncurrent',
    ]
    for end in ['2025-12-27', '2024-12-28']:
        print(f'\nAMD {end}')
        nil_rows = []
        for tag in html.find_all(attrs={'name': 'us-gaap:CommitmentsAndContingencies'}):
            context = financial_data.xb.contexts[tag['contextref']]
            if context.period.get('instant') != end or context.dimensions:
                continue
            if str(context.entity['identifier']).lstrip('0') != '2488':
                continue
            row = tag.find_parent('tr').get_text(' ', strip=True)
            print(f"Commitments entry: xsi:nil={tag.get('xsi:nil')}; row={row}")
            nil_rows.append(tag.get('xsi:nil') == 'true' and 'see Note 12' in row)
        assert nil_rows and all(nil_rows)

        values = []
        for concept in components:
            value = get_reported_value(financial_data, 'us-gaap:' + concept, end)
            assert value is not None, f'Missing {concept}'
            print(f'  {concept}: {value:,.0f}')
            values.append(value)
        total = sum(values)
        assets = get_reported_value(financial_data, 'us-gaap:Assets', end)
        equity = get_reported_value(financial_data, 'us-gaap:StockholdersEquity', end)
        combined = get_reported_value(financial_data, 'us-gaap:LiabilitiesAndStockholdersEquity', end)
        assert total + equity == combined == assets
        print(f'Liability rows: {total:,.0f}; assets minus equity: {assets - equity:,.0f}')
        print(f'Liabilities/assets: {total / assets:.10f}')
        print('PASS: reviewed liability rows plus equity reconcile to the reported total.')
    print('\nPASS: raw nil-caption and component reconciliation checks completed.')


if __name__ == '__main__':
    main()
