"""Compare the 22 archived filings after removing retrieval issue tracking."""
import json
from pathlib import Path

folder = Path(__file__).resolve().parent
before = json.loads((folder / 'real_baseline_results.json').read_text())
after = json.loads((folder / 'real_no_issues_results.json').read_text())
assert len(before) == len(after) == 22
changes = [dict(before=old, after=new) for old, new in zip(before, after) if old != new]
(folder / 'no_issues_results_comparison.json').write_text(
    json.dumps(dict(filings=22, ratios=44, changes=changes), indent=2) + '\n')
for old, new in zip(before, after):
    assert (old['ticker'], old['end'], old['start']) == (new['ticker'], new['end'], new['start'])
    for ratio in ('debt', 'interest'):
        assert old[ratio]['value'] == new[ratio]['value'], (old, new)
print(f'All 44 ratio values unchanged; {len(changes)} filing status changes recorded.')

import hashlib
root = folder.parents[2]
hashes = json.loads((folder.parent / 'full_review/baseline_hashes.json').read_text())
for name, expected in hashes.items():
    if name.startswith('data/'):
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
print('Production CSV hashes unchanged.')
