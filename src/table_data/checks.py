"""Validation and visible summaries at the CSV/database handoffs."""
import pandas as pd


def check_companies(df):
    required = ["ticker", "cik", "company_name", "sector"]
    if df.empty or df[required].isna().any().any():
        raise ValueError("Company data is empty or contains missing required fields")
    if df["ticker"].duplicated().any():
        raise ValueError("Company data contains duplicate tickers")
    for column in ["ticker", "company_name", "sector"]:
        if df[column].astype(str).str.strip().eq("").any():
            raise ValueError(f"Company data contains blank {column} values")
    cik = pd.to_numeric(df["cik"], errors="raise")
    if ((cik <= 0) | (cik % 1 != 0)).any():
        raise ValueError("Company CIKs must be positive integers")
    print(f"Company data checked: {len(df)} unique tickers, "
          f"{df['cik'].nunique()} distinct CIKs, {df['sector'].nunique()} sectors", flush=True)


def check_ratios(df):
    keys = ["ticker", "fiscal_period_end"]
    if df[keys].isna().any().any() or df["ticker"].astype(str).str.strip().eq("").any():
        raise ValueError("Financial data contains missing/blank keys")
    if df.duplicated(keys).any():
        raise ValueError("Financial data contains duplicate ticker/period keys")
    pd.to_datetime(df["fiscal_period_end"], format="%Y-%m-%d", errors="raise")
    print(f"Financial data checked: {len(df)} rows, {df['ticker'].nunique()} tickers; "
          f"periods {df['fiscal_period_end'].min()} through {df['fiscal_period_end'].max()}", flush=True)
    for column in ["debt_to_assets_ratio", "interest_coverage_ratio"]:
        values = pd.to_numeric(df[column], errors="raise")
        print(f"  {column}: {values.notna().sum()} available, {values.isna().sum()} missing; "
              f"zero={values.eq(0).sum()}, negative={values.lt(0).sum()}, "
              f"min={values.min()}, max={values.max()}", flush=True)
