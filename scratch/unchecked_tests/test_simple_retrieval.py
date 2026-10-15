"""Constructed XML tests: unit filtering happens at the source boundary."""
import unittest
from edgar.xbrl import XBRL
from value_retrieval.get_reporting_period import get_annual_start
from value_retrieval.get_assets import get_assets
from calculations.debt_to_asset_ratio import calculate_debt_to_assets
from table_data.generate_ratios import filing_ratio

END = '2025-12-31'

def fact(name, value, unit='dollars', context='i'):
    content = '' if value is None else str(value)
    nil = ' xsi:nil="true"' if value is None else ''
    return f'<us-gaap:{name} contextRef="{context}" unitRef="{unit}" decimals="0"{nil}>{content}</us-gaap:{name}>'


def source(facts):
    xml = f'''<xbrl xmlns="http://www.xbrl.org/2003/instance"
        xmlns:us-gaap="http://fasb.org/us-gaap/2026" xmlns:dei="http://xbrl.sec.gov/dei/2026"
        xmlns:iso="http://www.xbrl.org/2003/iso4217" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <context id="i"><entity><identifier scheme="http://www.sec.gov/CIK">1</identifier></entity>
          <period><instant>{END}</instant></period></context>
        <context id="d"><entity><identifier scheme="http://www.sec.gov/CIK">1</identifier></entity>
          <period><startDate>2025-01-01</startDate><endDate>{END}</endDate></period></context>
        <unit id="dollars"><measure>iso:USD</measure></unit>
        <unit id="foreign"><measure>iso:EUR</measure></unit>
        <dei:DocumentType contextRef="d">10-K</dei:DocumentType>
        <dei:DocumentFiscalPeriodFocus contextRef="d">FY</dei:DocumentFiscalPeriodFocus>
        <dei:DocumentPeriodEndDate contextRef="d">{END}</dei:DocumentPeriodEndDate>
        {facts}</xbrl>'''
    parsed = XBRL()
    parsed.parser.parse_instance_content(xml)
    return parsed


class RetrievalScopeTests(unittest.TestCase):
    def test_units_are_not_validated_under_scope_assumption(self):
        # Deliberately outside supported scope: demonstrates removal of enforcement,
        # not an endorsement of treating foreign-currency data as USD.
        data = source(fact('Assets', 100, 'foreign'))
        self.assertEqual(get_assets(data, END), 100)

    def test_missing_source_and_valid_ratio(self):
        self.assertEqual(filing_ratio(calculate_debt_to_assets, None, END), (None, 'missing'))
        data = source(fact('Assets', 100) + fact('Liabilities', 40))
        value, status = filing_ratio(calculate_debt_to_assets, data, END)
        self.assertEqual(str(value), '0.4')
        self.assertEqual(status, 'available')

    def test_unitless_metadata_establishes_annual_start(self):
        data = source(fact('Assets', 100))
        self.assertEqual(get_annual_start(data, END), '2025-01-01')

    def test_usd_nil_is_missing_not_zero(self):
        self.assertIsNone(get_assets(source(fact('Assets', None)), END))
        self.assertEqual(get_assets(source(fact('Assets', 0)), END), 0)


from value_retrieval.get_liabilities import get_liabilities
from value_retrieval.get_interest_expense import get_interest_expense
from value_retrieval.get_operating_income import get_operating_income

