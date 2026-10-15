# stops floating-point rounding error
from decimal import Decimal

def get_value(financial_data, concept, period_end, period_start=None):
    if financial_data is None:
        return None
    facts = financial_data.query().by_concept(concept, exact=True).to_dataframe()
    matches = facts[facts['is_dimensioned'] == False]
    if period_start is None:
        matches = matches[matches['period_instant'].astype(str).str[:10] == period_end]
    else:
        matches = matches[matches['period_start'].astype(str).str[:10] == period_start]
        matches = matches[matches['period_end'].astype(str).str[:10] == period_end]
    if matches.empty or matches['value'].isna().any() or matches['value'].eq('').any():
        return None
    return Decimal(str(matches.iloc[0]['value']))
