import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

def refresh_view():

    load_dotenv()
    connection_string = os.getenv("db_connection_string")
    engine = create_engine(connection_string)

    with engine.begin() as connection:
        for filename in ("sector_leverage.sql", "sector_interest_coverage.sql"):
            with open(f"src/database/sql/{filename}") as f:
                connection.execute(text(f.read()))

    print("Both sector view definitions committed", flush=True)
