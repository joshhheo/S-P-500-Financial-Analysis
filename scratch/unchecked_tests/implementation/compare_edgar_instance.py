"""Compare the previous reader to Edgar-backed extraction on saved SEC documents."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from value_retrieval.source import parse_source

spec = importlib.util.spec_from_file_location('previous_source', HERE / 'source_before_edgar_instance.py')
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
    assert before.__dict__ == after.__dict__, (row['ticker'], row['end'])
    results.append(dict(ticker=row['ticker'], end=row['end'], entire_source_identical=True))
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
(HERE / 'edgar_instance_comparison.json').write_text(json.dumps(result, indent=2) + '\n')
