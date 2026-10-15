"""Load audited CSV results without routing decimal values through binary floats."""
import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from table_data.checks import check_ratios

AUDIT_COLUMNS = ['cik', 'accession', 'fiscal_period_start', 'debt_to_assets_status',
                 'interest_coverage_status', 'extraction_evidence']


def financials_table_info():
    df = pd.read_csv('data/financial_ratios.csv', dtype=str, keep_default_na=False)
    if not set(AUDIT_COLUMNS).issubset(df.columns):
        raise ValueError('CSV lacks extraction evidence; regenerate with the audited extractor')
    check_ratios(df)
    for column in ['cik', 'accession', 'extraction_evidence']:
        if df[column].str.strip().eq('').any():
            raise ValueError(f'Missing required provenance: {column}')
    # Validation finishes before opening a connection or writing any row.
    load_dotenv()
    engine = create_engine(os.getenv('db_connection_string'))
    columns = ['ticker', 'fiscal_period_end', 'debt_to_assets_ratio', 'interest_coverage_ratio'] + AUDIT_COLUMNS
    placeholders = [f'CAST(:{c} AS NUMERIC)' if c.endswith('_ratio') else f':{c}' for c in columns]
    updates = ', '.join(f'{c} = EXCLUDED.{c}' for c in columns if c not in ('ticker','fiscal_period_end'))
    query = text(f"INSERT INTO financials ({', '.join(columns)}) VALUES ({', '.join(placeholders)}) "
                 f"ON CONFLICT (ticker, fiscal_period_end) DO UPDATE SET {updates}")
    with engine.begin() as connection:
        for row in df.to_dict('records'):
            previous = connection.execute(text('SELECT cik FROM financials WHERE ticker=:ticker '
                'AND fiscal_period_end=:fiscal_period_end'), row).scalar()
            if previous and str(previous) != row['cik']:
                raise ValueError('Ticker/period already belongs to another CIK')
            connection.execute(query, {c: row[c] if row[c] != '' else None for c in columns})
    print(f'Financial transaction committed: {len(df)} audited upserts', flush=True)
