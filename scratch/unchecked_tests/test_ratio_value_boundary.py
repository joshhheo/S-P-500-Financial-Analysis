"""Constructed tests for the retrieval/arithmetic boundary; no live filings."""
import unittest
from table_data.generate_ratios import filing_ratio
from decimal import Decimal
from test_source_evidence import instance, fact, END
from value_retrieval.source import parse_source
from value_retrieval.get_assets import get_assets
from value_retrieval.get_liabilities import get_liabilities
from value_retrieval.get_interest_expense import get_interest_expense
from value_retrieval.get_operating_income import get_operating_income
from calculations.debt_to_asset_ratio import calculate_debt_to_assets
from calculations.interest_coverage_ratio import calculate_interest_coverage


class RatioValueBoundaryTests(unittest.TestCase):
    def test_reported_assets_precede_other_balance_totals(self):
        source = parse_source(instance(
            fact('Assets', '100') + fact('Liabilities', '50') +
            fact('LiabilitiesAndStockholdersEquity', '120')), cik=2488)
        self.assertEqual(get_assets(source, END), 100)

    def test_disclosed_zero_is_valid_input_but_cannot_be_a_divisor(self):
        source = parse_source(instance(fact('Assets', '0') + fact('Liabilities', '5')), cik=2488)
        liabilities = get_liabilities(source, END)
        assets = get_assets(source, END)
        self.assertEqual(liabilities, Decimal('5'))
        self.assertEqual(assets, Decimal('0'))
        result = filing_ratio(calculate_debt_to_assets, source, END)
        self.assertEqual(result[1], 'missing')
        self.assertIsNone(result[0])

    def test_annual_period_failure_is_established_by_retrieval(self):
        self.assertIsNone(get_interest_expense(None, None, END))
        result = filing_ratio(calculate_interest_coverage, None, None, END)
        self.assertEqual(result, (None, 'missing'))


    def test_each_reported_metric_returns_without_comparing_its_filed_equation(self):
        cases = [
            ('Assets', 'AssetsCurrent', get_assets, None),
            ('Liabilities', 'LiabilitiesCurrent', get_liabilities, None),
            ('OperatingIncomeLoss', 'Revenues', get_operating_income, '2025-01-01'),
            ('InterestExpense', 'InterestExpenseNonoperating', get_interest_expense, '2025-01-01'),
        ]
        for concept, child, getter, start in cases:
            with self.subTest(concept=concept):
                context = 'd' if start else 'i'
                source = parse_source(instance(fact(concept, '100', context=context) +
                                               fact(child, '50', context=context)), cik=2488)
                source.equations = {('constructed', 'us-gaap:' + concept): [('us-gaap:' + child, 1)]}
                args = (source, start, END) if start else (source, END)
                self.assertEqual(getter(*args), 100)

    def test_independent_getters_can_be_combined_in_the_only_complete_currency(self):
        xml = instance(fact('Assets', '100') + fact('Liabilities', '50') +
                       fact('Assets', '200').replace('unitRef="u"', 'unitRef="eur"'))
        xml = xml.replace('</unit>', '</unit><unit id="eur"><measure>iso:EUR</measure></unit>', 1)
        source = parse_source(xml, cik=2488)
        self.assertIsNone(get_assets(source, END))
        self.assertEqual(get_assets(source, END, currency='USD'), 100)
        self.assertEqual(get_liabilities(source, END, currency='USD'), 50)
        self.assertEqual(filing_ratio(calculate_debt_to_assets, source, END)[0], Decimal('0.5'))

    def test_disjoint_currencies_are_not_combined(self):
        xml = instance(fact('Assets', '100') +
                       fact('Liabilities', '50').replace('unitRef="u"', 'unitRef="eur"'))
        xml = xml.replace('</unit>', '</unit><unit id="eur"><measure>iso:EUR</measure></unit>', 1)
        result = filing_ratio(calculate_debt_to_assets, parse_source(xml, cik=2488), END)
        self.assertIsNone(result[0])
        self.assertEqual(result[1], 'missing')

    def test_reported_operand_does_not_inspect_unused_reconciliation_equations(self):
        source = parse_source(instance(fact('OperatingIncomeLoss', '100', context='d')), cik=2488)
        source.equations = {('constructed', 'us-gaap:OperatingIncomeLoss'):
                            [('us-gaap:AdvertisingExpense', 1)]}
        self.assertEqual(get_operating_income(source, '2025-01-01', END), 100)
        result = filing_ratio(calculate_interest_coverage, source, '2025-01-01', END)
        self.assertIsNone(result[0])
        self.assertEqual(result[1], 'missing')
