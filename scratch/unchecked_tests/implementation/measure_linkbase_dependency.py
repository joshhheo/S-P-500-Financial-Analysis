"""Offline ablation: same archived facts, with and without filed calculations.

No production writes, network requests, or database access. Disabling equations
also disables their use inside accounting fallbacks, leaving those formulas intact.
"""
import json
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'src'))
from value_retrieval.source import parse_source
from value_retrieval.get_assets import get_assets
from value_retrieval.get_liabilities import get_liabilities
from value_retrieval.get_operating_income import get_operating_income
from value_retrieval.get_interest_expense import get_interest_expense
from calculations.debt_to_asset_ratio import calculate_debt_to_assets
from calculations.interest_coverage_ratio import calculate_interest_coverage
from table_data.generate_ratios import filing_ratio


def values(source, start, end):
    result = {}
    for currency in source.currencies(end, start):
        result[currency] = {
            'assets': get_assets(source, end, currency=currency),
            'liabilities': get_liabilities(source, end, currency=currency),
            'operating_income': get_operating_income(source, start, end, currency=currency),
            'interest_expense': get_interest_expense(source, start, end, currency=currency),
        }
    result['ratios'] = {
        'debt_to_assets': filing_ratio(calculate_debt_to_assets, source, end)[0],
        'interest_coverage': filing_ratio(calculate_interest_coverage, source, start, end)[0],
    }
    return result

rows = []
losses = []
changes = []
for entry in json.loads((HERE / 'instance_manifest.json').read_text()):
    saved = json.loads((HERE.parent / 'extraction_audit' / f"{entry['ticker']}-{entry['end']}.json").read_text())
    documents = entry['documents']
    instance = next(doc for doc in documents if doc['file'].endswith('_htm.xml'))
    source = parse_source((HERE / instance['file']).read_bytes(),
                          [(HERE / doc['file']).read_bytes() for doc in documents if doc is not instance],
                          cik=saved['cik'], accession=entry['accession'], documents=documents)
    start = source.annual_start(entry['end'])
    enabled = values(source, start, entry['end'])
    disabled = values(replace(source, equations={}), start, entry['end'])
    identity = dict(ticker=entry['ticker'], end=entry['end'])
    rows.append(dict(**identity, enabled=enabled, disabled=disabled))
    for basis, metrics in enabled.items():
        for metric, value in metrics.items():
            other = disabled[basis][metric]
            detail = dict(**identity, basis=basis, metric=metric, enabled=value, disabled=other)
            if value is not None and other is None:
                losses.append(detail)
            elif value != other:
                changes.append(detail)
summary = dict(companies=len({r['ticker'] for r in rows}), filings=len(rows),
               companies_losing_values=sorted({r['ticker'] for r in losses}),
               losses=losses, other_changes=changes)
(HERE / 'linkbase_dependency_results.json').write_text(json.dumps(dict(summary=summary, filings=rows), default=str, indent=2) + '\n')
print(json.dumps(summary, default=str, indent=2))
