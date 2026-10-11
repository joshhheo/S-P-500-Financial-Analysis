import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


def financials_table_info():
    load_dotenv()
    engine = create_engine(os.getenv("db_connection_string"))

    df = pd.read_csv("data/financial_ratios.csv")

    # postgres does not allow null values in primary key
    df = df.dropna(subset=["ticker", "fiscal_period_end"])

    upsert_query = """
    INSERT INTO financials (ticker, fiscal_period_end, debt_to_assets_ratio, interest_coverage_ratio)
    VALUES (:ticker, :fiscal_period_end, :debt_to_assets_ratio, :interest_coverage_ratio)
    ON CONFLICT (ticker, fiscal_period_end)
    DO UPDATE SET
        debt_to_assets_ratio = EXCLUDED.debt_to_assets_ratio,
        interest_coverage_ratio = EXCLUDED.interest_coverage_ratio;
    """

    # begin automatically handles commit
    with engine.begin() as connection:
        for _, row in df.iterrows():
            connection.execute(text(upsert_query), {
                "ticker": row["ticker"],
                "fiscal_period_end": row["fiscal_period_end"],
                "debt_to_assets_ratio": (
                    row["debt_to_assets_ratio"]
                    if pd.notna(row["debt_to_assets_ratio"])
                    else None
                ),
                "interest_coverage_ratio": (
                    row["interest_coverage_ratio"]
                    if pd.notna(row["interest_coverage_ratio"])
                    else None
                ),
            })
