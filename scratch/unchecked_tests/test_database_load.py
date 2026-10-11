import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from database.financials_table_info import financials_table_info


class DatabaseLoadTests(unittest.TestCase):
    def test_upsert_both_ratios_and_replace_missing_with_null(self):
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE financials (ticker TEXT, fiscal_period_end TEXT, debt_to_assets_ratio NUMERIC, interest_coverage_ratio NUMERIC, PRIMARY KEY (ticker, fiscal_period_end))"))
        rows = pd.DataFrame([
            dict(ticker="AMD", fiscal_period_end="2025-12-27", debt_to_assets_ratio=.18, interest_coverage_ratio=28),
            dict(ticker="BAD", fiscal_period_end=None, debt_to_assets_ratio=1, interest_coverage_ratio=1),
        ])
        with patch("database.financials_table_info.create_engine", return_value=engine), patch("database.financials_table_info.load_dotenv"), patch("database.financials_table_info.pd.read_csv", return_value=rows) as read:
            financials_table_info()
            read.assert_called_with("data/financial_ratios.csv")
            rows.loc[0, "debt_to_assets_ratio"] = .2
            rows.loc[0, "interest_coverage_ratio"] = float("nan")
            financials_table_info()
        with engine.connect() as connection:
            result = connection.execute(text("SELECT ticker, debt_to_assets_ratio, interest_coverage_ratio FROM financials")).all()
        self.assertEqual(result, [("AMD", .2, None)])
