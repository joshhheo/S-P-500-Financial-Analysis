"""Exact XML boundary and accounting regressions. XML examples are constructed.

The 22-filing test separately uses original SEC documents and frozen independent
inline-XBRL results from the prior review; it makes no network requests.
"""
import hashlib
import json
from decimal import Decimal
from pathlib import Path
import sys
import unittest
from table_data.generate_ratios import filing_ratio
from urllib.parse import urlparse
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from value_retrieval.source import parse_source, Source, period_type
from value_retrieval.get_value import get_value as retrieve
from calculations.debt_to_asset_ratio import calculate_debt_to_assets
from calculations.interest_coverage_ratio import calculate_interest_coverage

HERE=Path(__file__).parent
END='2025-12-31'
NS=Source('2026', '1', [], {}).namespace
SCHEMA=Source('2026', '1', [], {}).schema


def instance(facts, start='2025-01-01'):
    return f'''<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:us-gaap="{NS}"
        xmlns:dei="http://xbrl.sec.gov/dei/2026" xmlns:iso="http://www.xbrl.org/2003/iso4217"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <context id="i"><entity><identifier scheme="http://www.sec.gov/CIK">0000002488</identifier></entity><period><instant>{END}</instant></period></context>
        <context id="d"><entity><identifier scheme="http://www.sec.gov/CIK">0000002488</identifier></entity><period><startDate>{start}</startDate><endDate>{END}</endDate></period></context>
        <unit id="u"><measure>iso:USD</measure></unit>{facts}</xbrl>'''


def fact(concept,value,context='i',decimals='0'):
    return f'<us-gaap:{concept} contextRef="{context}" unitRef="u" decimals="{decimals}">{value}</us-gaap:{concept}>'


def calculation(arcrole,extra='',weight='1.00',custom=False):
    schema='https://example.com/company.xsd' if custom else SCHEMA
    return f'''<linkbase xmlns="http://www.xbrl.org/2003/linkbase" xmlns:xlink="http://www.w3.org/1999/xlink">
      <calculationLink xlink:role="role" xlink:type="extended">
        <loc xlink:label="a" xlink:href="{schema}#us-gaap_Assets"/>
        <loc xlink:label="c" xlink:href="{SCHEMA}#us-gaap_AssetsCurrent"/>
        <calculationArc xlink:arcrole="{arcrole}" xlink:from="a" xlink:to="c" weight="{weight}"/>{extra}
      </calculationLink></linkbase>'''


