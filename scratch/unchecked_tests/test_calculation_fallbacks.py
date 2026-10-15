"""Run from the repository root: python -m unittest discover -s scratch/unchecked_tests."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
from edgar.xbrl.models import CalculationArc, CalculationTree

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from legacy_api import get_value
from legacy_api import get_assets
from legacy_api import get_liabilities
from legacy_api import get_interest_expense

END = '2025-12-27'
START = '2024-12-29'


def fact(name, value, **overrides):
    row = dict(concept='us-gaap:' + name, numeric_value=value, unit_ref='usd', decimals='0',
               is_dimensioned=False,
               period_instant=END, period_start=START, period_end=END)
    row.update(overrides)
    return row


def filing(rows, networks=()):
    from filing_fixtures import financials
    return financials(dict(facts=rows, calculations={str(i): [
        dict(parent=p,child=c,weight=w) for p,c,w in network]
        for i,network in enumerate(networks)}))


ASSET_ARCS = [('us-gaap_Assets', 'us-gaap_AssetsCurrent', 1),
              ('us-gaap_Assets', 'us-gaap_AssetsNoncurrent', 1)]


class FallbackTests(unittest.TestCase):
    def test_direct_precedence_and_reported_zero(self):
        for direct in [0, 99]:
            data = filing([fact('Assets', direct), fact('AssetsCurrent', 0),
                           fact('AssetsNoncurrent', direct)], [ASSET_ARCS])
            self.assertEqual(get_value(data, 'us-gaap:Assets', END), direct)

    def test_reported_value_precedes_a_conflicting_filed_sum(self):
        data = filing([fact('Assets', 99), fact('AssetsCurrent', 10),
                       fact('AssetsNoncurrent', 20)], [ASSET_ARCS])
        self.assertEqual(get_assets(data, END), 99)

    def test_weighted_sum_without_descendant_double_counting(self):
        arcs = [('us-gaap_OperatingIncomeLoss','us-gaap_GrossProfit',1),
                ('us-gaap_OperatingIncomeLoss','us-gaap_OperatingExpenses',-1),
                ('us-gaap_GrossProfit','us-gaap_Revenues',1)]
        data = filing([fact('GrossProfit',10),fact('OperatingExpenses',3),fact('Revenues',10)],[arcs])
        self.assertEqual(get_value(data,'us-gaap:OperatingIncomeLoss',END,START),7)

    def test_missing_wrong_scope_period_and_custom(self):
        for overrides in [dict(numeric_value=None), dict(is_dimensioned=True),
                          dict(period_instant='2024-12-28')]:
            data = filing([fact('AssetsCurrent', 10),
                           fact('AssetsNoncurrent', 20, **overrides)], [ASSET_ARCS])
            self.assertIsNone(get_value(data, 'us-gaap:Assets', END))
        data = filing([fact('AssetsCurrent', 10)], [ASSET_ARCS])
        self.assertIsNone(get_value(data, 'us-gaap:Assets', END))
        data = filing([fact('Custom', 10, concept='amd:Custom')],
                      [[('us-gaap_Assets', 'amd_Custom', 1)]])
        self.assertIsNone(get_value(data, 'us-gaap:Assets', END))

    def test_networks_stay_separate_and_later_complete_network_is_used(self):
        a = ASSET_ARCS + [('us-gaap_Assets', 'amd_Missing', 1)]
        b = [('us-gaap_Assets', 'us-gaap_Cash', 1)]
        data = filing([fact('AssetsCurrent', 10), fact('AssetsNoncurrent', 20),
                       fact('Cash', 30)], [a, b])
        self.assertEqual(get_value(data, 'us-gaap:Assets', END), 30)

    def test_duration_matches_both_dates_and_preserves_sign(self):
        arcs = [[('us-gaap_OperatingIncomeLoss', 'us-gaap_Revenues', 1),
                 ('us-gaap_OperatingIncomeLoss', 'us-gaap_OperatingExpenses', -1)]]
        for start, expected in [(START, -5), ('2025-10-01', None)]:
            data = filing([fact('Revenues', 10, period_start=start),
                           fact('OperatingExpenses', 15)], arcs)
            self.assertEqual(get_value(data, 'us-gaap:OperatingIncomeLoss', END, START), expected)

    def test_linkbase_before_fixed_assets_and_fixed_fallback_after_failure(self):
        rows = [fact('AssetsCurrent', 10), fact('AssetsNoncurrent', 20), fact('Cash', 8)]
        data = filing(rows, [[('us-gaap_Assets', 'us-gaap_Cash', 1)]])
        self.assertEqual(get_assets(data, END), 8)
        data = filing(rows, [[('us-gaap_Assets', 'amd_Custom', 1)]])
        self.assertEqual(get_assets(data, END), 30)

    def test_equity_requires_temporary_and_noncontrolling_components(self):
        rows = [fact('Assets', 100), fact('StockholdersEquity', 60)]
        self.assertIsNone(get_liabilities(filing(rows), END))
        rows.append(fact('MinorityInterest', 0))
        self.assertIsNone(get_liabilities(filing(rows), END))
        rows.append(fact('TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests', 5))
        self.assertEqual(get_liabilities(filing(rows), END), 35)

    def test_interest_fixed_fallback_preserves_net_sign_and_needs_both_parts(self):
        rows = [fact('InterestIncomeOperating', 10), fact('InterestIncomeExpenseNet', -2)]
        def interest(rows):
            return get_interest_expense(filing(rows), START, END)
        self.assertIsNone(interest(rows))
        rows.append(fact('InterestExpenseNonoperating', 3))
        self.assertEqual(interest(rows), 15)
        rows.append(fact('InterestExpenseOperating', 4))
        self.assertEqual(interest(rows), 7)

    def test_fixed_component_can_use_linkbase(self):
        rows = [fact('InterestIncomeOperating', 10), fact('InterestIncomeExpenseNet', -2),
                fact('FinanceLeaseInterestExpense', 3)]
        arcs = [[('us-gaap_InterestExpenseNonoperating', 'us-gaap_FinanceLeaseInterestExpense', 1)]]
        result = get_interest_expense(filing(rows, arcs), START, END)
        self.assertEqual(result, 15)


if __name__ == '__main__':
    unittest.main()
