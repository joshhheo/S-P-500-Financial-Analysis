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
    matches = matches.dropna(subset=['value'])
    matches = matches[matches['value'] != '']
    if matches.empty:
        return None
    return float(matches.iloc[0]['value'])


def get_annual_start(financial_data, period_end):
    if financial_data is None:
        return None
    starts = None
    checks = {
        'dei:DocumentType': '10-K',
        'dei:DocumentFiscalPeriodFocus': 'FY',
        'dei:DocumentPeriodEndDate': period_end,
    }
    # xbrl structure links info via context, not columns of table
    for concept, value in checks.items():
        facts = financial_data.query().by_concept(concept, exact=True).to_dataframe()
        matches = facts[facts['is_dimensioned'] == False]
        matches = matches[matches['period_end'].astype(str).str[:10] == period_end]
        matches = matches[matches['value'] == value]
        dates = set(matches['period_start'].dropna().astype(str).str[:10])
        if starts is None:
            starts = dates
        else:
            starts = starts.intersection(dates)
    if len(starts) == 1:
        # sets cannot be indexed
        return list(starts)[0]
    else:
        return None
