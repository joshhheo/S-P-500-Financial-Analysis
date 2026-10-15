"""Offline experiment: SEC section 9.10 selection, not production behavior."""
from decimal import Decimal
from itertools import permutations
import json
from pathlib import Path
import unittest


def select_consistent_value(rows):
    # This experiment requires identical context/unit IDs. A general consumer
    # must compare equivalent contexts/units before applying this numeric rule.
    if not rows:
        return None
    scope = None
    values_by_precision = {}
    lower = Decimal('-Infinity')
    upper = Decimal('Infinity')
    best_precision = Decimal('-Infinity')
    selected = None
    for row in rows:
        row_scope = (row['concept'], row['context_ref'], row['unit_ref'])
        if scope is not None and row_scope != scope:
            raise ValueError('Different concepts, contexts, or units')
        scope = row_scope
        if row.get('decimals') is None:
            raise ValueError('Missing accuracy metadata')
        precision = Decimal(row['decimals'])
        value = Decimal(row['value'])
        if not value.is_finite():
            raise ValueError('Nonfinite value')
        if precision in values_by_precision:
            if values_by_precision[precision] != value:
                raise ValueError('Different values with equal accuracy')
        values_by_precision[precision] = value
        radius = Decimal(0)
        if precision != Decimal('Infinity'):
            radius = Decimal(10) ** (-precision) / 2
        lower = max(lower, value - radius)
        upper = min(upper, value + radius)
        if precision > best_precision:
            best_precision = precision
            selected = value
    if lower > upper:
        raise ValueError('Inconsistent rounding intervals')
    return selected


def fact(value, decimals):
    return dict(concept='us-gaap:Assets', context_ref='same', unit_ref='usd',
                value=str(value), decimals=decimals)


class DuplicatePrecisionTests(unittest.TestCase):
    def test_installed_edgartools_preserves_different_precision(self):
        import pandas as pd
        from edgar.xbrl.facts import _deduplicate_facts
        rows = [fact('15500000000', '-8'), fact('15477000000', '-6')]
        frame = _deduplicate_facts(pd.DataFrame(rows))
        self.assertEqual(len(frame), 2)
        self.assertEqual(select_consistent_value(frame.to_dict('records')), Decimal('15477000000'))

    def test_original_apple_tags_in_every_order(self):
        path = Path(__file__).with_name('duplicate_precision_evidence.json')
        groups = {}
        for row in json.loads(path.read_text())['facts']:
            key = (row['concept'], row['context_ref'], row['unit_ref'])
            groups.setdefault(key, []).append(row)
        duplicates = 0
        differing = 0
        expected = {'us-gaap:UnrecognizedTaxBenefits': Decimal('15477000000'),
                    'us-gaap:DebtInstrumentCarryingAmount': Decimal('118063000000')}
        for key, rows in groups.items():
            if len(rows) < 2:
                continue
            duplicates += 1
            selected = select_consistent_value(rows)
            values = set()
            for row in rows:
                values.add(Decimal(row['value']))
            if len(values) > 1:
                differing += 1
                self.assertEqual(selected, expected[key[0]])
            for ordering in permutations(rows):
                self.assertEqual(select_consistent_value(ordering), selected)
        self.assertEqual(duplicates, 17)
        self.assertEqual(differing, 2)

    def test_equal_accuracy_conflict_even_when_intervals_touch(self):
        with self.assertRaises(ValueError):
            select_consistent_value([fact(100, '0'), fact(101, '0')])

    def test_inconsistent_different_accuracy(self):
        with self.assertRaises(ValueError):
            select_consistent_value([fact(100, '-1'), fact(120, '0')])

    def test_negative_zero_and_exact_values(self):
        self.assertEqual(select_consistent_value([fact(-100, '-1'), fact(-103, '0')]), -103)
        self.assertEqual(select_consistent_value([fact(0, '-1'), fact(1, 'INF')]), 1)

    def test_inclusive_boundary(self):
        self.assertEqual(select_consistent_value([fact(100, '-1'), fact('105', 'INF')]), Decimal('105'))

    def test_all_intervals_must_overlap(self):
        with self.assertRaises(ValueError):
            select_consistent_value([fact(100, '-2'), fact(60, '-1'), fact(140, '0')])

    def test_missing_metadata_and_mixed_units_are_not_ranked(self):
        with self.assertRaises(ValueError):
            select_consistent_value([fact(100, None)])
        other = fact(100, '0')
        other['unit_ref'] = 'eur'
        with self.assertRaises(ValueError):
            select_consistent_value([fact(100, '0'), other])
