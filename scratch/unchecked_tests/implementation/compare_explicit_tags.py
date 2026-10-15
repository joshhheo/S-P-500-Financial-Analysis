"""Compare saved offline runs; do not run the pipeline or access the database."""
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
before = json.loads((HERE / 'real_before_explicit_tags.json').read_text())
after = json.loads((HERE / 'real_results.json').read_text())
changes = []
assert len(before) == len(after) == 22
for old, new in zip(before, after):
    assert (old['ticker'], old['end']) == (new['ticker'], new['end'])
    for metric in ('debt', 'interest'):
        assert old[metric]['value'] == new[metric]['value']
        assert old[metric]['status'] == new[metric]['status']
        prior = old[metric]['evidence'].get('coverage_notes', [])
        current = new[metric]['evidence'].get('coverage_notes', [])
        if prior != current:
            changes.append(dict(ticker=new['ticker'], end=new['end'], metric=metric,
                                before=prior, after=current))
old_values, new_values = copy.deepcopy(before), copy.deepcopy(after)
for results in (old_values, new_values):
    for row in results:
        for metric in ('debt', 'interest'):
            row[metric]['evidence'].pop('coverage_notes', None)
assert old_values == new_values
baseline = json.loads((HERE.parent / 'full_review/baseline_hashes.json').read_text())
csvs = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
        for name, expected in baseline.items() if name.startswith('data/')}
assert all(csvs.values())
result = dict(filings_compared=22, values_and_statuses_identical=True,
              evidence_identical_except_coverage_notes=True, coverage_note_changes=changes,
              production_csvs_unchanged=csvs, live_pipeline_run=False, live_database_access=False)
(HERE / 'explicit_tags_comparison.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
