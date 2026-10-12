import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

def refresh_view():

    load_dotenv()
    connection_string = os.getenv("db_connection_string")
    engine = create_engine(connection_string)

    with engine.begin() as connection:
        for filename, view in (
            ("sector_leverage.sql", "sector_leverage_rankings"),
            ("sector_interest_coverage.sql", "sector_interest_coverage_rankings"),
        ):
            with open(f"src/database/sql/{filename}") as f:
                connection.execute(text(f.read()))

            rows = connection.execute(text(f"SELECT COUNT(*) FROM {view}")).scalar_one()
            expected = connection.execute(text("SELECT COUNT(*) FROM companies WHERE is_current_constituent = TRUE")).scalar_one()
            if rows != expected:
                raise ValueError(f"{view}: expected {expected} current constituents, found {rows}")
            print(f"{view}: {rows} rows verified against current membership (commit pending)", flush=True)
    print("Both sector view definitions committed", flush=True)
