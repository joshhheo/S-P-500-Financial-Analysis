from pathlib import Path
import pandas as pd
from table_data.checks import check_companies, check_ratios
from edgar import Company

from setup_sec_identity import setup_sec_identity
from calculations.debt_to_asset_ratio import calculate_debt_to_assets
from calculations.interest_coverage_ratio import calculate_interest_coverage


def generate_ratios():
    setup_sec_identity()

    companies = pd.read_csv("data/company_status.csv")

    check_companies(companies)
    print(f"Extracting up to five distinct original 10-K periods per ticker for {len(companies)} tickers", flush=True)
    results = []
    no_filings = []
    columns = ["ticker", "fiscal_period_end", "debt_to_assets_ratio", "interest_coverage_ratio"]
    checkpoint = Path("data/financial_ratios.partial.csv")
    temporary = checkpoint.with_suffix(".tmp")
    pd.DataFrame(columns=columns).to_csv(temporary, index=False)
    temporary.replace(checkpoint)
    print(f"Started fresh checkpoint at {checkpoint}; this run does not resume a previous extraction", flush=True)

    for index, company in companies.iterrows():
        ticker = company["ticker"]
        cik = int(company["cik"])

        filings = Company(cik).get_filings(
            form="10-K",
            amendments=False,
        )

        periods = []
        skipped_dates = 0
        skipped_duplicates = 0
        missing_financials = 0
        missing_annual_start = 0
        first_result = len(results)

        for filing in filings:
            if not filing.period_of_report:
                skipped_dates += 1
                continue

            period_end = str(filing.period_of_report)[:10]

            if period_end in periods:
                skipped_duplicates += 1
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

            missing_financials += financial_data is None
            missing_annual_start += period_start is None

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

        company_rows = results[first_result:]
        if not periods:
            no_filings.append(ticker)
        debt_count = 0
        interest_count = 0
        for row in company_rows:
            if row["debt_to_assets_ratio"] is not None:
                debt_count += 1
            if row["interest_coverage_ratio"] is not None:
                interest_count += 1
        print(f"{index + 1}/{len(companies)} {ticker} (CIK {cik}): periods={periods}; "
              f"debt/assets={debt_count}/{len(periods)}, interest coverage={interest_count}/{len(periods)}; "
              f"missing financials={missing_financials}, missing annual start={missing_annual_start}; "
              f"skipped among examined filings: no date={skipped_dates}, duplicate period={skipped_duplicates}", flush=True)
        # Replace atomically so an interrupted write leaves the last checkpoint intact.
        temporary = checkpoint.with_suffix(".tmp")
        pd.DataFrame(results, columns=columns).to_csv(temporary, index=False)
        temporary.replace(checkpoint)
        print(f"Checkpoint: {len(results)} rows saved to {checkpoint}; "
              f"{index + 1}/{len(companies)} tickers processed. Partial file is not loaded by the database loader.", flush=True)

    df = pd.DataFrame(results, columns=columns)
    check_ratios(df)
    print(f"Tickers with no selected periods ({len(no_filings)}): {no_filings}", flush=True)
    if df.empty:
        raise ValueError("No financial rows extracted; completed CSV was not replaced")
    temporary = Path("data/financial_ratios.csv.tmp")
    df.to_csv(temporary, index=False)
    temporary.replace("data/financial_ratios.csv")
    print(f"Extraction complete: saved {len(df)} rows to data/financial_ratios.csv", flush=True)


if __name__ == "__main__":
    generate_ratios()
