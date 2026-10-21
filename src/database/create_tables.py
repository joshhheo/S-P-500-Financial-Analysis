import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

def create_tables():
    load_dotenv()

    connection_string = os.getenv("db_connection_string")
    engine = create_engine(connection_string)

    # store queries as string
    # primary/refrence key to avoid repeating constants
    create_companies_table = """
    CREATE TABLE IF NOT EXISTS companies (
        ticker TEXT PRIMARY KEY,
        cik TEXT,
        company_name TEXT,
        sector TEXT,
        is_current_constituent BOOLEAN NOT NULL DEFAULT FALSE
    );
    """

    # composite key allows duplicate tickers
    create_financials_table = """
    CREATE TABLE IF NOT EXISTS financials (
        ticker TEXT REFERENCES companies(ticker),
        fiscal_period_start DATE,
        fiscal_period_end DATE,
        liabilities_to_assets_ratio NUMERIC,
        interest_coverage_ratio NUMERIC,
        PRIMARY KEY (ticker, fiscal_period_end)
    );
    """

    # with statement to close connection automatically
    with engine.begin() as connection:
        connection.execute(text(create_companies_table))
        connection.execute(text(create_financials_table))


if __name__ == "__main__":
    create_tables()
