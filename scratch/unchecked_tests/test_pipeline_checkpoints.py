"""Offline checks for pipeline diagnostics and saved partial extraction."""
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from table_data.checks import check_companies, check_ratios
from table_data.generate_ratios import generate_ratios


class CheckpointTests(unittest.TestCase):
    def test_duplicate_keys_rejected_but_missing_ratios_allowed(self):
        df = pd.DataFrame([dict(ticker="ABC", fiscal_period_end="2025-12-31",
                                debt_to_assets_ratio=None, interest_coverage_ratio=None)])
        with contextlib.redirect_stdout(io.StringIO()):
            check_ratios(df)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            check_ratios(pd.concat([df, df]))
        df.loc[0, "fiscal_period_end"] = "not-a-date"
        with self.assertRaises(ValueError):
            check_ratios(df)

    def test_empty_company_list_rejected_before_membership_reset(self):
        with self.assertRaises(ValueError):
            check_companies(pd.DataFrame(columns=["ticker", "cik", "company_name", "sector"]))

    def test_interruption_keeps_completed_csv_and_saves_partial_rows(self):
        original_directory = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                Path("data").mkdir()
                Path("data/financial_ratios.csv").write_text("previous completed run\n")
                pd.DataFrame([dict(ticker=t, cik=c, company_name=t, sector="Technology")
                              for t, c in [("AAA", 1), ("BBB", 2)]]).to_csv("data/company_status.csv", index=False)
                financials = SimpleNamespace(xb=SimpleNamespace(reporting_periods=[
                    dict(type="duration", period_type="Annual", start_date="2025-01-01", end_date="2025-12-31")]))
                filing = SimpleNamespace(period_of_report="2025-12-31", obj=lambda: SimpleNamespace(financials=financials))
                company = SimpleNamespace(get_filings=lambda **kwargs: [filing])
                with patch("table_data.generate_ratios.setup_sec_identity"), \
                     patch("table_data.generate_ratios.Company", side_effect=[company, RuntimeError("interrupted")]), \
                     patch("table_data.generate_ratios.calculate_debt_to_assets", return_value=.5), \
                     patch("table_data.generate_ratios.calculate_interest_coverage", return_value=None), \
                     contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(RuntimeError, "interrupted"):
                        generate_ratios()
                self.assertEqual(Path("data/financial_ratios.csv").read_text(), "previous completed run\n")
                partial = pd.read_csv("data/financial_ratios.partial.csv")
                self.assertEqual(partial["ticker"].tolist(), ["AAA"])
                self.assertEqual(partial.loc[0, "debt_to_assets_ratio"], .5)
                self.assertTrue(pd.isna(partial.loc[0, "interest_coverage_ratio"]))
            finally:
                os.chdir(original_directory)
