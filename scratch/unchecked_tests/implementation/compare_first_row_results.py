"""Compare archived filing outputs before and after first-row selection."""
import json
from pathlib import Path

folder = Path(__file__).resolve().parent
before = json.loads((folder / 'real_no_issues_results.json').read_text())
after = json.loads((folder / 'real_first_row_results.json').read_text())
assert [(r['ticker'], r['end']) for r in before] == [(r['ticker'], r['end']) for r in after]
changes = [{'before': a, 'after': b} for a, b in zip(before, after) if a != b]
result = {'filings': len(after), 'ratio_slots': 2 * len(after), 'changes': changes}
(folder / 'first_row_comparison.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
