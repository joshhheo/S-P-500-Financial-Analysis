"""Compare frozen results and source size; never run the pipeline or database."""
import hashlib
import json
from pathlib import Path

folder = Path(__file__).resolve().parent
root = folder.parents[2]
before = json.loads((folder / 'real_first_row_results.json').read_text())
after = json.loads((folder / 'real_simplified_results.json').read_text())
assert [(r['ticker'], r['end']) for r in before] == [(r['ticker'], r['end']) for r in after]
changes = [{'before': a, 'after': b} for a, b in zip(before, after) if a != b]
counts = {}
for path in sorted((folder / 'before_simplify_retrieval').glob('*.py')):
    current = root / 'src/value_retrieval' / path.name
    counts[path.name] = {'before': len(path.read_text().splitlines()),
                         'after': len(current.read_text().splitlines())}
baseline = json.loads((folder.parent / 'full_review/baseline_hashes.json').read_text())
unchanged = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() == checksum
             for name, checksum in baseline.items() if name.startswith('data/')}
result = {'filings': len(after), 'ratio_slots': 2 * len(after), 'changes': changes,
          'lines_including_comments_and_blanks': counts, 'production_csvs_unchanged': unchanged}
(folder / 'simplified_comparison.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
