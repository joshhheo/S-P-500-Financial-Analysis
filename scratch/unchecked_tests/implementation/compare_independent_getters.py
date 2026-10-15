"""Check archived real filings; distinguish added coverage notes from value changes."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
before = json.loads((HERE / 'real_before_independent_getters.json').read_text())
after = json.loads((HERE / 'real_results.json').read_text())
assert len(before) == len(after) == 22
changes = []
for old, new in zip(before, after):
    assert (old['ticker'], old['end'], old['start']) == (new['ticker'], new['end'], new['start'])
    for ratio in ('debt', 'interest'):
        prior, current = old[ratio], new[ratio]
        assert prior['value'] == current['value']
        if prior == current:
            continue
        # The newly independent reconciliation checks the available operand
        # even when its partner is missing. Only coverage metadata may differ.
        assert current['value'] is None
        assert current['status'] == 'incomplete_standard_coverage'
        assert prior['status'] in ('missing_required_amount', 'incomplete_standard_coverage')
        prior_evidence = dict(prior['evidence'])
        current_evidence = dict(current['evidence'])
        prior_notes = prior_evidence.pop('coverage_notes')
        current_notes = current_evidence.pop('coverage_notes')
        assert set(prior_notes) < set(current_notes)
        assert prior_evidence == current_evidence
        assert prior['reason'] == current['reason']
        changes.append(dict(ticker=new['ticker'], end=new['end'], ratio=ratio,
                            previous_status=prior['status'], status=current['status'],
                            added_coverage_notes=sorted(set(current_notes) - set(prior_notes))))
baseline = json.loads((HERE.parent / 'full_review/baseline_hashes.json').read_text())
csvs = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
        for name, expected in baseline.items() if name.startswith('data/')}
assert all(csvs.values())
result = dict(filings_compared=22, all_numeric_values_and_missing_values_unchanged=True,
              all_available_results_including_evidence_identical=True,
              unavailable_result_coverage_changes=changes, production_csvs_unchanged=csvs,
              live_pipeline_run=False, live_database_access=False, network_used=False)
(HERE / 'independent_getter_comparison.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
