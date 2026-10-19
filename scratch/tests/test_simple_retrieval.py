"""Constructed XML tests for exact retrieval and reviewed accounting identities."""
import unittest
from edgar.xbrl import XBRL
from value_retrieval.get_value import get_annual_start
from value_retrieval.get_assets import get_assets
from calculations.debt_to_asset_ratio import calculate_debt_to_assets

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
    def test_first_nonmissing_match_preserves_zero_and_order(self):
        # Construct Edgar's query result directly so parser deduplication cannot
        # hide the mixed blank/numeric rows this selection policy addresses.
        import pandas as pd
        from unittest.mock import Mock
        from value_retrieval.get_value import get_value

        cases = [([100, None], 100), ([None, '', 100], 100),
                 ([float('nan'), '', 0, 100], 0), ([None, '', 100, 101], 100),
                 ([None, float('nan'), ''], None), ([], None)]
        for start in [None, '2025-01-01']:
            for values, expected in cases:
                with self.subTest(start=start, values=values):
                    rows = [dict(value=value, is_dimensioned=False,
                                 period_instant=END, period_start='2025-01-01',
                                 period_end=END) for value in values]
                    # A usable number outside the selected scope must not win.
                    rows.insert(0, dict(value=999, is_dimensioned=True,
                                        period_instant=END, period_start='2025-01-01',
                                        period_end=END))
                    data = Mock()
                    data.query.return_value.by_concept.return_value.to_dataframe.return_value = pd.DataFrame(rows)
                    self.assertEqual(get_value(data, 'us-gaap:Assets', END, start), expected)

    def test_units_are_not_validated_under_scope_assumption(self):
        # Deliberately outside supported scope: demonstrates removal of enforcement,
        # not an endorsement of treating foreign-currency data as USD.
        data = source(fact('Assets', 100, 'foreign'))
        self.assertEqual(get_assets(data, END), 100)

    def test_missing_source_and_valid_ratio(self):
        self.assertIsNone(calculate_debt_to_assets(None, END))
        data = source(fact('Assets', 100) + fact('Liabilities', 40))
        value = calculate_debt_to_assets(data, END)
        self.assertEqual(str(value), '0.4')

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

    def test_operating_income_does_not_assume_missing_adjustments_zero(self):
        data = source(fact('GrossProfit', 100, context='d') + fact('OperatingExpenses', 20, context='d'))
        self.assertIsNone(get_operating_income(data, '2025-01-01', END))

    def test_zero_denominator_is_missing(self):
        data = source(fact('Assets', 0) + fact('Liabilities', 40))
        self.assertIsNone(calculate_debt_to_assets(data, END))

    def test_pipeline_uses_edgar_objects_without_network_or_csv_writes(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        import pandas as pd
        from table_data.generate_ratios import generate_ratios
        data = source(fact('Assets', 100) + fact('Liabilities', 40))
        filing = SimpleNamespace(period_of_report=END, obj=lambda: SimpleNamespace(financials=SimpleNamespace(xb=data)))
        company = SimpleNamespace(get_filings=lambda **kwargs: [filing])
        module = 'table_data.generate_ratios.'
        with patch(module+'setup_sec_identity'), patch(module+'Company', return_value=company), patch(module+'pd.read_csv', return_value=pd.DataFrame([dict(ticker='TEST',cik=1)])), patch.object(pd.DataFrame, 'to_csv', autospec=True) as save:
            generate_ratios()
            save.assert_called_once()
            self.assertEqual(str(save.call_args.args[1]), 'data/financial_ratios.csv')
            self.assertFalse(save.call_args.kwargs['index'])
            rows = save.call_args.args[0].to_dict('records')
            self.assertEqual(str(rows[0]['debt_to_assets_ratio']), '0.4')
            self.assertIsNone(rows[0]['interest_coverage_ratio'])
            self.assertEqual(set(rows[0]), {'ticker', 'fiscal_period_start', 'fiscal_period_end', 'debt_to_assets_ratio', 'interest_coverage_ratio'})
            self.assertEqual(rows[0]['fiscal_period_start'], '2025-01-01')


class ReviewedFallbackTests(unittest.TestCase):
    def duration_source(self, values):
        return source(''.join(fact(name, value, context='d') for name, value in values.items()))

    def coverage_interest(self, values):
        return get_interest_expense(self.duration_source(values), '2025-01-01', END)

    def operating_income(self, values):
        return get_operating_income(self.duration_source(values), '2025-01-01', END)

    def test_net_assets_identities_keep_negative_net_assets(self):
        self.assertEqual(get_assets(source(fact('Liabilities', 120) + fact('AssetsNet', -20)), END), 100)
        self.assertEqual(get_liabilities(source(fact('Assets', 100) + fact('AssetsNet', -20)), END), 120)
        self.assertIsNone(get_assets(source(fact('AssetsNet', 100)), END))
        self.assertIsNone(get_liabilities(source(fact('AssetsNet', 100)), END))

    def test_partners_permanent_equity_requires_temporary_equity(self):
        facts = fact('Assets', 100) + fact('PartnersCapitalIncludingPortionAttributableToNoncontrollingInterest', 25)
        self.assertIsNone(get_liabilities(source(facts), END))
        facts += fact('TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests', 5)
        self.assertEqual(get_liabilities(source(facts), END), 70)

    def test_operating_income_formulas_with_explicit_zero_adjustments(self):
        zero = dict(OtherOperatingIncomeExpenseNet=0, GovernmentAssistanceOperatingIncome=0)
        self.assertEqual(self.operating_income(dict(zero, GrossProfit=100, OperatingExpenses=120)), -20)
        self.assertEqual(self.operating_income(dict(zero, Revenues=200, CostsAndExpenses=150)), 50)
        self.assertEqual(self.operating_income(dict(zero, Revenues=200, CostOfRevenue=80, OperatingExpenses=70)), 50)
        self.assertEqual(self.operating_income(dict(zero, GrossProfit=120, CostsAndExpenses=150, CostOfRevenue=80)), 50)
        self.assertIsNone(self.operating_income(dict(zero, RevenueFromContractWithCustomerExcludingAssessedTax=200, CostsAndExpenses=150)))
        self.assertIsNone(self.operating_income(dict(zero, GrossProfit=100)))
        self.assertIsNone(self.operating_income(dict(zero, GrossProfit=100, OperatingExpenses=20, OtherOperatingIncomeExpenseNet=5)))

    def test_direct_values_and_first_formula_take_priority(self):
        self.assertEqual(self.operating_income(dict(OperatingIncomeLoss=0, GrossProfit=100, OperatingExpenses=20)), 0)
        zero = dict(OtherOperatingIncomeExpenseNet=0, GovernmentAssistanceOperatingIncome=0)
        self.assertEqual(self.operating_income(dict(zero, GrossProfit=100, OperatingExpenses=20, Revenues=200, CostsAndExpenses=100)), 80)
        self.assertEqual(self.coverage_interest(dict(InterestExpense=0, InterestCostsIncurred=100, InterestCostsCapitalized=20)), 0)
        self.assertEqual(self.coverage_interest(dict(InterestExpenseOperating=5, InterestExpenseNonoperating=10, InterestCostsIncurred=100, InterestCostsCapitalized=20)), 15)

    def test_incurred_less_capitalized_requires_both_inputs(self):
        for capitalized in ['InterestCostsCapitalized', 'InterestCostsCapitalizedAdjustment']:
            with self.subTest(capitalized=capitalized):
                self.assertEqual(self.coverage_interest({'InterestCostsIncurred': 100, capitalized: 30}), 70)
                self.assertEqual(self.coverage_interest({'InterestCostsIncurred': 100, capitalized: 0}), 100)
        self.assertIsNone(self.coverage_interest(dict(InterestCostsIncurred=100)))
        self.assertIsNone(self.coverage_interest(dict(InterestCostsIncurred=100, InterestCostsIncurredCapitalized=30)))
        self.assertIsNone(self.coverage_interest(dict(InterestPaidNet=70)))

    def test_total_interest_income_less_net_interest(self):
        self.assertEqual(self.coverage_interest(dict(InterestIncomeOperatingAndNonoperating=50, InterestRevenueExpenseNet=-20)), 70)
        self.assertEqual(self.coverage_interest(dict(InterestIncomeOperatingAndNonoperating=50, InterestIncomeExpenseNet=10, InterestIncomeExpenseNonoperatingNet=-30)), 70)
        self.assertIsNone(self.coverage_interest(dict(InterestIncomeOperatingAndNonoperating=50, InterestIncomeExpenseNet=10)))

    def test_interest_income_dividends_and_net_partitions(self):
        self.assertEqual(self.coverage_interest(dict(InterestAndDividendIncomeOperating=40, DividendIncomeOperating=10, InterestIncomeExpenseNet=5, InterestExpenseNonoperating=15)), 40)
        self.assertIsNone(self.coverage_interest(dict(InterestAndDividendIncomeOperating=40, InterestIncomeExpenseNet=5, InterestExpenseNonoperating=15)))
        self.assertEqual(self.coverage_interest(dict(InterestIncomeOperating=30, InterestRevenueExpenseNet=-10, InterestIncomeExpenseNonoperatingNet=-15, InterestExpenseNonoperating=15)), 40)
        self.assertEqual(self.coverage_interest(dict(InterestIncomeOperatingAndNonoperating=50, InterestIncomeOperating=30, InterestExpenseOperating=25, InterestIncomeExpenseNonoperatingNet=-15)), 60)

    def test_interest_missing_component_is_not_zero(self):
        self.assertIsNone(self.coverage_interest(dict(InterestExpenseNonoperating=20)))
        self.assertIsNone(self.coverage_interest(dict(InterestExpenseOperating=20)))
        self.assertIsNone(self.coverage_interest(dict(InterestAndDebtExpense=20)))
        self.assertIsNone(self.coverage_interest(dict(InterestExpenseDebt=20, FinanceLeaseInterestExpense=5)))


class NestedDefinitionFallbackTests(unittest.TestCase):
    def duration(self, values):
        return source(''.join(fact(name, value, context='d') for name, value in values.items()))

    def test_operating_expense_complement(self):
        from value_retrieval.operating_income.get_operating_expenses import get_operating_expenses
        values = dict(OperatingCostsAndExpenses=20, SellingGeneralAndAdministrativeExpense=10)
        self.assertEqual(get_operating_expenses(self.duration(values), '2025-01-01', END), 30)
        for missing in values:
            incomplete = dict(values)
            del incomplete[missing]
            self.assertIsNone(get_operating_expenses(self.duration(incomplete), '2025-01-01', END))
        self.assertEqual(get_operating_expenses(self.duration(dict(values, OperatingExpenses=0)), '2025-01-01', END), 0)
        values.update(GrossProfit=100, OtherOperatingIncomeExpenseNet=0, GovernmentAssistanceOperatingIncome=0)
        self.assertEqual(get_operating_income(self.duration(values), '2025-01-01', END), 70)

    def test_operating_revenue_partition_and_root_paths(self):
        from value_retrieval.operating_income.get_operating_revenue import get_operating_revenue
        values = dict(RegulatedOperatingRevenue=70, UnregulatedOperatingRevenue=30)
        self.assertEqual(get_operating_revenue(self.duration(values), '2025-01-01', END), 100)
        for missing in values:
            incomplete = dict(values)
            del incomplete[missing]
            self.assertIsNone(get_operating_revenue(self.duration(incomplete), '2025-01-01', END))
        self.assertEqual(get_operating_revenue(self.duration(dict(values, Revenues=0)), '2025-01-01', END), 0)
        self.assertEqual(get_operating_revenue(self.duration(dict(values, RegulatedAndUnregulatedOperatingRevenue=90)), '2025-01-01', END), 90)
        values.update(OtherOperatingIncomeExpenseNet=0, GovernmentAssistanceOperatingIncome=0)
        self.assertEqual(get_operating_income(self.duration(dict(values, CostsAndExpenses=60)), '2025-01-01', END), 40)
        self.assertEqual(get_operating_income(self.duration(dict(values, CostOfRevenue=40, OperatingExpenses=20)), '2025-01-01', END), 40)

    def test_members_equity_keeps_temporary_equity_separate(self):
        from value_retrieval.assets_and_liabilities.equity.get_members_equity import get_members_equity
        values = dict(MembersEquity=30, MembersEquityAttributableToNoncontrollingInterest=5)
        self.assertEqual(get_members_equity(self.instant(values), END), 35)
        for missing in values:
            incomplete = dict(values)
            del incomplete[missing]
            self.assertIsNone(get_members_equity(self.instant(incomplete), END))
        values.update(Liabilities=60)
        self.assertIsNone(get_assets(self.instant(values), END))
        values['TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests'] = 5
        self.assertEqual(get_assets(self.instant(values), END), 100)
        values.pop('Liabilities')
        values['Assets'] = 100
        self.assertEqual(get_liabilities(self.instant(values), END), 60)
        values['LimitedLiabilityCompanyLlcMembersEquityIncludingPortionAttributableToNoncontrollingInterest'] = 0
        self.assertEqual(get_members_equity(self.instant(values), END), 0)

    def instant(self, values):
        return source(''.join(fact(name, value) for name,value in values.items()))

    def test_consolidated_equity_before_treasury_includes_nci(self):
        from value_retrieval.assets_and_liabilities.get_equity import get_equity
        values = dict(StockholdersEquityBeforeTreasuryStock=80,
                      TreasuryStockCommonValue=7, TreasuryStockPreferredValue=3,
                      MinorityInterest=15)
        # NCI is already included in the before-treasury amount; do not add 15.
        self.assertEqual(get_equity(self.instant(values), END), 70)
        for missing in ['StockholdersEquityBeforeTreasuryStock', 'TreasuryStockCommonValue', 'TreasuryStockPreferredValue']:
            incomplete = dict(values)
            del incomplete[missing]
            self.assertIsNone(get_equity(self.instant(incomplete), END))
        values['TreasuryStockValue'] = 0
        self.assertEqual(get_equity(self.instant(values), END), 80)
        values['StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'] = 0
        self.assertEqual(get_equity(self.instant(values), END), 0)

    def test_nested_equity_reaches_both_main_metrics(self):
        values = dict(PartnersCapital=30, PartnersCapitalAttributableToNoncontrollingInterest=5,
                      TemporaryEquityCarryingAmountAttributableToParent=2,
                      RedeemableNoncontrollingInterestEquityCommonCarryingAmount=1,
                      RedeemableNoncontrollingInterestEquityPreferredCarryingAmount=2,
                      RedeemableNoncontrollingInterestEquityOtherCarryingAmount=0)
        self.assertEqual(get_assets(self.instant(dict(values, Liabilities=60)), END), 100)
        self.assertEqual(get_liabilities(self.instant(dict(values, Assets=100)), END), 60)
        for missing in values:
            incomplete = dict(values)
            del incomplete[missing]
            self.assertIsNone(get_assets(self.instant(dict(incomplete, Liabilities=60)), END))
        self.assertIsNone(get_assets(self.instant(values), END))
        self.assertIsNone(get_liabilities(self.instant(values), END))

    def test_assistance_income_partition_retains_zero_guard(self):
        values = dict(GrossProfit=100, OperatingExpenses=40, OtherOperatingIncomeExpenseNet=0,
                      GovernmentAssistanceAmount=5, GovernmentAssistanceNonoperatingIncome=5)
        def evaluate(values):
            data = source(''.join(fact(n,v,context='d') for n,v in values.items()))
            return get_operating_income(data, '2025-01-01', END)
        self.assertEqual(evaluate(values), 60)
        self.assertIsNone(evaluate(dict(values, GovernmentAssistanceNonoperatingIncome=4)))
        for missing in ['GovernmentAssistanceAmount','GovernmentAssistanceNonoperatingIncome']:
            incomplete=dict(values)
            del incomplete[missing]
            self.assertIsNone(evaluate(incomplete))
        self.assertIsNone(evaluate(dict(values, GovernmentAssistanceOperatingIncome=1)))

    def test_refactor_retains_identity_order(self):
        # Incurred/capitalized remains ahead of the derived net-interest identity.
        values = dict(InterestCostsIncurred=100, InterestCostsCapitalized=20,
                      InterestIncomeOperatingAndNonoperating=50,
                      InterestIncomeExpenseNet=10, InterestIncomeExpenseNonoperatingNet=-30)
        data=source(''.join(fact(n,v,context='d') for n,v in values.items()))
        self.assertEqual(get_interest_expense(data,'2025-01-01',END),80)
        # Direct revenue/cost total remains ahead of nested gross-profit retrieval.
        values = dict(OtherOperatingIncomeExpenseNet=0, GovernmentAssistanceOperatingIncome=0,
                      Revenues=200, CostsAndExpenses=100, CostOfRevenue=50, OperatingExpenses=10)
        data=source(''.join(fact(n,v,context='d') for n,v in values.items()))
        self.assertEqual(get_operating_income(data,'2025-01-01',END),100)
