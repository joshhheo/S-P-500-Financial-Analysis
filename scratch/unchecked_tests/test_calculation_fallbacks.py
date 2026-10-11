"""Run from the repository root: python -m unittest discover -s scratch/tests."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
from edgar.xbrl.models import CalculationArc, CalculationTree

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from quick_setup.get_calculated_value import get_value
from quick_setup.get_assets_liabilities import get_assets_liabilities
from quick_setup.get_operating_income_interest_expense import get_operating_income_interest_expense

END = '2025-12-27'
START = '2024-12-29'


def fact(name, value, **overrides):
    row = dict(concept='us-gaap:' + name, numeric_value=value,
               is_dimensioned=False, entity_identifier='0000002488',
               period_instant=END, period_start=START, period_end=END)
    row.update(overrides)
    return row


def filing(rows, networks=()):
    class Query:
        def by_concept(self, concept, exact):
            assert exact
            self.concept = concept
            return self

        def to_dataframe(self):
            return pd.DataFrame([r for r in rows if r['concept'] == self.concept])

    def query(include_contexts=False):
        assert include_contexts  # The real XBRL API excludes these by default.
        return Query()

    trees = {}
    for index, network in enumerate(networks):
        trees[str(index)] = CalculationTree(
            role_uri=str(index), definition='', root_element_id=network[0][0],
            all_arcs=[CalculationArc(parent_id=p, child_id=c, weight=w)
                      for p, c, w in network],
        )
    return SimpleNamespace(xb=SimpleNamespace(
        query=query, entity_info={'identifier': '2488'}, calculation_trees=trees,
        presentation_trees={}))


ASSET_ARCS = [('us-gaap_Assets', 'us-gaap_AssetsCurrent', 1),
              ('us-gaap_Assets', 'us-gaap_AssetsNoncurrent', 1)]


class FallbackTests(unittest.TestCase):
    def test_direct_precedence_and_reported_zero(self):
        for direct in [0, 99]:
            data = filing([fact('Assets', direct), fact('AssetsCurrent', 10),
                           fact('AssetsNoncurrent', 20)], [ASSET_ARCS])
            self.assertEqual(get_value(data, 'us-gaap:Assets', END), direct)

    def test_weighted_sum_without_descendant_double_counting(self):
        arcs = ASSET_ARCS + [('us-gaap_AssetsCurrent', 'us-gaap_Cash', 1)]
        arcs[1] = ('us-gaap_Assets', 'us-gaap_AssetsNoncurrent', -1)
        data = filing([fact('AssetsCurrent', 10), fact('AssetsNoncurrent', 3),
                       fact('Cash', 6)], [arcs])
        self.assertEqual(get_value(data, 'us-gaap:Assets', END), 7)

    def test_missing_wrong_scope_period_entity_and_custom(self):
        for overrides in [dict(numeric_value=None), dict(is_dimensioned=True),
                          dict(period_instant='2024-12-28'),
                          dict(entity_identifier='1')]:
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
                       fact('Cash', 8)], [a, b])
        self.assertEqual(get_value(data, 'us-gaap:Assets', END), 8)

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
        self.assertEqual(get_assets_liabilities(data, END)['assets'], 8)
        data = filing(rows, [[('us-gaap_Assets', 'amd_Custom', 1)]])
        self.assertEqual(get_assets_liabilities(data, END)['assets'], 30)

    def test_equity_requires_temporary_and_noncontrolling_components(self):
        rows = [fact('Assets', 100), fact('StockholdersEquity', 60)]
        self.assertIsNone(get_assets_liabilities(filing(rows), END)['liabilities'])
        rows.append(fact('MinorityInterest', 0))
        self.assertIsNone(get_assets_liabilities(filing(rows), END)['liabilities'])
        rows.append(fact('TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests', 5))
        self.assertEqual(get_assets_liabilities(filing(rows), END)['liabilities'], 35)

    def test_interest_fixed_fallback_preserves_net_sign_and_needs_both_parts(self):
        rows = [fact('InterestIncomeOperating', 10), fact('InterestIncomeExpenseNet', -2)]
        def interest(rows):
            return get_operating_income_interest_expense(filing(rows), START, END)['interest_expense']
        self.assertIsNone(interest(rows))
        rows.append(fact('InterestExpenseNonoperating', 3))
        self.assertEqual(interest(rows), 15)
        rows.append(fact('InterestExpenseOperating', 4))
        self.assertEqual(interest(rows), 7)

    def test_fixed_component_can_use_linkbase(self):
        rows = [fact('InterestIncomeOperating', 10), fact('InterestIncomeExpenseNet', -2),
                fact('FinanceLeaseInterestExpense', 3)]
        arcs = [[('us-gaap_InterestExpenseNonoperating', 'us-gaap_FinanceLeaseInterestExpense', 1)]]
        result = get_operating_income_interest_expense(filing(rows, arcs), START, END)
        self.assertEqual(result['interest_expense'], 15)


if __name__ == '__main__':
    unittest.main()
