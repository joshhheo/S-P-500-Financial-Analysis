"""Reproducible offline selection audit; saves structured results only."""
import ast
import copy
from decimal import Decimal
import json
from pathlib import Path
import sys

from lxml import etree

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(HERE.parent))
from filing_fixtures import financials
from legacy_api import get_reported_value, normalize_concept_name
from legacy_api import liabilities_from_balance_sheet
from test_duplicate_precision import select_consistent_value


def audit():
    targets = set()
    for path in (ROOT / 'src/value_retrieval').glob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value.startswith('us-gaap:') and len(node.value) > 8:
                    targets.add(node.value)
    result = dict(targets=sorted(targets), filings=[], raw_units=[], general_conflicts=[],
                  combined_conflicts=[], reconciliation_failures=[], unresolved_facts=[])
    for path in sorted((HERE.parent / 'extraction_audit').glob('*-*.json')):
        data = json.loads(path.read_text())
        fin = financials(data)
        equations = []
        combined = []
        for target in sorted(targets):
            values = set()
            for role, tree in fin.xb.calculation_trees.items():
                children = []
                for arc in tree.all_arcs:
                    if normalize_concept_name(arc.parent_id) == target:
                        children.append(arc)
                if not children:
                    continue
                for start in (None, data['start']):
                    total = Decimal(0)
                    components = []
                    for arc in children:
                        concept = normalize_concept_name(arc.child_id)
                        amount = get_reported_value(fin, concept, data['end'], start)
                        if amount is None:
                            break
                        total += Decimal(str(arc.weight)) * Decimal(str(amount))
                        components.append(dict(concept=concept, value=str(amount), weight=arc.weight))
                    else:
                        reported = get_reported_value(fin, target, data['end'], start)
                        equations.append(dict(target=target, role=role, start=start, total=str(total),
                                              reported=reported, components=components))
                        values.add((start, total))
            if len(values) > 1:
                result['general_conflicts'].append(dict(filing=path.name, target=target,
                                                        values=sorted(str(v) for v in values)))
        for role, tree in fin.xb.calculation_trees.items():
            isolated = copy.copy(fin)
            isolated.xb = copy.copy(fin.xb)
            isolated.xb.calculation_trees = {role: tree}
            amount = liabilities_from_balance_sheet(isolated, data['end'])
            if amount is None:
                continue
            entry = dict(role=role, liabilities=amount, reported=get_reported_value(fin, 'us-gaap:Liabilities', data['end']))
            total = Decimal(0)
            components = []
            for arc in tree.all_arcs:
                if normalize_concept_name(arc.parent_id) != 'us-gaap:LiabilitiesAndStockholdersEquity':
                    continue
                concept = normalize_concept_name(arc.child_id)
                if concept == 'us-gaap:CommitmentsAndContingencies':
                    continue
                value = get_reported_value(fin, concept, data['end'])
                if value is None:
                    entry['reconciliation'] = 'missing direct component'
                    break
                total += Decimal(str(arc.weight)) * Decimal(str(value))
                components.append(dict(concept=concept, value=str(value), weight=arc.weight))
            else:
                reported = get_reported_value(fin, 'us-gaap:LiabilitiesAndStockholdersEquity', data['end'])
                residual = Decimal(str(reported)) - total
                entry.update(reconciliation='exact' if residual == 0 else 'different',
                             residual=str(residual), components=components)
                if residual:
                    result['reconciliation_failures'].append(dict(filing=path.name, **entry))
            combined.append(entry)
        values = set()
        for equation in combined:
            values.add(equation['liabilities'])
        if len(values) > 1:
            result['combined_conflicts'].append(dict(filing=path.name, values=sorted(values)))
        result['filings'].append(dict(filing=path.name, general_equations=equations, combined_equations=combined))
    for path in sorted(HERE.glob('*-*.json')):
        data = json.loads(path.read_text())
        groups = {}
        units = {}
        for unit, xml in data['units'].items():
            node = etree.fromstring(xml.encode())
            measures = node.xpath('.//*[local-name()="measure"]/text()')
            units[unit] = measures
        for fact in data['facts']:
            key = fact['concept']
            groups.setdefault(key, []).append(fact)
        unit_conflicts = []
        precision_conflicts = []
        duplicates = 0
        for concept, rows in groups.items():
            identifiers = set()
            scopes = {}
            for row in rows:
                identifiers.add(row['unit_ref'])
                key = (row['context_ref'], row['unit_ref'])
                scopes.setdefault(key, []).append(row)
            if len(identifiers) > 1:
                unit_conflicts.append(dict(concept=concept, units=sorted(identifiers)))
            for rows in scopes.values():
                if len(rows) < 2:
                    continue
                duplicates += 1
                try:
                    select_consistent_value(rows)
                except ValueError as error:
                    precision_conflicts.append(dict(concept=concept, error=str(error)))
        target_units = {}
        for target in targets:
            for row in groups.get(target, []):
                target_units.setdefault(target, units[row['unit_ref']])
        result['raw_units'].append(dict(filing=path.name, facts=len(data['facts']), units=units,
                                       target_units=target_units, unit_conflicts=unit_conflicts,
                                       duplicate_groups=duplicates, precision_conflicts=precision_conflicts,
                                       unsupported_transforms=data['unsupported_transforms']))
    (HERE / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    summary = dict(filings=len(result['filings']), raw_filings=len(result['raw_units']),
                   general_conflicts=result['general_conflicts'], combined_conflicts=result['combined_conflicts'],
                   reconciliation_failures=result['reconciliation_failures'])
    for row in result['raw_units']:
        print(row['filing'], 'unit conflicts:', row['unit_conflicts'], 'precision conflicts:', row['precision_conflicts'])
    print(json.dumps(summary, indent=2))
    return result


if __name__ == '__main__':
    audit()
