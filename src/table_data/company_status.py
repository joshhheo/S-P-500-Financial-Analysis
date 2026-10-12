import pandas as pd
from wiki_pull import get_wiki_dataframe
from table_data.checks import check_companies

def create_company_status_csv():
    companies = get_wiki_dataframe()
    print(f"Wikipedia returned {len(companies)} company rows", flush=True)
    results = []

    for _, company in companies.iterrows():
        results.append({
            "ticker": company["Symbol"],
            "cik": int(company["CIK"]),
            "company_name": company["Security"],
            "sector": company["GICS Sector"],
        })

    df = pd.DataFrame(results)
    check_companies(df)
    df.to_csv("data/company_status.csv", index=False)
    print(f"Saved {len(df)} company rows to data/company_status.csv", flush=True)


if __name__ == "__main__":
    create_company_status_csv()