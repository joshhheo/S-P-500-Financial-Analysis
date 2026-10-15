"""Constructed tests of the user-selected first-successful-fallback policy."""
import unittest
from unittest.mock import patch
from decimal import Decimal
from test_source_evidence import instance, fact, END
from value_retrieval.source import parse_source
from value_retrieval.get_assets import get_assets
from value_retrieval.get_liabilities import get_liabilities
from value_retrieval.get_interest_expense import get_interest_expense
from value_retrieval.get_operating_income import get_operating_income


class OrderedFallbackTests(unittest.TestCase):
    def test_reported_values_do_not_evaluate_fallbacks_including_zero(self):
        cases = [('Assets', get_assets, False), ('Liabilities', get_liabilities, False),
                 ('InterestExpense', get_interest_expense, True),
                 ('OperatingIncomeLoss', get_operating_income, True)]
        for concept, getter, duration in cases:
            for value in ('0', '100'):
                with self.subTest(concept=concept, value=value):
                    source = parse_source(instance(fact(concept, value, context='d' if duration else 'i')), cik=2488)
                    args = (source, '2025-01-01', END) if duration else (source, END)
                    with patch('value_retrieval.get_value.get_calculated_amount',
                               side_effect=AssertionError('Fallback must not run')):
                        self.assertEqual(getter(*args), Decimal(value))

    def test_successful_equation_does_not_read_later_conflicting_duplicates(self):
        # The second equation would fail duplicate selection if it were evaluated.
        source = parse_source(instance(fact('Cash', '25') + fact('AssetsCurrent', '10') +
                                       fact('AssetsCurrent', '20')), cik=2488)
        source.equations = {
            ('first', 'us-gaap:Assets'): [('us-gaap:Cash', 1)],
            ('second', 'us-gaap:Assets'): [('us-gaap:AssetsCurrent', 1)],
        }
        self.assertEqual(get_assets(source, END), 25)

    def test_derived_zero_is_success_and_does_not_fall_through(self):
        source = parse_source(instance(fact('Cash', '0') + fact('AssetsCurrent', '10') +
                                       fact('AssetsNoncurrent', '20')), cik=2488)
        source.equations = {('first', 'us-gaap:Assets'): [('us-gaap:Cash', 1)]}
        self.assertEqual(get_assets(source, END), 0)

    def test_incomplete_first_equation_allows_next_complete_equation(self):
        source = parse_source(instance(fact('AssetsCurrent', '10') + fact('Cash', '25')), cik=2488)
        source.equations = {
            ('first', 'us-gaap:Assets'): [('us-gaap:AssetsCurrent', 1), ('us-gaap:AssetsNoncurrent', 1)],
            ('second', 'us-gaap:Assets'): [('us-gaap:Cash', 1)],
        }
        self.assertEqual(get_assets(source, END), 25)
