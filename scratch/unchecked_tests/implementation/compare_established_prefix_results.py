"""Compare archived filing results before and after the explicit prefix policy."""
import json
from pathlib import Path

folder = Path(__file__).resolve().parent
before = json.loads((folder / 'real_simplified_results.json').read_text())
after = json.loads((folder / 'real_established_prefix_results.json').read_text())
assert [(r['ticker'], r['end']) for r in before] == [(r['ticker'], r['end']) for r in after]
result = {'filings': len(after), 'ratio_slots': 2 * len(after),
          'changes': [{'before': a, 'after': b} for a, b in zip(before, after) if a != b]}
(folder / 'established_prefix_comparison.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
