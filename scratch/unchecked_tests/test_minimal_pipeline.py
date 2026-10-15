"""Constructed storage and orchestration tests; no SEC requests or live database."""
from decimal import Decimal
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import pandas as pd
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from table_data.generate_ratios import generate_ratios, save_csv
from database.financials_table_info import financials_table_info
from test_database_load import row


class MinimalPipelineTests(unittest.TestCase):
    def test_csv_keeps_decimal_digits_zero_missing_and_status(self):
        values = [Decimal('0.1234567890123456789012345678'), Decimal(0), None]
        rows = [dict(ticker='ABC', fiscal_period_end=f'202{i}-12-31',
                     debt_to_assets_ratio=value,
                     debt_to_assets_status='available' if value is not None else 'missing')
                for i, value in enumerate(values)]
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent / 'implementation') as directory:
            path = Path(directory) / 'ratios.csv'
            save_csv(rows, path)
            restored = pd.read_csv(path, dtype=str, keep_default_na=False)
        self.assertEqual(restored.debt_to_assets_ratio.tolist(),
                         ['0.1234567890123456789012345678', '0', ''])
        self.assertEqual(restored.debt_to_assets_status.tolist(),
                         ['available', 'available', 'missing'])

    def test_only_five_distinct_filing_periods_are_written(self):
        filings = [SimpleNamespace(period_of_report=f'{year}-12-31', accession_no=str(index))
                   for index, year in enumerate([2025, 2025, 2024, 2023, 2022, 2021, 2020])]
        source = SimpleNamespace(annual_start=lambda end: end[:4] + '-01-01')
        company = SimpleNamespace(get_filings=lambda **kwargs: filings)
        original = Path.cwd()
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent / 'implementation') as directory:
            try:
                os.chdir(directory)
                Path('data').mkdir()
                pd.DataFrame([dict(ticker='ABC', cik=1)]).to_csv('data/company_status.csv', index=False)
                with patch('table_data.generate_ratios.setup_sec_identity'), \
                     patch('table_data.generate_ratios.Company', return_value=company), \
                     patch('table_data.generate_ratios.from_filing', return_value=source), \
                     patch('table_data.generate_ratios.filing_ratio', return_value=(None, 'missing')):
                    generate_ratios()
                saved = pd.read_csv('data/financial_ratios.csv')
                self.assertEqual(saved.fiscal_period_end.tolist(),
                                 [f'{year}-12-31' for year in range(2025, 2020, -1)])
                self.assertEqual(saved.accession.tolist(), [0, 2, 3, 4, 5])
            finally:
                os.chdir(original)

    def test_ticker_collision_does_not_overwrite_another_company(self):
        engine = create_engine('sqlite://')
        self.addCleanup(engine.dispose)
        with engine.begin() as connection:
            connection.execute(text('CREATE TABLE financials (ticker TEXT, fiscal_period_end TEXT, cik TEXT)'))
            connection.execute(text("INSERT INTO financials VALUES ('AMD', '2025-12-27', '999')"))
        with patch('database.financials_table_info.create_engine', return_value=engine), \
             patch('database.financials_table_info.load_dotenv'), \
             patch('database.financials_table_info.pd.read_csv', return_value=pd.DataFrame([dict(row(), ticker='NEW'), row()])):
            self.assertIsNone(financials_table_info())
        with engine.connect() as connection:
            self.assertEqual(connection.execute(text('SELECT cik FROM financials')).all(), [('999',)])
