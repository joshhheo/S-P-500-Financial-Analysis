"""Verify the metric-first cleanup against the saved pre-refactor filing results."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
before = json.loads((HERE / 'real_before_barebones.json').read_text())
after = json.loads((HERE / 'real_results.json').read_text())
assert len(before) == len(after) == 22
assert before == after, 'A value, status or evidence field changed'
baseline = json.loads((HERE.parent / 'full_review/baseline_hashes.json').read_text())
csvs = {}
for name, expected in baseline.items():
    if name.startswith('data/'):
        csvs[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
assert all(csvs.values())
result = dict(
    filings_compared=22, full_results_including_evidence_identical=True,
    production_csvs_unchanged=csvs, live_pipeline_run=False, live_database_access=False,
)
(HERE / 'barebones_comparison.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
