"""Regression checks using the 22 saved filing extracts; no network or DB writes."""
from decimal import Decimal
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from filing_fixtures import financials
from legacy_api import get_assets
from legacy_api import get_liabilities, liabilities_from_balance_sheet
from legacy_api import calculate_debt_to_assets
from legacy_api import calculate_interest_coverage
from test_calculation_fallbacks import fact, filing, START, END



class FilingRatioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = [json.loads(p.read_text()) for p in
                    sorted((ROOT / "scratch/unchecked_tests/extraction_audit").glob("*-*.json"))]
        assert len(cls.data) == 22

    def test_all_saved_filings_and_hidden_liability_controls(self):
        recovered = {
            "AMD": [4922000000, 12830000000, 11993000000, 11658000000, 13927000000],
            "WMT": [152969000000, 159206000000, 161828000000, 163131000000, 178488000000],
        }
        counts = {"AMD": 0, "WMT": 0}
        interest_count = 0
        for d in self.data:
            with self.subTest(ticker=d["ticker"], end=d["end"]):
                fin = financials(d)
                assets = get_assets(fin, d["end"])
                liabilities = get_liabilities(fin, d["end"])
                if d["ticker"] in recovered:
                    expected = recovered[d["ticker"]][counts[d["ticker"]]]
                    counts[d["ticker"]] += 1
                    self.assertEqual(liabilities, expected)
                else:
                    expected = liabilities
                    self.assertIsNotNone(expected)
                self.assertEqual(calculate_debt_to_assets(fin, d["end"]),
                                 expected / assets)
                hidden = copy.deepcopy(d)
                hidden["facts"] = [f for f in hidden["facts"]
                                   if f["concept"] != "us-gaap:Liabilities"]
                self.assertEqual(get_liabilities(financials(hidden), d["end"]), expected)
                ratio = calculate_interest_coverage(fin, d["start"], d["end"])
                if d["ticker"] in {"AMD", "AAPL", "MSFT", "WMT"}:
                    if ratio is not None:
                        interest_count += 1
                    if d["ticker"] == "WMT" or (d["ticker"] == "AAPL" and d["end"][:4] >= "2024") or (d["ticker"] == "MSFT" and d["end"][:4] >= "2025"):
                        self.assertIsNone(ratio)
        self.assertEqual(interest_count, 11)

    def test_missing_branch_can_be_solved_but_custom_and_caption_cannot_be_guessed(self):
        source = next(d for d in self.data if d["ticker"] == "WMT" and d["end"] == "2026-01-31")
        for change in ["missing_equity", "missing_liability", "missing_caption", "numeric_caption", "custom", "unknown_standard", "wrong_date", "dimensioned"]:
            with self.subTest(change=change):
                d = copy.deepcopy(source)
                removed = {"missing_equity": "RedeemableNoncontrollingInterestEquityCarryingAmount", "missing_liability": "FinanceLeaseLiabilityNoncurrent", "missing_caption": "CommitmentsAndContingencies"}.get(change)
                if removed:
                    d["facts"] = [f for f in d["facts"] if f["concept"] != "us-gaap:" + removed]
                for f in d["facts"]:
                    if change == "numeric_caption" and f["concept"] == "us-gaap:CommitmentsAndContingencies":
                        f["numeric_value"] = 1
                    if f["concept"] == "us-gaap:FinanceLeaseLiabilityNoncurrent":
                        if change == "wrong_date": f["period_instant"] = "2000-01-01"
                        if change == "dimensioned": f["is_dimensioned"] = True
                if change in {"custom", "unknown_standard"}:
                    for arcs in d["calculations"].values():
                        for a in arcs:
                            if a["child"] == "us-gaap:FinanceLeaseLiabilityNoncurrent":
                                a["child"] = "wmt:Unreviewed" if change == "custom" else "us-gaap:Unreviewed"
                actual=calculate_debt_to_assets(financials(d), d["end"])
                if change in {"missing_equity","missing_liability","wrong_date","dimensioned"}:
                    # One absent component is independently solvable from the
                    # reported combined total and every remaining component.
                    self.assertEqual(actual,Decimal(178488000000)/Decimal(284668000000))
                else:
                    self.assertIsNone(actual)

    def test_zero_denominators_negative_income_and_missing_annual_start(self):
        self.assertIsNone(calculate_debt_to_assets(filing([fact("Assets", 0), fact("Liabilities", 2)]), END))
        for expense, expected in [(0, None), (2, -3)]:
            data = filing([fact("OperatingIncomeLoss", -6), fact("InterestExpense", expense)])
            self.assertEqual(calculate_interest_coverage(data, START, END), expected)
            self.assertIsNone(calculate_interest_coverage(data, None, END))

    def test_current_only_needs_an_actual_complete_equation(self):
        data = filing([fact("Assets", 100), fact("LiabilitiesCurrent", 20)])
        self.assertIsNone(calculate_debt_to_assets(data, END))
        data = filing([fact("Assets", 100), fact("LiabilitiesCurrent", 20)],
                      [[("us-gaap_Liabilities", "us-gaap_LiabilitiesCurrent", 1)]])
        self.assertEqual(calculate_debt_to_assets(data, END), Decimal("0.2"))

    def test_combined_equation_works_without_presentation_trees(self):
        for ticker, expected in [("AMD", 13927000000), ("WMT", 178488000000)]:
            for data in self.data:
                if data["ticker"] != ticker:
                    continue
                if data["end"] not in ["2025-12-27", "2026-01-31"]:
                    continue
                with self.subTest(ticker=ticker):
                    fin = financials(data)
                    self.assertFalse(hasattr(fin.xb, "presentation_trees"))
                    self.assertEqual(liabilities_from_balance_sheet(fin, data["end"]), expected)

    def test_combined_equation_still_requires_total_weights_and_both_categories(self):
        rows = [fact("LiabilitiesAndStockholdersEquity", 100),
                fact("LiabilitiesCurrent", 60), fact("StockholdersEquity", 40)]
        arcs = [("us-gaap_LiabilitiesAndStockholdersEquity", "us-gaap_LiabilitiesCurrent", 1),
                ("us-gaap_LiabilitiesAndStockholdersEquity", "us-gaap_StockholdersEquity", 1)]
        self.assertEqual(liabilities_from_balance_sheet(filing(rows, [arcs]), END), 60)
        self.assertIsNone(liabilities_from_balance_sheet(filing(rows[1:], [arcs]), END))
        self.assertIsNone(liabilities_from_balance_sheet(filing(rows, [arcs[:1]]), END))
        wrong_weight = list(arcs)
        wrong_weight[1] = (arcs[1][0], arcs[1][1], -1)
        self.assertIsNone(liabilities_from_balance_sheet(filing(rows, [wrong_weight]), END))
