"""Verify explicitly supported concepts against archived official sources."""
import unittest
from table_data.generate_ratios import filing_ratio
from review_explicit_concepts import review
from test_source_evidence import instance, fact, calculation, END
from value_retrieval.source import parse_source
from value_retrieval.get_value import get_value as retrieve, get_amount


class ExplicitConceptTests(unittest.TestCase):
    def test_supported_concepts_match_official_releases(self):
        result = review()
        self.assertEqual(len(result['versions']), 6)
        self.assertGreater(result['concept_count'], 0)

    def test_unreviewed_standard_component_is_not_dropped_from_sum(self):
        xml = instance(fact('AssetsCurrent', '10') + fact('OtherAssetsCurrent', '20'))
        calc = calculation('http://www.xbrl.org/2003/arcrole/summation-item')
        from test_source_evidence import SCHEMA
        extra = f'''<loc xlink:label="other" xlink:href="{SCHEMA}#us-gaap_OtherAssetsCurrent"/>
          <calculationArc xlink:arcrole="http://www.xbrl.org/2003/arcrole/summation-item"
           xlink:from="a" xlink:to="other" weight="1"/>'''
        calc = calc.replace('</calculationLink>', extra + '</calculationLink>')
        source = parse_source(xml, [calc], cik=2488)
        self.assertIsNone(get_amount(source, 'us-gaap:Assets', END, currency='USD'))
        self.assertIsNone(retrieve(source, 'us-gaap:OtherAssetsCurrent', END))

    def test_unreviewed_parent_cannot_be_derived_from_reviewed_child(self):
        xml = instance(fact('AssetsCurrent', '10'))
        calc = calculation('http://www.xbrl.org/2003/arcrole/summation-item')
        calc = calc.replace('#us-gaap_Assets"', '#us-gaap_CustomLookingName"')
        source = parse_source(xml, [calc], cik=2488)
        self.assertIsNone(retrieve(source, 'us-gaap:CustomLookingName', END))

    def test_reported_ratio_skips_unused_reconciliation_components(self):
        from calculations.interest_coverage_ratio import calculate_interest_coverage
        xml = instance(fact('OperatingIncomeLoss', '10', context='d') +
                       fact('InterestExpense', '2', context='d'))
        calc = calculation('http://www.xbrl.org/2003/arcrole/summation-item')
        calc = calc.replace('#us-gaap_Assets"', '#us-gaap_OperatingIncomeLoss"')
        calc = calc.replace('#us-gaap_AssetsCurrent"', '#us-gaap_AdvertisingExpense"')
        source = parse_source(xml, [calc], cik=2488)
        result = calculate_interest_coverage(source, '2025-01-01', END, currency='USD')
        self.assertEqual(result, 5)
