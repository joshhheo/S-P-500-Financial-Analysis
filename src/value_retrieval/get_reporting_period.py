
def get_annual_start(financial_data, period_end):
    if financial_data is None:
        return None
    starts = None
    for concept, value in (
        ('dei:DocumentType', '10-K'),
        ('dei:DocumentFiscalPeriodFocus', 'FY'),
        ('dei:DocumentPeriodEndDate', period_end),
    ):
        facts = financial_data.query().by_concept(concept, exact=True).to_dataframe()
        matches = facts[
            (facts['is_dimensioned'] == False)
            & (facts['period_end'].astype(str).str[:10] == period_end)
            & (facts['value'] == value)
        ]
        dates = set(matches['period_start'].dropna().astype(str).str[:10])
        starts = dates if starts is None else starts & dates
    return starts.pop() if len(starts) == 1 else None
