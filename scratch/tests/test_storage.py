"""Isolated SQLite handoff tests; this never connects to the live database.

SQLite is used only for transaction/NULL behavior, not PostgreSQL precision claims.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from sqlalchemy import create_engine, event, text

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from database.companies_table_info import companies_table_info
from database.financials_table_info import financials_table_info


def row(liabilities_to_assets=0.4, interest=28):
    return dict(
        ticker='AMD',
        fiscal_period_start='2024-12-29',
        fiscal_period_end='2025-12-27',
        liabilities_to_assets_ratio=liabilities_to_assets,
        interest_coverage_ratio=interest,
    )


class DatabaseLoadTests(unittest.TestCase):
    def test_numeric_load_null_replacement_without_financials_cik(self):
        engine = create_engine('sqlite://')
        self.addCleanup(engine.dispose)
        with engine.begin() as connection:
            connection.execute(text('''
                CREATE TABLE financials (
                    ticker TEXT,
                    fiscal_period_start TEXT,
                    fiscal_period_end TEXT,
                    liabilities_to_assets_ratio NUMERIC,
                    interest_coverage_ratio NUMERIC,
                    PRIMARY KEY (ticker, fiscal_period_end)
                )
            '''))
        binds = []

        @event.listens_for(engine, 'before_cursor_execute')
        def capture(connection, cursor, statement, parameters, context, many):
            if statement.lstrip().startswith('INSERT'):
                binds.append(parameters)

        with patch('database.financials_table_info.create_engine', return_value=engine), \
             patch('database.financials_table_info.load_dotenv'), \
             patch('database.financials_table_info.pd.read_csv', return_value=pd.DataFrame([row()])) as read:
            financials_table_info()
            read.assert_called_with('data/financial_ratios.csv')
            read.return_value = pd.DataFrame([row(0.2, float('nan'))])
            financials_table_info()

        self.assertEqual(binds[0][1], 0.4)
        with engine.connect() as connection:
            result = connection.execute(text('''
                SELECT liabilities_to_assets_ratio, interest_coverage_ratio
                FROM financials
            ''')).one()
        self.assertEqual(tuple(result), (0.2, None))

    def test_company_loader_keeps_cik_for_each_share_class(self):
        engine = create_engine('sqlite://')
        self.addCleanup(engine.dispose)
        with engine.begin() as connection:
            connection.execute(text('''
                CREATE TABLE companies (
                    ticker TEXT PRIMARY KEY,
                    cik TEXT,
                    company_name TEXT,
                    sector TEXT,
                    is_current_constituent BOOLEAN
                )
            '''))
        companies = pd.DataFrame([
            dict(ticker='GOOG', cik=1652044, company_name='Alphabet Class C', sector='Communication Services'),
            dict(ticker='GOOGL', cik=1652044, company_name='Alphabet Class A', sector='Communication Services'),
        ])
        with patch('database.companies_table_info.create_engine', return_value=engine), \
             patch('database.companies_table_info.load_dotenv'), \
             patch('database.companies_table_info.pd.read_csv', return_value=companies):
            companies_table_info()
            companies_table_info()

        with engine.connect() as connection:
            rows = connection.execute(text('SELECT ticker, cik FROM companies ORDER BY ticker')).all()
        self.assertEqual(rows, [('GOOG', '1652044'), ('GOOGL', '1652044')])
