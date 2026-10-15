"""Regression tests for defects recorded in the historical review.

All examples below are constructed unless explicitly loaded from a saved filing.
They do not assert that a company filed the constructed values. No live services
are called, and production files are never written.
"""
import contextlib
from decimal import Decimal
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from table_data.generate_ratios import filing_ratio
import os
import tempfile
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from filing_fixtures import financials
from legacy_api import get_value
from legacy_api import get_assets
from legacy_api import get_liabilities
from legacy_api import get_interest_expense
from legacy_api import select_reported_amount
from legacy_api import calculate_debt_to_assets
from legacy_api import calculate_interest_coverage

END = '2025-12-31'
START = '2025-01-01'


def instant(name, amount, unit='USD', decimals='0'):
    return dict(concept='us-gaap:' + name, value=str(amount),
                numeric_value=amount, unit_ref=unit, decimals=decimals,
                is_dimensioned=False, entity_identifier='0000002488',
                context_ref='current_instant', period_instant=END,
                period_start=None, period_end=None)


def duration(name, amount, unit='USD', decimals='0'):
    row = instant(name, amount, unit, decimals)
    row.update(context_ref='current_duration', period_instant=None,
               period_start=START, period_end=END)
    return row


def network(parent, children):
    return [dict(parent='us-gaap:' + parent, child='us-gaap:' + child, weight=weight)
            for child, weight in children]


def sample(rows, *networks):
    return financials(dict(facts=rows, calculations={str(i): arcs for i, arcs in enumerate(networks)}))


class FullReviewTests(unittest.TestCase):
    def test_currency_mismatch_blocks_ratio(self):
        fin = sample([instant('Assets', 100, 'USD'), instant('Liabilities', 50, 'EUR')])
        # USD and EUR are individually legal monetary units, but cannot cancel.
        self.assertIsNone(calculate_debt_to_assets(fin, END))

    def test_currency_mismatch_blocks_sums(self):
        rows = [instant('AssetsCurrent', 40, 'USD'), instant('AssetsNoncurrent', 60, 'EUR')]
        self.assertIsNone(get_assets(sample(rows), END))
        arcs = network('Assets', [('AssetsCurrent', 1), ('AssetsNoncurrent', 1)])
        self.assertIsNone(get_assets(sample(rows, arcs), END))

    def test_distinct_currencies_are_separate_bases(self):
        fin = sample([instant('Assets', 100, 'USD'), instant('Assets', 90, 'EUR'),
                      instant('Liabilities', 50, 'USD')])
        self.assertIsNone(get_assets(fin, END))
        # The ratio can select the one complete compatible currency pair.
        self.assertEqual(calculate_debt_to_assets(fin, END), Decimal("0.5"))

    def test_standard_payables_branch_is_retrieved(self):
        rows = [instant('LiabilitiesAndStockholdersEquity', 100),
                instant('AccountsPayableCurrent', 60),
                instant('StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest', 40)]
        arcs = network('LiabilitiesAndStockholdersEquity', [
            ('AccountsPayableCurrent', 1),
            ('StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest', 1)])
        # The complete supplied equation partitions 100 into liability 60 + equity 40.
        self.assertEqual(get_liabilities(sample(rows, arcs), END), 60)

    def test_temporary_equity_split_is_retrieved(self):
        rows = [instant('Assets', 100),
                instant('StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest', 40),
                instant('TemporaryEquityCarryingAmountAttributableToParent', 10),
                instant('RedeemableNoncontrollingInterestEquityCarryingAmount', 5)]
        # Both portions of temporary equity are explicit. No zero is inferred.
        self.assertEqual(get_liabilities(sample(rows), END), 45)

    def test_complete_nested_standard_equation_is_evaluated(self):
        rows = [duration('RevenueFromContractWithCustomerExcludingAssessedTax', 100),
                duration('CostOfRevenue', 30), duration('OperatingExpenses', 20)]
        arcs = network('OperatingIncomeLoss', [('GrossProfit', 1), ('OperatingExpenses', -1)])
        arcs += network('GrossProfit', [('RevenueFromContractWithCustomerExcludingAssessedTax', 1),
                                        ('CostOfRevenue', -1)])
        self.assertEqual(get_value(sample(rows, arcs), 'us-gaap:OperatingIncomeLoss', END, START), 50)

    def test_filed_inverse_interest_equation_is_solved(self):
        rows = [duration('InterestCostsIncurred', 12), duration('InterestCostsCapitalized', 2)]
        arcs = network('InterestCostsIncurred', [('InterestExpense', 1), ('InterestCostsCapitalized', 1)])
        # A supplied complete semantic relationship gives one unknown: 12 = expense + 2.
        self.assertEqual(get_interest_expense(sample(rows, arcs), START, END), 10)

    def test_first_equation_precedes_later_rounding_compatible_total(self):
        rows = [instant('AssetsCurrent', 50, decimals='-1'),
                instant('AssetsNoncurrent', 50, decimals='-1'),
                instant('CashAndCashEquivalentsAtCarryingValue', 30, decimals='-1'),
                instant('AccountsReceivableNetCurrent', 30, decimals='-1'),
                instant('LiabilitiesAndStockholdersEquity', 105, decimals='0')]
        a = network('Assets', [('AssetsCurrent', 1), ('AssetsNoncurrent', 1)])
        b = network('Assets', [('CashAndCashEquivalentsAtCarryingValue', 1),
                               ('AccountsReceivableNetCurrent', 1), ('AssetsNoncurrent', 1)])
        # Ordered policy returns the first filed sum; it does not reconcile to 105.
        self.assertEqual(get_assets(sample(rows, a, b), END), 100)

    def test_nil_caption_allows_assets_reconstruction(self):
        caption = instant('CommitmentsAndContingencies', None)
        caption.update(value='', numeric_value=None)
        rows = [instant('LiabilitiesCurrent', 60),
                instant('StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest', 40),caption]
        arcs = network('LiabilitiesAndStockholdersEquity', [('LiabilitiesCurrent', 1),
            ('StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest', 1),
            ('CommitmentsAndContingencies', 1)])
        self.assertEqual(get_assets(sample(rows, arcs), END), 100)

    def test_exact_integer_is_preserved(self):
        value = 9007199254740993
        actual = select_reported_amount(pd.DataFrame([instant('Assets', value, decimals='INF')]),
                                        'us-gaap:Assets', END)
        self.assertEqual(actual, Decimal(value))

    def test_annual_context_ambiguity_is_not_resolved_by_order(self):
        from value_retrieval.source import Source
        records=[]
        for start in ('2025-01-01','2024-12-29'):
            for concept,value in [('DocumentType','10-K'),('DocumentFiscalPeriodFocus','FY'),('DocumentPeriodEndDate',END)]:
                records.append(dict(concept='dei:'+concept,value=value,entity_identifier='2488',
                    is_dimensioned=False,period_start=start,period_end=END,context_ref=start))
        for order in (records,list(reversed(records))):
            self.assertIsNone(Source('2026', '2488', order, {}).annual_start(END))

    def test_unavailable_values_share_one_missing_state(self):
        missing = sample([])
        zero = sample([duration('OperatingIncomeLoss', 10), duration('InterestExpense', 0)])
        conflict = sample([duration('OperatingIncomeLoss', 10),
                           duration('InterestExpense', 1), duration('InterestExpense', 2)])
        from calculations.interest_coverage_ratio import calculate_interest_coverage
        results=[filing_ratio(calculate_interest_coverage, fin,START,END) for fin in (missing,zero)]
        self.assertEqual(filing_ratio(calculate_interest_coverage, conflict, START, END),
                         (Decimal(10), 'available'))  # Duplicate conflicts are assumed absent.
        self.assertTrue(all(r[0] is None for r in results))
        self.assertEqual({r[1] for r in results}, {'missing'})
        frame = pd.DataFrame(results, columns=['value', 'status'])
        restored = pd.read_csv(io.StringIO(frame.to_csv(index=False)))
        self.assertTrue(restored['value'].isna().all())
        self.assertEqual(restored['status'].tolist(), [r[1] for r in results])

    def test_none_financials_are_handled(self):
        self.assertIsNone(calculate_debt_to_assets(None, END))
        self.assertIsNone(calculate_interest_coverage(None, START, END))

    def test_real_walmart_independent_balance_reconciliation(self):
        data = json.loads((ROOT / 'scratch/unchecked_tests/extraction_audit/WMT-2026-01-31.json').read_text())
        fin = financials(data)
        total = get_value(fin, 'us-gaap:LiabilitiesAndStockholdersEquity', data['end'])
        equity = get_value(fin, 'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest', data['end'])
        temporary = get_value(fin, 'us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount', data['end'])
        self.assertEqual(get_liabilities(fin, data['end']), 178488000000)
        self.assertEqual(total - equity - temporary, 178488000000)


