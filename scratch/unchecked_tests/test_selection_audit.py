"""Real constituent evidence plus explicitly altered controls; no live requests."""
import contextlib
import copy
import csv
from decimal import Decimal
import io
import json
from pathlib import Path
import unittest

from selection_audit.analyze import audit
from filing_fixtures import financials
from legacy_api import liabilities_from_balance_sheet
from test_duplicate_precision import select_consistent_value

HERE = Path(__file__).resolve().parent


def fact_interval(rows):
    # Duplicate consistency is established before calculating an uncertainty
    # interval. These are bounds, never invented replacement fact values.
    select_consistent_value(rows)
    lower = Decimal('-Infinity')
    upper = Decimal('Infinity')
    for row in rows:
        accuracy = Decimal(row['decimals'])
        value = Decimal(row['value'])
        radius = Decimal(0)
        if accuracy != Decimal('Infinity'):
            radius = Decimal(10) ** (-accuracy) / 2
        lower = max(lower, value - radius)
        upper = min(upper, value + radius)
    return (lower, upper)


def reconciles(parent, components):
    units = set()
    for row in parent:
        units.add(row['unit_ref'])
    lower = Decimal(0)
    upper = Decimal(0)
    for component in components:
        for row in component:
            units.add(row['unit_ref'])
        interval = fact_interval(component)
        lower += interval[0]
        upper += interval[1]
    if len(units) != 1:
        raise ValueError('Mixed units')
    total = fact_interval(parent)
    return max(lower, total[0]) <= min(upper, total[1])


class SelectionAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with contextlib.redirect_stdout(io.StringIO()):
            cls.results = json.loads((HERE/'selection_audit/results.json').read_text())

    def test_all_real_samples_are_constituents_with_matching_ciks(self):
        members = {}
        with (HERE.parents[1] / 'data/company_status.csv').open() as stream:
            for row in csv.DictReader(stream):
                members[row['ticker']] = int(row['cik'])
        count = 0
        for path in (HERE / 'extraction_audit').glob('*-*.json'):
            data = json.loads(path.read_text())
            self.assertEqual(members[data['ticker']], data['cik'])
            count += 1
        self.assertEqual(count, 22)

    def test_raw_target_units_and_duplicate_consistency(self):
        self.assertEqual(len(self.results['raw_units']), 6)
        for filing in self.results['raw_units']:
            self.assertEqual(filing['unit_conflicts'], [], filing['filing'])
            self.assertEqual(filing['precision_conflicts'], [], filing['filing'])
            for units in filing['target_units'].values():
                self.assertEqual(units, ['iso4217:USD'], filing['filing'])

    def test_broader_equation_scan_identifies_only_berkshire_conflict(self):
        conflicts = self.results['general_conflicts']
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]['filing'], 'BRK-B-2025-12-31.json')
        self.assertEqual(conflicts[0]['target'], 'us-gaap:LiabilitiesAndStockholdersEquity')
        self.assertEqual(len(self.results['combined_conflicts']), 0)
        self.assertEqual(len(self.results['reconciliation_failures']), 0)

    def test_all_ten_real_liability_branch_sums_reconcile(self):
        count = 0
        for filing in self.results['filings']:
            for equation in filing['combined_equations']:
                has_total = False
                for component in equation.get('components', []):
                    if component['concept'] == 'us-gaap:Liabilities':
                        has_total = True
                if has_total:
                    continue
                self.assertEqual(equation['reconciliation'], 'exact')
                count += 1
        self.assertEqual(count, 10)

    def test_offline_reconciliation_detects_change_but_ordered_retrieval_does_not_compare(self):
        data = json.loads((HERE / 'selection_audit/AMD-2025-12-27.json').read_text())
        original = json.loads((HERE / 'extraction_audit/AMD-2025-12-27.json').read_text())
        selected = None
        for filing in self.results['filings']:
            if filing['filing'] == 'AMD-2025-12-27.json':
                selected = filing['combined_equations'][0]
        groups = {}
        for row in data['facts']:
            if row['instant'] == [data['end']]:
                groups.setdefault(row['concept'], []).append(row)
        parent = groups['us-gaap:LiabilitiesAndStockholdersEquity']
        components = []
        for component in selected['components']:
            components.append(groups[component['concept']])
        self.assertTrue(reconciles(parent, components))
        altered = copy.deepcopy(components)
        for row in altered[0]:
            row['value'] = str(Decimal(row['value']) + 1000000000)
        self.assertFalse(reconciles(parent, altered))
        # Constructed alteration: ordered retrieval now returns the changed component sum.
        base = liabilities_from_balance_sheet(financials(original), original['end'])
        for row in original['facts']:
            if row['concept'] == 'us-gaap:LiabilitiesCurrent' and not row['is_dimensioned']:
                if str(row['period_instant'])[:10] == original['end']:
                    row['numeric_value'] += 1000000000
        self.assertEqual(liabilities_from_balance_sheet(financials(original), original['end']),
                         base + 1000000000)
        # A one-million difference is compatible with rounded million-dollar
        # inputs here. This is an altered control, not an observed filing error.
        rounded = copy.deepcopy(parent)
        for row in rounded:
            row['value'] = str(Decimal(row['value']) + 1000000)
        self.assertTrue(reconciles(rounded, components))
