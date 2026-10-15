"""Constructed tests for the direct-tag and accounting-only retrieval contract."""
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from value_retrieval.source import Source, parse_source, from_filing
from value_retrieval.get_assets import get_assets
from value_retrieval.get_liabilities import get_liabilities
from value_retrieval.get_interest_expense import get_interest_expense

END='2025-12-31'
def source(values):
 records=[]
 for concept,value in values.items():
  records.append(dict(concept='us-gaap:'+concept,value=str(value),nil=False,entity_identifier='1',is_dimensioned=False,period_instant=END,period_start='2025-01-01',period_end=END,unit_ref='u',decimals='0'))
 return Source('1',records)

class AccountingOnlyTests(unittest.TestCase):
 def test_direct_zero_precedes_formula(self):
  self.assertEqual(get_assets(source(dict(Assets=0,AssetsCurrent=10,AssetsNoncurrent=20)),END),0)
 def test_asset_partition(self):
  self.assertEqual(get_assets(source(dict(AssetsCurrent=10,AssetsNoncurrent=20)),END),30)
 def test_liability_partition(self):
  self.assertEqual(get_liabilities(source(dict(LiabilitiesCurrent=10,LiabilitiesNoncurrent=20)),END),30)
 def test_equity_identity_requires_temporary_equity(self):
  values=dict(Assets=100,StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest=40)
  self.assertIsNone(get_liabilities(source(values),END))
  values['TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests']=0
  self.assertEqual(get_liabilities(source(values),END),60)
 def test_cycles_and_missing_components(self):
  self.assertIsNone(get_assets(source({}),END))
  self.assertIsNone(get_liabilities(source(dict(LiabilitiesCurrent=10)),END))
 def test_nested_interest_formula(self):
  data=source(dict(InterestIncomeOperating=15,InterestIncomeExpenseNet=5,InterestExpenseNonoperating=20))
  self.assertEqual(get_interest_expense(data,'2025-01-01',END),30)
 def test_currency_and_dimension_selection(self):
  data=source(dict(AssetsCurrent=10,AssetsNoncurrent=20))
  data.records[1]['is_dimensioned']=True
  self.assertIsNone(get_assets(data,END))
 def test_no_calculation_attachments_requested(self):
  instance=SimpleNamespace(content='instance')
  adapter=SimpleNamespace(has_instance_document=True,get=lambda name:instance)
  filing=SimpleNamespace(attachments=object(),accession_no='test')
  with patch('edgar.xbrl.xbrl.XBRLAttachments',return_value=adapter),patch('value_retrieval.source.parse_source',return_value='prepared') as parse:
   self.assertEqual(from_filing(filing,1),'prepared')
   parse.assert_called_once_with('instance',cik=1)
