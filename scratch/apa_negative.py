import sys
sys.path.append("src")
from edgar import Company
from setup_sec_identity import setup_sec_identity

setup_sec_identity()

company = Company("MRSH")
financial_data = company.get_financials()

assets = financial_data.get_total_assets()
liabilities = financial_data.get_total_liabilities()
equity = financial_data.get_stockholders_equity()

print("assets:", assets)
print("liabilities:", liabilities)
print("equity:", equity)

result = financial_data.xb.query().by_concept("us-gaap:Assets", exact=True).to_dataframe()
# to_string to stop truncating
print(result[["fiscal_year", "numeric_value", "is_dimensioned", "label"]].to_string(index=False))