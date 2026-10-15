"""Offline comparison for the compliant-input parsing simplification."""
import hashlib
import json
from pathlib import Path

folder = Path(__file__).resolve().parent
before = json.loads((folder / 'real_source_simplified_results.json').read_text())
after = json.loads((folder / 'real_compliant_parsing_results.json').read_text())
assert [(r['ticker'], r['end']) for r in before] == [(r['ticker'], r['end']) for r in after]
root = folder.parents[2]
baseline = json.loads((folder.parent / 'full_review/baseline_hashes.json').read_text())
result = {'filings': len(after), 'ratio_slots': 2 * len(after),
          'changes': [{'before': a, 'after': b} for a, b in zip(before, after) if a != b],
          'production_csvs_unchanged': {
              name: hashlib.sha256((root / name).read_bytes()).hexdigest() == checksum
              for name, checksum in baseline.items() if name.startswith('data/')}}
(folder / 'compliant_parsing_comparison.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
