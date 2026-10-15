"""Production regression checks for equation selection using saved S&P 500 filings."""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from filing_fixtures import financials
from legacy_api import get_liabilities
from legacy_api import get_assets



class EquationSelectionTests(unittest.TestCase):
    def test_same_berkshire_equation_also_affects_asset_fallback(self):
        path = Path(__file__).with_name('extraction_audit') / 'BRK-B-2025-12-31.json'
        data = json.loads(path.read_text())
        retained = []
        for row in data['facts']:
            if row['concept'] not in ('us-gaap:Assets', 'us-gaap:LiabilitiesAndStockholdersEquity'):
                retained.append(row)
        data['facts'] = retained
        fin = financials(data)
        self.assertEqual(get_assets(fin, data['end']), 1222176000000)
        fin.audit_source.equations = dict(reversed(list(fin.audit_source.equations.items())))
        self.assertEqual(get_assets(fin, data['end']), 1222176000000)

    def test_berkshire_hidden_liabilities_are_independent_of_calculation_role_order(self):
        path = Path(__file__).with_name("extraction_audit") / "BRK-B-2025-12-31.json"
        data = json.loads(path.read_text())
        self.assertEqual(get_liabilities(financials(data), data["end"]), 502473000000)

        hidden = copy.deepcopy(data)
        hidden["facts"] = []
        for fact in data["facts"]:
            if fact["concept"] != "us-gaap:Liabilities":
                hidden["facts"].append(fact)
        self.assertEqual(get_liabilities(financials(hidden), hidden["end"]), 502473000000)

        # Same facts and equations: put the condensed disclosure network first.
        role = "http://www.berkshirehathaway.com/20251231/taxonomy/role/Role_DisclosureCondensedFinancialInformationBalanceSheetsDetail"
        fin = financials(hidden)
        trees = fin.audit_source.equations
        reordered = dict(sorted(trees.items(),key=lambda item: role not in item[0][0]))
        fin.audit_source.equations = reordered
        # Parent-only equity no longer contributes a misleading candidate.
        self.assertEqual(get_liabilities(fin, hidden["end"]), 502473000000)

        # With the direct reported amount present, network order has no effect.
        direct = financials(data)
        direct.audit_source.equations = reordered
        self.assertEqual(get_liabilities(direct, data["end"]), 502473000000)

    def test_targeted_filter_preserves_saved_results_with_and_without_direct_liabilities(self):
        count = 0
        folder = Path(__file__).with_name('extraction_audit')
        for path in folder.glob('*.json'):
            data = json.loads(path.read_text())
            if not isinstance(data, dict) or 'calculations' not in data or 'end' not in data:
                continue
            for hide_direct in (False, True):
                sample = copy.deepcopy(data)
                if hide_direct:
                    sample['facts'] = []
                    for row in data['facts']:
                        if row['concept'] != 'us-gaap:Liabilities':
                            sample['facts'].append(row)
                fin = financials(sample)
                expected = get_liabilities(financials(data), data['end'])
                fin.audit_source.equations = dict(reversed(list(fin.audit_source.equations.items())))
                self.assertEqual(get_liabilities(fin, sample['end']), expected, path.name)
                count += 1
        self.assertEqual(count, 44)