class SourceEvidenceTests(unittest.TestCase):
    def test_calc11_and_decimal_weight_lexical_forms(self):
        for arcrole in ['http://www.xbrl.org/2003/arcrole/summation-item','https://xbrl.org/2023/arcrole/summation-item']:
            source=parse_source(instance(fact('AssetsCurrent','25')),[calculation(arcrole)],cik=2488)
            self.assertEqual(retrieve(source,'us-gaap:Assets',END),25)

    def test_prohibited_arc_and_custom_schema_imitation_are_not_used(self):
        arcrole='https://xbrl.org/2023/arcrole/summation-item'
        prohibited=f'<calculationArc xmlns:xlink="http://www.w3.org/1999/xlink" xlink:arcrole="{arcrole}" xlink:from="a" xlink:to="c" weight="1.00" priority="2" use="prohibited"/>'
        for xml in [calculation(arcrole,prohibited),calculation(arcrole,custom=True)]:
            source=parse_source(instance(fact('AssetsCurrent','25')),[xml],cik=2488)
            self.assertIsNone(retrieve(source,'us-gaap:Assets',END))

    def test_exact_large_amount_and_tiny_component_survive(self):
        source=parse_source(instance(fact('AssetsCurrent','9007199254740993',decimals='INF')+
            fact('AssetsNoncurrent','0.00000000000000000001',decimals='INF')),cik=2488)
        self.assertEqual(retrieve(source,'us-gaap:Assets',END),Decimal('9007199254740993.00000000000000000001'))

    def test_nil_numeric_duplicates_conflict(self):
        source=parse_source(instance(fact('Assets','25')+
            '<us-gaap:Assets contextRef="i" unitRef="u" xsi:nil="true"/>'),cik=2488)
        self.assertIsNone(retrieve(source, 'us-gaap:Assets', END))

    def test_annual_required_context_accepts_short_year_without_length_guess(self):
        facts=''.join(f'<dei:{c} contextRef="d">{v}</dei:{c}>' for c,v in
                      [('DocumentType','10-K'),('DocumentFiscalPeriodFocus','FY'),('DocumentPeriodEndDate',END)])
        source=parse_source(instance(facts,start='2025-03-01'),cik=2488)
        self.assertEqual(source.annual_start(END),'2025-03-01')
        source.records.append(dict(source.records[0],value='10-Q'))
        self.assertIsNone(source.annual_start(END))

    def test_wrong_entity_and_dimensioned_values_are_not_consolidated(self):
        xml=instance(fact('Assets','25')).replace('0000002488','0000000001')
        source=parse_source(xml,cik=2488)
        self.assertIsNone(retrieve(source,'us-gaap:Assets',END))
        segment='<segment xmlns:d="http://xbrl.org/2006/xbrldi"><d:explicitMember dimension="company:Axis">company:Member</d:explicitMember></segment>'
        xml=instance(fact('Assets','25')).replace('</entity>',segment+'</entity>')
        self.assertIsNone(retrieve(parse_source(xml,cik=2488),'us-gaap:Assets',END))

    def test_concept_periods_use_the_documented_2026_baseline(self):
        for concept in ('InterestExpenseOperating', 'InterestExpenseNonoperating'):
            self.assertEqual(period_type('us-gaap:' + concept), 'duration')
        self.assertEqual(period_type('us-gaap:Assets'), 'instant')
        self.assertIsNone(period_type('us-gaap:UnknownConcept'))

    def test_all_original_instances_match_independent_inline_evidence(self):
        from legacy_api import get_value
        folder=HERE/'implementation'
        manifest=json.loads((folder/'instance_manifest.json').read_text())
        independent={r['filing']:r for r in json.loads((HERE/'full_review/raw_filing_results.json').read_text())}
        metric_names={'assets':'Assets','liabilities':'Liabilities','operating_income':'OperatingIncomeLoss','interest_expense':'InterestExpense'}
        count=debt_count=interest_count=0
        for row in manifest:
            with self.subTest(ticker=row['ticker'],end=row['end']):
                docs=row['documents'];raw=next(d for d in docs if d['file'].endswith('_htm.xml'))
                for doc in docs:
                    self.assertEqual(hashlib.sha256((folder/doc['file']).read_bytes()).hexdigest(),doc['sha256'])
                baseline=independent[row['ticker']+'-'+row['end']]
                source=parse_source((folder/raw['file']).read_bytes(),[(folder/d['file']).read_bytes() for d in docs if d is not raw],
                    cik=baseline['membership']['cik'],accession=row['accession'],documents=docs)
                start=source.annual_start(row['end'])
                for metric,concept in metric_names.items():
                    actual=get_value(source,'us-gaap:'+concept,row['end'],start if metric in ('operating_income','interest_expense') else None)
                    expected=baseline['values'][metric]
                    self.assertEqual(actual,None if expected is None else Decimal(str(expected)))
                    count+=1
                debt=filing_ratio(calculate_debt_to_assets, source,row['end'])
                interest=filing_ratio(calculate_interest_coverage, source,start,row['end'])
                debt_count+=debt[1]=='available';interest_count+=interest[1]=='available'
                self.assertTrue(source.documents)
        self.assertEqual((count,debt_count,interest_count),(88,22,11))

    def test_attachment_adapter_with_original_xml_and_embedded_calculations(self):
        from types import SimpleNamespace
        from edgar.attachments import Attachment, Attachments
        from value_retrieval.source import from_filing
        folder=HERE/'implementation'
        manifest=json.loads((folder/'instance_manifest.json').read_text())
        for ticker in ['AAPL','BRK-B','AMD']:
            row=next(r for r in manifest if r['ticker']==ticker)
            attachments=[]
            for index,doc in enumerate(row['documents']):
                filename=doc['file'].split('__',1)[1]
                kind='EX-101.SCH' if filename.endswith('.xsd') else ('XML' if filename.endswith('_htm.xml') else 'EX-101.CAL')
                attachment=Attachment(str(index),'saved official document',filename,False,urlparse(doc['url']).path,kind,None)
                attachment.content=(folder/doc['file']).read_text()
                attachments.append(attachment)
            full=Attachments([],attachments,[])
            # Exercise the homepage fallback used for SEC extracted instances.
            filing=SimpleNamespace(attachments=Attachments([],[],[]),homepage=SimpleNamespace(attachments=full),accession_no=row['accession'])
            cik={'AAPL':320193,'BRK-B':1067983,'AMD':2488}[ticker]
            source=from_filing(filing,cik)
            self.assertEqual(source.accession,row['accession'])
            self.assertGreater(len(source.equations),0)
            self.assertEqual(filing_ratio(calculate_debt_to_assets, source,row['end'])[1],'available')

    def test_reported_ratio_operand_precedes_its_filed_calculation(self):
        xml=instance(fact('Assets','100')+fact('AssetsCurrent','80')+fact('Liabilities','50'))
        calc=calculation('https://xbrl.org/2023/arcrole/summation-item')
        result=filing_ratio(calculate_debt_to_assets, parse_source(xml,[calc],cik=2488),END)
        self.assertEqual(result, (Decimal('0.5'), 'available'))

    def test_unloaded_referenced_calculation_document_is_not_silently_ignored(self):
        xml=instance(fact('AssetsCurrent','100'))
        calc=calculation('https://xbrl.org/2023/arcrole/summation-item')
        schema='''<schema xmlns="http://www.w3.org/2001/XMLSchema" xmlns:l="http://www.xbrl.org/2003/linkbase"
         xmlns:xlink="http://www.w3.org/1999/xlink"><annotation><appinfo><l:linkbaseRef
         xlink:role="http://www.xbrl.org/2003/role/calculationLinkbaseRef" xlink:href="missing.xml"/>
         </appinfo></annotation></schema>'''
        source=parse_source(xml,[calc,schema],cik=2488,documents=[dict(url='https://www.sec.gov/example/schema.xsd')])
        self.assertIsNone(retrieve(source,'us-gaap:Assets',END))
        self.assertIn('not supplied',source.calculation_issue)
