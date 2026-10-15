"""Exercise selection rules through production retrieval and ratio boundaries."""
from decimal import Decimal
from value_retrieval.source import period_type
import contextlib
import copy
import io
import json
from pathlib import Path
import unittest

from test_calculation_fallbacks import fact, filing, ASSET_ARCS, END, START
from legacy_api import get_value, get_reported_value
from legacy_api import calculate_debt_to_assets
from legacy_api import calculate_interest_coverage
from test_duplicate_precision import select_consistent_value


class ProductionSelectionTests(unittest.TestCase):
    def test_refreshed_standard_duplicate_groups_through_production(self):
        count = 0
        folder = Path(__file__).with_name('selection_audit')
        for path in folder.glob('*-*.json'):
            data = json.loads(path.read_text())
            groups = {}
            for row in data['facts']:
                if period_type(row['concept']):
                    key = (row['concept'], row['context_ref'], row['unit_ref'])
                    groups.setdefault(key, []).append(row)
            for originals in groups.values():
                if len(originals) < 2:
                    continue
                rows = []
                for original in originals:
                    rows.append(fact(original['concept'].removeprefix('us-gaap:'), original['value'],
                                     unit_ref=original['unit_ref'], decimals=original['decimals'],
                                     period_instant=original['instant'][0] if original['instant'] else None,
                                     period_start=original['start'][0] if original['start'] else None,
                                     period_end=original['end'][0] if original['end'] else None))
                start = originals[0]['start'][0] if originals[0]['start'] else None
                select_consistent_value(originals)  # Independently verify these real duplicates agree.
                for order in (rows, list(reversed(rows))):
                    self.assertEqual(get_reported_value(filing(order), originals[0]['concept'], data['end'], start), Decimal(str(order[0]['numeric_value'])))
                count += 1
        self.assertEqual(count, 56)  # Frozen groups within the explicit metric allowlist.

    def test_original_apple_unreviewed_concept_stays_excluded(self):
        data = json.loads(Path(__file__).with_name('duplicate_precision_evidence.json').read_text())
        rows = []
        for original in data['facts']:
            if original['concept'] == 'us-gaap:UnrecognizedTaxBenefits':
                rows.append(fact('UnrecognizedTaxBenefits', original['value'],
                                 unit_ref=original['unit_ref'], decimals=original['decimals']))
        self.assertEqual(len(rows), 2)
        for order in (rows, list(reversed(rows))):
            # This real concept remains outside metric coverage.
            self.assertIsNone(get_reported_value(filing(order), 'us-gaap:UnrecognizedTaxBenefits', END))

    def test_conflict_detection_is_outside_the_compliant_source_assumption(self):
        rows = [fact('Assets', 100), fact('Assets', 110),
                fact('AssetsCurrent', 10), fact('AssetsNoncurrent', 20), fact('Liabilities', 15)]
        fin = filing(rows, [ASSET_ARCS])
        self.assertEqual(get_value(fin, 'us-gaap:Assets', END), 100)
        self.assertEqual(calculate_debt_to_assets(fin, END), Decimal('0.15'))

    def test_first_fact_accuracy_is_used_without_comparing_later_facts(self):
        for decimals in ('-1', None):
            rows = [fact('Assets', 100, decimals=decimals), fact('Assets', 120, decimals='0')]
            self.assertEqual(get_value(filing(rows), 'us-gaap:Assets', END),
                             100)

    def test_equal_amounts_are_safe_but_different_units_are_not_duplicates(self):
        rows = [fact('Assets', 100, decimals=None), fact('Assets', 100, decimals=None)]
        self.assertEqual(get_value(filing(rows), 'us-gaap:Assets', END), 100)
        for row in rows: row['decimals']='0'
        rows[1]['unit_ref'] = 'eur'
        self.assertIsNone(get_value(filing(rows), 'us-gaap:Assets', END))

    def test_first_complete_equation_precedes_later_equations_and_fixed_formula(self):
        rows = [fact('AssetsCurrent', 10), fact('AssetsNoncurrent', 20),
                fact('Cash', 8), fact('Liabilities', 5)]
        other = [('us-gaap_Assets', 'us-gaap_Cash', 1)]
        for networks, expected in [([ASSET_ARCS, other], 30), ([other, ASSET_ARCS], 8)]:
            fin = filing(rows, networks)
            self.assertEqual(get_value(fin, 'us-gaap:Assets', END), expected)
            from decimal import Decimal, localcontext
            with localcontext() as context:
                context.prec = 28
                self.assertEqual(calculate_debt_to_assets(fin, END), Decimal(5) / expected)

    def test_matching_equations_are_allowed(self):
        rows = [fact('AssetsCurrent', 10), fact('AssetsNoncurrent', 20), fact('Cash', 30)]
        other = [('us-gaap_Assets', 'us-gaap_Cash', 1)]
        self.assertEqual(get_value(filing(rows, [ASSET_ARCS, other]), 'us-gaap:Assets', END), 30)

    def test_filed_balance_sheet_partition_precedes_current_noncurrent_identity(self):
        rows = [fact('Assets', 100), fact('LiabilitiesAndStockholdersEquity', 100),
                fact('StockholdersEquity', 40), fact('MinorityInterest', 0),
                fact('TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests', 0),
                fact('LiabilitiesCurrent', 60), fact('LiabilitiesNoncurrent', 50)]
        first = [('us-gaap_LiabilitiesAndStockholdersEquity', 'us-gaap_LiabilitiesCurrent', 1),
                 ('us-gaap_LiabilitiesAndStockholdersEquity', 'us-gaap_StockholdersEquity', 1)]
        second = copy.deepcopy(first)
        second[0] = ('us-gaap_LiabilitiesAndStockholdersEquity', 'us-gaap_LiabilitiesNoncurrent', 1)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(get_value(filing(rows, [first, second]), 'us-gaap:Liabilities', END), 60)

    def test_duration_duplicates_also_use_first_reported_value(self):
        rows = [fact('Assets', 100), fact('Liabilities', 50),
                fact('OperatingIncomeLoss', 30), fact('OperatingIncomeLoss', 40), fact('InterestExpense', 5)]
        fin = filing(rows)
        self.assertEqual(calculate_debt_to_assets(fin, END), .5)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(calculate_interest_coverage(fin, START, END), 6)
        from table_data.generate_ratios import filing_ratio
        from calculations.interest_coverage_ratio import calculate_interest_coverage as formula
        self.assertEqual(filing_ratio(formula, fin, START, END), (Decimal(6), 'available'))

    def test_first_row_is_selected_only_after_all_basis_filters(self):
        from value_retrieval.get_value import get_reported_amount
        source = filing([fact('Assets', 100)])
        valid = source.records[0]
        excluded = [dict(valid, value='999', **change) for change in (
            {'concept': 'us-gaap:Liabilities'},
            {'entity_identifier': '999999'},
            {'period_instant': '2020-12-31'},
            {'is_dimensioned': True},
            {'unit_ref': 'eur'},
        )]
        source.units['eur'] = 'EUR'
        source.records = excluded + [valid, dict(valid, value='100')]
        self.assertEqual(get_reported_amount(source, 'us-gaap:Assets', END,
                                            currency='USD'), 100)
