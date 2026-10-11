import pandas as pd
from edgar import Company

from quick_setup.setup_sec_identity import setup_sec_identity
from calculations.debt_to_asset_ratio import calculate_debt_to_assets
from calculations.interest_coverage_ratio import calculate_interest_coverage


def generate_ratios():
    setup_sec_identity()

    companies = pd.read_csv("data/company_status.csv")

    results = []

    for index, company in companies.iterrows():
        ticker = company["ticker"]
        cik = int(company["cik"])

        filings = Company(cik).get_filings(
            form="10-K",
            amendments=False,
        )

        periods = []

        for filing in filings:
            if not filing.period_of_report:
                continue

            period_end = str(filing.period_of_report)[:10]

            if period_end in periods:
                continue

            periods.append(period_end)

            annual_report = filing.obj()
            financial_data = None

            if annual_report is not None:
                financial_data = annual_report.financials

            period_start = None

            if financial_data is not None:
                for period in financial_data.xb.reporting_periods:
                    if period["type"] != "duration":
                        continue

                    if period["period_type"] != "Annual":
                        continue

                    if period["end_date"] != period_end:
                        continue

                    period_start = period["start_date"]
                    break

            debt_ratio = calculate_debt_to_assets(
                financial_data, period_end
            )

            interest_coverage = None

            if period_start is not None:
                interest_coverage = calculate_interest_coverage(
                    financial_data, period_start, period_end
                )

            results.append({
                "ticker": ticker,
                "fiscal_period_end": period_end,
                "debt_to_assets_ratio": debt_ratio,
                "interest_coverage_ratio": interest_coverage,
            })

            if len(periods) == 5:
                break

        print(f"{index + 1}/{len(companies)}: {ticker}, {len(periods)} annual periods", flush=True)

    pd.DataFrame(results).to_csv(
        "data/financial_ratios.csv",
        index=False,
    )
    print(f"Saved {len(results)} rows to data/financial_ratios.csv")


if __name__ == "__main__":
    generate_ratios()
