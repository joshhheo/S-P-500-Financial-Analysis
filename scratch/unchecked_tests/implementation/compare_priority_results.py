"""Compare the 22 archived filings after enforcing linkbase-before-identities."""
import json
from pathlib import Path

folder = Path(__file__).resolve().parent
before = json.loads((folder / 'real_ordered_results.json').read_text())
after = json.loads((folder / 'real_priority_results.json').read_text())
assert len(before) == len(after) == 22
changes = [dict(before=old, after=new) for old, new in zip(before, after) if old != new]
(folder / 'priority_results_comparison.json').write_text(
    json.dumps(dict(filings=22, ratios=44, changes=changes), indent=2) + '\n')
assert not changes, changes
print('All 44 archived ratio values and statuses unchanged.')
