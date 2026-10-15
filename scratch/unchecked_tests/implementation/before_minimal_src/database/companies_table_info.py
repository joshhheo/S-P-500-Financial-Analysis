import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


def companies_table_info():
    load_dotenv()
    engine = create_engine(os.getenv("db_connection_string"))

    companies = pd.read_csv("data/company_status.csv")

    print(f"Loading {len(companies)} company rows; resetting current membership then upserting", flush=True)

    upsert_query = """
    INSERT INTO companies (ticker, company_name, sector, is_current_constituent)
    VALUES (:ticker, :company_name, :sector, TRUE)
    ON CONFLICT (ticker)
    DO UPDATE SET
        company_name = EXCLUDED.company_name,
        sector = EXCLUDED.sector,
        is_current_constituent = EXCLUDED.is_current_constituent;
    """

    with engine.begin() as connection:
        connection.execute(
            text("UPDATE companies SET is_current_constituent = FALSE")
        )
        for _, row in companies.iterrows():
            connection.execute(text(upsert_query), {
                "ticker": row["ticker"],
                "company_name": row["company_name"],
                "sector": row["sector"],
            })

    print(f'Company transaction committed: {len(companies)} upserts', flush=True)
