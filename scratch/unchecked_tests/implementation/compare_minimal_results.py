"""Compare saved real outputs and verify production CSVs remain untouched."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
before = json.loads((HERE / 'real_before_minimal.json').read_text())
after = json.loads((HERE / 'real_minimal_results.json').read_text())
differences = []
assert len(before) == len(after) == 22
for old, new in zip(before, after):
    assert (old['ticker'], old['end']) == (new['ticker'], new['end'])
    for ratio in ('debt', 'interest'):
        for field in ('value', 'status'):
            if old[ratio][field] != new[ratio][field]:
                differences.append(dict(ticker=new['ticker'], end=new['end'], ratio=ratio,
                                        field=field, before=old[ratio][field], after=new[ratio][field]))
checksums = json.loads((HERE.parent / 'full_review/baseline_hashes.json').read_text())
unchanged_csvs = {}
for filename, expected in checksums.items():
    if filename.startswith('data/'):
        actual = hashlib.sha256((ROOT / filename).read_bytes()).hexdigest()
        assert actual == expected, filename
        unchanged_csvs[filename] = actual
report = dict(filings=22, ratio_values_and_statuses_compared=44, differences=differences,
              production_csv_hashes=unchanged_csvs)
(HERE / 'minimal_results_comparison.json').write_text(json.dumps(report, indent=2) + '\n')
assert not differences, differences
print('All 44 ratio values and statuses unchanged; production CSV hashes unchanged.')