class ExplicitFormulaTests(unittest.TestCase):
    def test_partitions_and_direct_zero(self):
        data = source(fact('Assets', 0) + fact('AssetsCurrent', 10) + fact('AssetsNoncurrent', 20))
        self.assertEqual(get_assets(data, END), 0)
        self.assertEqual(get_assets(source(fact('AssetsCurrent', 10) + fact('AssetsNoncurrent', 20)), END), 30)
        self.assertEqual(get_liabilities(source(fact('LiabilitiesCurrent', 10) + fact('LiabilitiesNoncurrent', 20)), END), 30)

    def test_missing_equity_and_explicit_zero(self):
        facts = fact('Assets', 100) + fact('StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest', 40)
        self.assertIsNone(get_liabilities(source(facts), END))
        facts += fact('TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests', 0)
        self.assertEqual(get_liabilities(source(facts), END), 60)

    def test_equity_components_and_reverse_identity(self):
        facts = fact('Liabilities', 60) + fact('StockholdersEquity', 30) + fact('MinorityInterest', 10)
        facts += fact('TemporaryEquityCarryingAmountAttributableToParent', 0) + fact('RedeemableNoncontrollingInterestEquityCarryingAmount', 0)
        self.assertEqual(get_assets(source(facts), END), 100)
        self.assertIsNone(get_assets(source(''), END))

    def test_interest_and_wrong_dates(self):
        data = source(fact('InterestIncomeOperating', 15, context='d') + fact('InterestIncomeExpenseNet', 5, context='d') + fact('InterestExpenseNonoperating', 20, context='d'))
        self.assertEqual(get_interest_expense(data, '2025-01-01', END), 30)
        self.assertIsNone(get_interest_expense(data, '2025-04-01', END))
        self.assertIsNone(get_interest_expense(data, None, END))
        self.assertIsNone(get_operating_income(data, '2025-01-01', END))

    def test_dimensioned_fact_is_excluded(self):
        data = source(fact('Assets', 999) + fact('AssetsCurrent', 10) + fact('AssetsNoncurrent', 20))
        # Edgar supplies the dimension flag; change only the Assets context.
        from copy import deepcopy
        data.contexts['segment'] = deepcopy(data.contexts['i'])
        data.contexts['segment'].dimensions = {'us-gaap:StatementBusinessSegmentsAxis': 'test:SegmentMember'}
        for value in data._facts.values():
            if value.element_id == 'us-gaap:Assets':
                value.context_ref = 'segment'
        self.assertEqual(get_assets(data, END), 30)

    def test_short_annual_period_and_ambiguous_period(self):
        data = source(fact('OperatingIncomeLoss', 10, context='d'))
        data.contexts['d'].period['startDate'] = '2025-10-01'
        self.assertEqual(get_annual_start(data, END), '2025-10-01')

    def test_ambiguous_annual_start_is_missing(self):
        from copy import deepcopy
        data = source('')
        data.contexts['other'] = deepcopy(data.contexts['d'])
        data.contexts['other'].period['startDate'] = '2025-02-01'
        for key, original in list(data._facts.items()):
            if original.element_id.startswith('dei:'):
                duplicate = deepcopy(original)
                duplicate.context_ref = 'other'
                data._facts[key + '_other'] = duplicate
        self.assertIsNone(get_annual_start(data, END))

    def test_no_unreviewed_operating_income_formula(self):
        data = source(fact('GrossProfit', 100, context='d') + fact('OperatingExpenses', 20, context='d'))
        self.assertIsNone(get_operating_income(data, '2025-01-01', END))

    def test_zero_denominator_is_missing(self):
        data = source(fact('Assets', 0) + fact('Liabilities', 40))
        self.assertEqual(filing_ratio(calculate_debt_to_assets, data, END), (None, 'missing'))

    def test_pipeline_uses_edgar_objects_without_network_or_csv_writes(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        import pandas as pd
        from table_data.generate_ratios import generate_ratios
        data = source(fact('Assets', 100) + fact('Liabilities', 40))
        filing = SimpleNamespace(period_of_report=END, accession_no='test', obj=lambda: SimpleNamespace(financials=SimpleNamespace(xb=data)))
        company = SimpleNamespace(get_filings=lambda **kwargs: [filing])
        module = 'table_data.generate_ratios.'
        with patch(module+'setup_sec_identity'), patch(module+'Company', return_value=company), patch(module+'pd.read_csv', return_value=pd.DataFrame([dict(ticker='TEST',cik=1)])), patch(module+'save_csv') as save:
            generate_ratios()
            rows = save.call_args.args[0]
            self.assertEqual(str(rows[0]['debt_to_assets_ratio']), '0.4')
            self.assertEqual(rows[0]['interest_coverage_status'], 'missing')
            self.assertEqual(rows[0]['fiscal_period_start'], '2025-01-01')
