import sys
sys.path.append("src")

from edgar import Company
from setup_sec_identity import setup_sec_identity

setup_sec_identity()

ticker = "HONA"

company = Company(ticker)
financial_data = company.get_financials()

if financial_data is None:
    print("no filing")
else:
    print("filing availible")
