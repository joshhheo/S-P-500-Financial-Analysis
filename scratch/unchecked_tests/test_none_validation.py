"""Constructed missing/unsupported cases; malformed source syntax is out of scope."""
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from test_source_evidence import instance, fact, END
from value_retrieval.source import parse_source, from_filing
from value_retrieval.get_value import decimal_value, get_value as retrieve
from value_retrieval.get_equity import accuracy_interval
from value_retrieval.get_assets import get_assets
from table_data.generate_ratios import filing_ratio
from calculations.debt_to_asset_ratio import calculate_debt_to_assets


class NoneValidationTests(unittest.TestCase):
    def test_compliant_numbers_and_accuracy(self):
        self.assertIsNone(decimal_value(None))
        self.assertEqual(decimal_value('123.50'), Decimal('123.50'))
        self.assertEqual(decimal_value('1' * 61), Decimal('1' * 61))
        self.assertEqual(accuracy_interval(Decimal(100), '-2')[:2],
                         (Decimal(50), Decimal(150)))
        self.assertEqual(accuracy_interval(Decimal(100), 'INF')[:2],
                         (Decimal(100), Decimal(100)))
        self.assertIsNone(accuracy_interval(Decimal(1), None))

    def test_direct_first_row_precedes_accounting_fallback(self):
        source = parse_source(instance(fact('Assets', '100') + fact('Assets', '200') +
                                       fact('AssetsCurrent', '30') + fact('AssetsNoncurrent', '40')), cik=2488)
        self.assertEqual(get_assets(source, END), 100)

    def test_unavailable_unit_returns_none(self):
        source = parse_source(instance(fact('Assets', '100')), cik=2488)
        source.records[0]['unit_ref'] = 'unknown'
        self.assertIsNone(retrieve(source, 'us-gaap:Assets', END))

    def test_conflicting_reporting_currencies_do_not_become_an_arbitrary_basis(self):
        source = parse_source(instance(fact('Assets', '100') + fact('Liabilities', '50')), cik=2488)
        for currency in ('USD', 'EUR'):
            source.records.append(dict(concept='dei:EntityReportingCurrencyISOCode', value=currency,
                                       is_dimensioned=False, entity_identifier='2488', period_end=END))
        self.assertEqual(filing_ratio(calculate_debt_to_assets, source, END), (None, 'missing'))

    def test_unsupported_taxonomy_and_missing_instance_return_none(self):
        self.assertIsNone(parse_source('<xbrl xmlns="http://www.xbrl.org/2003/instance"/>', cik=2488))
        filing = SimpleNamespace(attachments=[], homepage=SimpleNamespace(attachments=[]))
        with patch('edgar.xbrl.xbrl.XBRLAttachments', return_value=SimpleNamespace(has_instance_document=False)):
            self.assertIsNone(from_filing(filing, 2488))

    def test_incompatible_components_cannot_enter_arithmetic(self):
        # The currency is enforced during retrieval, before plain numeric arithmetic.
        source = parse_source(instance(fact('AssetsCurrent', '30') +
                                       fact('AssetsNoncurrent', '40')), cik=2488)
        source.units['eur'] = 'EUR'
        source.records[1]['unit_ref'] = 'eur'
        self.assertIsNone(get_assets(source, END, currency='USD'))
        self.assertIsNone(get_assets(source, END, currency='EUR'))
