"""Compare complete archived-filing ratio outputs across the responsibility change."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
before = json.loads((HERE / 'real_before_ratio_boundary.json').read_text())
after = json.loads((HERE / 'real_results.json').read_text())
assert len(before) == len(after) == 22
assert before == after, 'A value, status, reason or evidence field changed'
baseline = json.loads((HERE.parent / 'full_review/baseline_hashes.json').read_text())
csvs = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
        for name, expected in baseline.items() if name.startswith('data/')}
assert all(csvs.values())
result = dict(filings_compared=22, complete_ratio_results_identical=True,
              production_csvs_unchanged=csvs, live_pipeline_run=False,
              live_database_access=False, network_used=False)
(HERE / 'ratio_boundary_comparison.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
