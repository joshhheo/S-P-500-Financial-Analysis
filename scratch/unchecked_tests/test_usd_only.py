"""Constructed XML tests: unit filtering happens at the source boundary."""
import unittest
from value_retrieval.source import parse_source
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
    return parse_source(xml, cik=1)


class USDOnlyTests(unittest.TestCase):
    def test_foreign_only_is_missing(self):
        data = source(fact('Assets', 100, 'foreign') + fact('Liabilities', 40, 'foreign'))
        self.assertIsNone(get_assets(data, END))
        self.assertEqual(filing_ratio(calculate_debt_to_assets, data, END), (None, 'missing'))

    def test_foreign_fact_before_usd_is_ignored(self):
        for value in (999, None):
            data = source(fact('Assets', value, 'foreign') + fact('Assets', 100))
            self.assertEqual(get_assets(data, END), 100)

    def test_usd_fallback_can_follow_foreign_direct_fact(self):
        data = source(fact('Assets', 999, 'foreign') + fact('AssetsCurrent', 30) + fact('AssetsNoncurrent', 70))
        self.assertEqual(get_assets(data, END), 100)

    def test_foreign_component_cannot_enter_formula(self):
        data = source(fact('AssetsCurrent', 30) + fact('AssetsNoncurrent', 70, 'foreign'))
        self.assertIsNone(get_assets(data, END))

    def test_missing_source_and_valid_ratio(self):
        self.assertEqual(filing_ratio(calculate_debt_to_assets, None, END), (None, 'missing'))
        data = source(fact('Assets', 100) + fact('Liabilities', 40))
        value, status = filing_ratio(calculate_debt_to_assets, data, END)
        self.assertEqual(str(value), '0.4')
        self.assertEqual(status, 'available')

    def test_unitless_metadata_survives_without_stored_units(self):
        data = source(fact('Assets', 100))
        self.assertEqual(data.annual_start(END), '2025-01-01')
        self.assertFalse(hasattr(data, 'units'))
        self.assertTrue(all('unit_ref' not in row for row in data.records))

    def test_usd_nil_is_missing_not_zero(self):
        self.assertIsNone(get_assets(source(fact('Assets', None)), END))
        self.assertEqual(get_assets(source(fact('Assets', 0)), END), 0)
