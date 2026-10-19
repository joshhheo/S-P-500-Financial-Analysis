"""Compare real archived filings with the frozen linkbase-disabled baseline."""
import json
import math
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'src'))

from edgar.xbrl import XBRL
from value_retrieval.get_value import get_annual_start
from value_retrieval.get_assets import get_assets
from value_retrieval.get_liabilities import get_liabilities
from value_retrieval.get_operating_income import get_operating_income
from value_retrieval.get_interest_expense import get_interest_expense
from calculations.debt_to_asset_ratio import calculate_debt_to_assets
from calculations.interest_coverage_ratio import calculate_interest_coverage


def verify_archived_filings():
    entries = json.loads((HERE / 'fixtures/instance_manifest.json').read_text())
    with zipfile.ZipFile(HERE / 'fixtures/filing_documents.zip') as documents:
        for entry in entries:
            instance = next(document for document in entry['documents']
                            if document['file'].endswith('_htm.xml'))
            source = XBRL()
            source.parser.parse_instance_content(documents.read(instance['file']).decode())
            end = entry['end']
            start = get_annual_start(source, end)
            result = {
                'USD': {
                    'assets': get_assets(source, end),
                    'liabilities': get_liabilities(source, end),
                    'operating_income': get_operating_income(source, start, end),
                    'interest_expense': get_interest_expense(source, start, end),
                },
                'ratios': {
                    'debt_to_assets': calculate_debt_to_assets(source, end),
                    'interest_coverage': calculate_interest_coverage(source, start, end),
                },
            }
            expected = entry['expected_disabled_linkbase_baseline']
            # Preserve the frozen expectations; missing states must match exactly.
            for group, values in result.items():
                for metric, actual in values.items():
                    previous = expected[group][metric]
                    details = (entry['ticker'], end, metric, actual, previous)
                    if actual is None or previous is None:
                        assert actual is None and previous is None, details
                    else:
                        assert math.isclose(actual, float(previous),
                                            rel_tol=1e-12, abs_tol=1e-12), details
    print(f'{len(entries)} archived filings match the frozen disabled-linkbase baseline.')


if __name__ == '__main__':
    verify_archived_filings()
