"""Isolated SQLite handoff tests; this never connects to the live database.

SQLite is used only for transaction/NULL behavior, not PostgreSQL precision claims.
"""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from sqlalchemy import create_engine, text, event
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from database.financials_table_info import financials_table_info


def row(debt='0.1234567890123456789012345678', interest='28'):
    evidence={name:dict(value=value or None,status='available' if value else 'missing')
              for name,value in [('debt_to_assets',debt),('interest_coverage',interest)]}
    return dict(ticker='AMD',fiscal_period_end='2025-12-27',cik='2488',accession='constructed',
        fiscal_period_start='2024-12-29',debt_to_assets_ratio=debt,interest_coverage_ratio=interest,
        debt_to_assets_status=evidence['debt_to_assets']['status'],
        interest_coverage_status=evidence['interest_coverage']['status'],extraction_evidence=json.dumps(evidence))


class DatabaseLoadTests(unittest.TestCase):
    def test_exact_bind_null_replacement_and_provenance(self):
        engine=create_engine('sqlite://')
        self.addCleanup(engine.dispose)
        with engine.begin() as connection:
            connection.execute(text('CREATE TABLE financials (ticker TEXT, fiscal_period_end TEXT, '
                'debt_to_assets_ratio NUMERIC, interest_coverage_ratio NUMERIC, cik TEXT, accession TEXT, '
                'fiscal_period_start TEXT, debt_to_assets_status TEXT, interest_coverage_status TEXT, '
                'extraction_evidence TEXT, PRIMARY KEY(ticker,fiscal_period_end))'))
        binds=[]
        @event.listens_for(engine,'before_cursor_execute')
        def capture(connection,cursor,statement,parameters,context,many):
            if statement.startswith('INSERT'): binds.append(parameters)
        with patch('database.financials_table_info.create_engine',return_value=engine), \
             patch('database.financials_table_info.load_dotenv'), \
             patch('database.financials_table_info.pd.read_csv',return_value=pd.DataFrame([row()])) as read:
            financials_table_info()
            read.assert_called_with('data/financial_ratios.csv',dtype=str,keep_default_na=False)
            read.return_value=pd.DataFrame([row('0.2','')])
            financials_table_info()
        self.assertEqual(binds[0][2],'0.1234567890123456789012345678')
        with engine.connect() as connection:
            result=connection.execute(text('SELECT debt_to_assets_ratio,interest_coverage_ratio,interest_coverage_status,cik,extraction_evidence FROM financials')).one()
        self.assertEqual(tuple(result),(.2,None,'missing','2488',None))
