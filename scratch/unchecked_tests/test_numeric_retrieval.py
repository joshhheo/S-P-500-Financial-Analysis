"""Constructed regressions for plain-number retrieval after removing Amount."""
from decimal import Decimal
import unittest

from test_calculation_fallbacks import fact, filing, END, START
from value_retrieval.get_value import get_value
from value_retrieval.get_equity import equation_applies


class NumericRetrievalTests(unittest.TestCase):
    def test_inverse_equation_preserves_negative_target_weight(self):
        # Net operating interest income = income - expense.
        rows = [fact('InterestIncomeExpenseNet', -2), fact('InterestIncomeOperating', 10)]
        network = [('us-gaap_InterestIncomeExpenseNet', 'us-gaap_InterestIncomeOperating', 1),
                   ('us-gaap_InterestIncomeExpenseNet', 'us-gaap_InterestExpenseOperating', -1)]
        self.assertEqual(get_value(filing(rows, [network]), 'us-gaap:InterestExpenseOperating',
                                   END, START, currency='USD'), Decimal(12))

    def test_nested_derivation_cannot_mix_currency_or_period(self):
        # Total interest needs both operating and nonoperating amounts. The
        # operating amount itself is derived from income minus net income.
        for mismatch in ({'unit_ref': 'eur'}, {'period_start': '2020-01-01'}):
            rows = [fact('InterestIncomeOperating', 10),
                    fact('InterestIncomeExpenseNet', -2, **mismatch),
                    fact('InterestExpenseNonoperating', 3)]
            source = filing(rows)
            source.units['eur'] = 'EUR'
            self.assertIsNone(get_value(source, 'us-gaap:InterestExpense', END, START,
                                        currency='USD'))

    def test_empty_accounting_cycle_returns_none(self):
        self.assertIsNone(get_value(filing([]), 'us-gaap:Assets', END, currency='USD'))

    def test_reported_equity_scope_still_accounts_for_rounding(self):
        parent = 'us-gaap:LiabilitiesAndStockholdersEquity'
        children = [('us-gaap:Liabilities', 1), ('us-gaap:StockholdersEquity', 1)]
        for inclusive, expected in ((100, True), (101, True), (102, False)):
            rows = [fact('StockholdersEquity', 100, decimals='0'),
                    fact('StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
                         inclusive, decimals='0')]
            self.assertEqual(equation_applies(filing(rows), parent, children, END,
                                             currency='USD'), expected)
