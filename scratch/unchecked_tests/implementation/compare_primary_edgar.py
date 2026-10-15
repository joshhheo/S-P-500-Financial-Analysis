"""Compare the previous reader to Edgar-backed extraction on saved SEC documents."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from value_retrieval.source import parse_source, period_type

spec = importlib.util.spec_from_file_location('previous_primary_source', HERE / 'source_before_primary_edgar.py')
previous = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = previous
spec.loader.exec_module(previous)

results = []
for row in json.loads((HERE / 'instance_manifest.json').read_text()):
    saved = json.loads((HERE.parent / 'extraction_audit' / f"{row['ticker']}-{row['end']}.json").read_text())
    documents = row['documents']
    instance = next(doc for doc in documents if doc['file'].endswith('_htm.xml'))
    content = (HERE / instance['file']).read_bytes()
    calculations = [(HERE / doc['file']).read_bytes() for doc in documents if doc is not instance]
    args = dict(cik=saved['cik'], accession=row['accession'], documents=documents)
    before = previous.parse_source(content, calculations, **args)
    after = parse_source(content, calculations, **args)
    required_dei = {'dei:DocumentType', 'dei:DocumentFiscalPeriodFocus',
                    'dei:DocumentPeriodEndDate', 'dei:EntityReportingCurrencyISOCode'}
    expected_records = [fact for fact in before.records
                        if period_type(fact['concept'], before.year) or fact['concept'] in required_dei]
    # Only the reviewed concepts are now carried into selection. Unit dictionaries
    # can contain unused nonmonetary units from Edgar; compare referenced units.
    # Edgar groups duplicate occurrences; record ordering is not financial meaning.
    fingerprint = lambda records: Counter(json.dumps(fact, sort_keys=True) for fact in records)
    assert fingerprint(expected_records) == fingerprint(after.records), (row['ticker'], row['end'], 'facts')
    for fact in expected_records:
        if period_type(fact['concept'], before.year):
            unit = fact['unit_ref']
            assert before.units.get(unit) == after.units.get(unit), (row['ticker'], unit)
    for field in ('year', 'cik', 'equations', 'accession', 'documents', 'calculation_issue'):
        assert getattr(before, field) == getattr(after, field), (row['ticker'], field)
    results.append(dict(ticker=row['ticker'], end=row['end'], all_selection_inputs_identical=True,
                        fact_order_changed=expected_records != after.records))
    print(row['ticker'], row['end'], 'identical', flush=True)

before_results = json.loads((HERE / 'real_before_barebones.json').read_text())
after_results = json.loads((HERE / 'real_results.json').read_text())
assert before_results == after_results
baseline = json.loads((HERE.parent / 'full_review/baseline_hashes.json').read_text())
csvs = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
        for name, expected in baseline.items() if name.startswith('data/')}
assert all(csvs.values())
result = dict(filings=results, full_ratio_results_identical=True,
              production_csvs_unchanged=csvs, live_pipeline_run=False,
              live_database_access=False, network_used=False)
(HERE / 'primary_edgar_comparison.json').write_text(json.dumps(result, indent=2) + '\n')