class AdditionalAccountingControls(unittest.TestCase):
    def test_first_equation_wins_even_when_fixed_sum_differs_within_rounding(self):
        rows=[instant('AssetsCurrent',50,decimals='-1'),instant('AssetsNoncurrent',50,decimals='-1'),
              instant('CashAndCashEquivalentsAtCarryingValue',30,decimals='-1'),
              instant('AccountsReceivableNetCurrent',30,decimals='-1')]
        other=network('Assets',[('CashAndCashEquivalentsAtCarryingValue',1),
            ('AccountsReceivableNetCurrent',1),('AssetsNoncurrent',1)])
        self.assertEqual(get_assets(sample(rows,other),END),110)

    def test_parent_equity_is_not_inclusive_when_reported_totals_differ(self):
        rows=[instant('LiabilitiesAndStockholdersEquity',100),instant('StockholdersEquity',30),
              instant('StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',40)]
        parent=network('LiabilitiesAndStockholdersEquity',[('Liabilities',1),('StockholdersEquity',1)])
        inclusive=network('LiabilitiesAndStockholdersEquity',[('Liabilities',1),
            ('StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',1)])
        self.assertEqual(get_liabilities(sample(rows,parent,inclusive),END),60)

    def test_defined_partition_can_supply_a_nested_standard_component(self):
        rows=[instant('LiabilitiesCurrent',30),instant('LiabilitiesNoncurrent',20),
              instant('StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',50)]
        arcs=network('Assets',[('Liabilities',1),
            ('StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',1)])
        self.assertEqual(get_assets(sample(rows,arcs),END),100)


if __name__ == '__main__':
    unittest.main()
