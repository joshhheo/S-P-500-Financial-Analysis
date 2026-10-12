import time

from table_data.company_status import create_company_status_csv
from table_data.generate_ratios import generate_ratios
from database.create_tables import create_tables
from database.companies_table_info import companies_table_info
from database.financials_table_info import financials_table_info
from database.refresh_view import refresh_view

def main():
    total_start = time.time()

    stages = [
        ("Company CSV creation", create_company_status_csv),
        ("SEC ratio extraction", generate_ratios),
        ("Database schema setup", create_tables),
        ("Company database load", companies_table_info),
        ("Financial database load", financials_table_info),
        ("Sector view refresh", refresh_view),
    ]
    for label, run_stage in stages:
        start = time.time()
        print(f"Starting {label}", flush=True)
        run_stage()
        print(f"{label} completed: {time.time() - start:.2f} seconds", flush=True)

    print(f"Total runtime: {time.time() - total_start:.2f} seconds")


if __name__ == "__main__":
    main()