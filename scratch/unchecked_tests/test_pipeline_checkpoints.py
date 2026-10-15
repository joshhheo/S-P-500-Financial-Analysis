"""Offline checks for pipeline diagnostics and saved partial extraction."""
from decimal import Decimal
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
from table_data.generate_ratios import generate_ratios


class CheckpointTests(unittest.TestCase):
    def test_interruption_keeps_completed_csv_and_saves_partial_rows(self):
        original_directory = Path.cwd()
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent / "implementation") as directory:
            try:
                os.chdir(directory)
                Path("data").mkdir()
                Path("data/financial_ratios.csv").write_text("previous completed run\n")
                pd.DataFrame([dict(ticker=t, cik=c, company_name=t, sector="Technology")
                              for t, c in [("AAA", 1), ("BBB", 2)]]).to_csv("data/company_status.csv", index=False)
                financials = SimpleNamespace(annual_start=lambda end: "2025-01-01")
                filing = SimpleNamespace(period_of_report="2025-12-31", accession_no="constructed", obj=lambda: SimpleNamespace(financials=financials))
                company = SimpleNamespace(get_filings=lambda **kwargs: [filing])
                with patch("table_data.generate_ratios.setup_sec_identity"), \
                     patch("table_data.generate_ratios.Company", side_effect=[company, RuntimeError("interrupted")]), \
                     patch("table_data.generate_ratios.from_filing", return_value=financials), \
                     patch("table_data.generate_ratios.filing_ratio", side_effect=[(Decimal("0.5"), "available"), (None, "missing")]), \
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
