import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


def companies_table_info():
    load_dotenv()
    engine = create_engine(os.getenv("db_connection_string"))

    companies = pd.read_csv("data/company_status.csv")

    print(f"Loading {len(companies)} company rows", flush=True)

    upsert_query = """
    INSERT INTO companies (ticker, cik, company_name, sector, is_current_constituent)
    VALUES (:ticker, :cik, :company_name, :sector, TRUE)
    ON CONFLICT (ticker)
    DO UPDATE SET
        cik = EXCLUDED.cik,
        company_name = EXCLUDED.company_name,
        sector = EXCLUDED.sector,
        is_current_constituent = EXCLUDED.is_current_constituent;
    """

    with engine.begin() as connection:
        # sets all companies to not current constituent
        # only companies in current csv get set to current constituent
        connection.execute(
            text("UPDATE companies SET is_current_constituent = FALSE")
        )
        for _, row in companies.iterrows():
            connection.execute(text(upsert_query), {
                "ticker": row["ticker"],
                "cik": str(int(row["cik"])),
                "company_name": row["company_name"],
                "sector": row["sector"],
            })
