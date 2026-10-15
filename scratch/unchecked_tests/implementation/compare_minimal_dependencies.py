"""Compare compact dependencies with the previous evidence graphs, offline.

Each archived filing is tested unchanged and with its four target totals hidden.
Hidden facts are constructed mutations, not additional real filing evidence.
Run from the repository root. Child processes import one implementation each.
"""
import copy
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def fingerprint(amount):
    if amount is None:
        return None
    if hasattr(amount, 'sources'):
        dependencies = set(amount.sources)
        direct = amount.direct
    else:
        dependencies = set()
        pending = [amount.evidence]
        while pending:
            node = pending.pop()
            if isinstance(node, dict):
                if node.get('method') == 'reported':
                    dependencies.add(node['concept'])
                pending.extend(node.values())
            elif isinstance(node, list):
                pending.extend(node)
        direct = amount.evidence.get('method') == 'reported'
    return dict(value=str(amount.value), unit=amount.unit, period=amount.period,
                lower=str(amount.lower), upper=str(amount.upper),
                sources=sorted(dependencies), direct=direct)


if len(sys.argv) == 2:
    from filing_fixtures import financials
    from value_retrieval.get_value import retrieve
    from value_retrieval.get_value import SelectionError
    targets = ['Assets', 'Liabilities', 'OperatingIncomeLoss', 'InterestExpense']
    results = []
    for entry in json.loads((HERE / 'instance_manifest.json').read_text()):
        data = json.loads((HERE.parent / 'extraction_audit' /
                           f"{entry['ticker']}-{entry['end']}.json").read_text())
        for hidden in (False, True):
            sample = copy.deepcopy(data)
            if hidden:
                sample['facts'] = [r for r in sample['facts']
                                   if r['concept'] not in {'us-gaap:' + t for t in targets}]
            source = financials(sample)
            for target in targets:
                issues = set()
                audit = {}
                current = 'issues' in inspect.signature(retrieve).parameters
                options = {'issues': issues} if current else {'audit': audit}
                try:
                    amount = retrieve(source, 'us-gaap:' + target, data['end'],
                                      data['start'] if target in targets[2:] else None,
                                      validated=True, **options)
                    result = fingerprint(amount)
                    if not current:
                        issues.update(audit.get('issues', set()))
                except SelectionError as error:
                    result = {'error': error.code}
                results.append(dict(ticker=data['ticker'], end=data['end'], hidden=hidden,
                                    target=target, result=result))
    Path(sys.argv[1]).write_text(json.dumps(results, indent=2) + '\n')
else:
    for label, source in [('before', HERE / 'before_minimal_src'), ('after', ROOT / 'src')]:
        env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(source), str(HERE.parent)]))
        subprocess.run([sys.executable, str(Path(__file__).resolve()),
                        str(HERE / f'minimal_dependencies_{label}.json')], env=env, check=True)
    before = json.loads((HERE / 'minimal_dependencies_before.json').read_text())
    after = json.loads((HERE / 'minimal_dependencies_after.json').read_text())
    differences = [dict(before=a, after=b) for a, b in zip(before, after) if a != b]
    report = dict(comparisons=len(after), differences=differences)
    (HERE / 'minimal_dependencies_comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    assert len(before) == len(after) == 176
    assert not differences, report
    print('176 amount/dependency comparisons unchanged: 88 real, 88 constructed hidden-total cases.')
