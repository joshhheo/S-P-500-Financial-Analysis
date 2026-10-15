"""Compare archived real outputs before/after ordered fallbacks; no live pipeline."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
before = json.loads((HERE / 'real_minimal_results.json').read_text())
after = json.loads((HERE / 'real_ordered_results.json').read_text())
changes = []
assert len(before) == len(after) == 22
for old, new in zip(before, after):
    assert (old['ticker'], old['end']) == (new['ticker'], new['end'])
    for ratio in ('debt', 'interest'):
        for field in ('value', 'status'):
            if old[ratio][field] != new[ratio][field]:
                changes.append(dict(ticker=new['ticker'], end=new['end'], ratio=ratio, field=field,
                                    before=old[ratio][field], after=new[ratio][field]))
checksums = json.loads((HERE.parent / 'full_review/baseline_hashes.json').read_text())
for filename, expected in checksums.items():
    if filename.startswith('data/'):
        assert hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() == expected, filename
report = dict(filings=22, ratios=44, changes=changes, production_csvs_unchanged=True)
(HERE / 'ordered_results_comparison.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
