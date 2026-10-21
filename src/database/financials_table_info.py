import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


def financials_table_info():
    df = pd.read_csv('data/financial_ratios.csv')
    load_dotenv()
    engine = create_engine(os.getenv('db_connection_string'))

    upsert_query = """
    INSERT INTO financials (
        ticker, liabilities_to_assets_ratio, interest_coverage_ratio,
        fiscal_period_start, fiscal_period_end
    )
    VALUES (
        :ticker, :liabilities_to_assets_ratio,
        :interest_coverage_ratio,
        :fiscal_period_start, :fiscal_period_end
    )
    ON CONFLICT (ticker, fiscal_period_end)
    DO UPDATE SET
        liabilities_to_assets_ratio = EXCLUDED.liabilities_to_assets_ratio,
        interest_coverage_ratio = EXCLUDED.interest_coverage_ratio,
        fiscal_period_start = EXCLUDED.fiscal_period_start;
    """

    with engine.begin() as connection:
        for row in df.to_dict('records'):
            # empty CSV cells become SQL NULL
            for column, value in row.items():
                if pd.isna(value):
                    row[column] = None
            connection.execute(text(upsert_query), row)

