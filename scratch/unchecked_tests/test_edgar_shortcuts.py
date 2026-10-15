"""Constructed offline attachments test; no downloaded data or live database."""
from types import SimpleNamespace
import unittest
from edgar.attachments import Attachment, Attachments
from test_source_evidence import instance, fact, END, SCHEMA
from value_retrieval.source import from_filing
from value_retrieval.get_value import get_value as retrieve


def attachment(name, kind, content):
    item = Attachment('1', 'constructed fixture', name, False,
                      '/Archives/constructed/' + name, kind, None)
    item.content = content
    return item


def link(child):
    return f'''<linkbase xmlns="http://www.xbrl.org/2003/linkbase" xmlns:xlink="http://www.w3.org/1999/xlink">
    <calculationLink xlink:role="role" xlink:type="extended">
      <loc xlink:label="parent" xlink:href="{SCHEMA}#us-gaap_Assets"/>
      <loc xlink:label="child" xlink:href="{SCHEMA}#us-gaap_{child}"/>
      <calculationArc xlink:arcrole="http://www.xbrl.org/2003/arcrole/summation-item"
       xlink:from="parent" xlink:to="child" weight="1"/>
    </calculationLink></linkbase>'''


class EdgarShortcutTests(unittest.TestCase):
    def test_query_keeps_all_calculation_files_without_selecting_one_per_type(self):
        raw = attachment('instance.xml', 'XML', instance(
            fact('AssetsCurrent', '10') + fact('AssetsNoncurrent', '20')))
        first = attachment('part1.xml', 'EX-101.CAL', link('AssetsCurrent'))
        second = attachment('part2.xml', 'EX-101.CAL', link('AssetsNoncurrent'))
        schema = attachment('schema.xsd', 'EX-101.SCH', '<schema/>')
        ignored = attachment('presentation.xml', 'EX-101.PRE', '<unused/>')
        # Exercise both document lists, and a repeated attachment URL.
        attachments = Attachments([first], [raw, first, second, schema, ignored], [])
        filing = SimpleNamespace(attachments=attachments, accession_no='constructed')
        source = from_filing(filing, 2488)
        self.assertEqual(set(source.equations[('role', 'us-gaap:Assets')]),
                         {('us-gaap:AssetsCurrent', 1), ('us-gaap:AssetsNoncurrent', 1)})
        self.assertEqual(len(source.documents), 4)
        self.assertEqual(retrieve(source, 'us-gaap:Assets', END), 30)

    def test_identified_duplicate_facts_keep_exact_text_precision_and_nil(self):
        from value_retrieval.source import parse_source
        xml = instance(
            '<us-gaap:Assets id="a" contextRef="i" unitRef="u" decimals="INF">9007199254740993</us-gaap:Assets>'
            '<us-gaap:Assets id="b" contextRef="i" unitRef="u" decimals="0">9007199254740993</us-gaap:Assets>'
            '<us-gaap:Liabilities id="c" contextRef="i" unitRef="u" xsi:nil="true"/>')
        source = parse_source(xml, cik=2488)
        self.assertEqual([row['fact_id'] for row in source.records], ['a', 'b', 'c'])
        self.assertEqual([row['decimals'] for row in source.records], ['INF', '0', None])
        self.assertEqual(retrieve(source, 'us-gaap:Assets', END), 9007199254740993)
        self.assertTrue(source.records[2]['nil'])

    def test_edgar_explicit_and_typed_dimensions_are_not_consolidated(self):
        from value_retrieval.source import parse_source
        members = [
            '<d:explicitMember dimension="company:Axis">company:Member</d:explicitMember>',
            '<d:typedMember dimension="company:Axis"><company:Domain>1</company:Domain></d:typedMember>',
            '<d:typedMember dimension="company:Axis"><company:Domain xsi:nil="true"/></d:typedMember>',
        ]
        for member in members:
            segment = ('<segment xmlns:d="http://xbrl.org/2006/xbrldi" '
                       'xmlns:company="https://company.example/taxonomy">' + member + '</segment>')
            xml = instance(fact('Assets', '25')).replace('</entity>', segment + '</entity>')
            self.assertIsNone(retrieve(parse_source(xml, cik=2488), 'us-gaap:Assets', END))

    def test_local_currency_namespace_and_divided_units(self):
        from value_retrieval.source import parse_source
        xml = instance(fact('Assets', '25')).replace(
            '<measure>iso:USD</measure>',
            '<measure xmlns:money="http://www.xbrl.org/2003/iso4217">money:USD</measure>')
        self.assertEqual(retrieve(parse_source(xml, cik=2488), 'us-gaap:Assets', END), 25)
        divided = xml.replace(
            '<measure xmlns:money="http://www.xbrl.org/2003/iso4217">money:USD</measure>',
            '<divide><unitNumerator><measure>iso:USD</measure></unitNumerator>'
            '<unitDenominator><measure>shares</measure></unitDenominator></divide>')
        self.assertIsNone(retrieve(parse_source(divided, cik=2488), 'us-gaap:Assets', END))

    def test_unlisted_and_default_prefixes_are_excluded(self):
        from value_retrieval.source import parse_source, Source
        namespace = Source('2026', '2488', [], {}).namespace
        for tag in [
            f'<local:Assets xmlns:local="{namespace}"',
            f'<Assets xmlns="{namespace}"',
        ]:
            close = tag.split()[0][1:]
            xml = instance(f'{tag} contextRef="i" unitRef="u" decimals="INF">9007199254740993</{close}>')
            xml = xml.replace(f'xmlns:us-gaap="{namespace}"', '')
            self.assertIsNone(retrieve(parse_source(xml, cik=2488), 'us-gaap:Assets', END))

    def test_namespace_shadowing_does_not_turn_custom_fact_into_standard(self):
        from value_retrieval.source import parse_source
        xml = instance(
            fact('Assets', '25') +
            '<us-gaap:Assets xmlns:us-gaap="https://company.example/taxonomy" '
            'contextRef="i" unitRef="u" decimals="0">999</us-gaap:Assets>')
        self.assertEqual(retrieve(parse_source(xml, cik=2488), 'us-gaap:Assets', END), 25)

    def test_idless_duplicate_nil_zero_and_absence_remain_distinct(self):
        from value_retrieval.source import parse_source
        nil = '<us-gaap:Assets contextRef="i" unitRef="u" xsi:nil="true"/>'
        self.assertIsNone(retrieve(parse_source(instance(nil), cik=2488), 'us-gaap:Assets', END))
        self.assertIsNone(retrieve(parse_source(instance(''), cik=2488), 'us-gaap:Assets', END))
        zero = parse_source(instance(fact('Assets', '0')), cik=2488)
        self.assertEqual(retrieve(zero, 'us-gaap:Assets', END), 0)
        conflict = parse_source(instance(fact('Assets', '0') + nil), cik=2488)
        self.assertIsNone(retrieve(conflict, 'us-gaap:Assets', END))

    def test_correct_prefix_can_be_declared_on_the_fact(self):
        from value_retrieval.source import parse_source, Source
        namespace = Source('2026', '2488', [], {}).namespace
        xml = instance('').replace(f'xmlns:us-gaap="{namespace}"', '')
        xml = xml.replace('</xbrl>', f'<us-gaap:Assets xmlns:us-gaap="{namespace}" '
                          'contextRef="i" unitRef="u" decimals="0">25</us-gaap:Assets></xbrl>')
        self.assertEqual(retrieve(parse_source(xml, cik=2488), 'us-gaap:Assets', END), 25)

    def test_root_alias_cannot_be_normalized_into_an_accepted_fact(self):
        from value_retrieval.source import parse_source, Source
        namespace = Source('2026', '2488', [], {}).namespace
        xml = instance('<g:Assets contextRef="i" unitRef="u" decimals="0">999</g:Assets>'
                       + fact('Assets', '25'))
        # Alias declaration order must not change the accepted us-gaap fact.
        for changed in (
            xml.replace('<xbrl ', f'<xbrl xmlns:g="{namespace}" ', 1),
            xml.replace(f'xmlns:us-gaap="{namespace}"',
                        f'xmlns:us-gaap="{namespace}" xmlns:g="{namespace}"'),
        ):
            self.assertEqual(retrieve(parse_source(changed, cik=2488), 'us-gaap:Assets', END), 25)

    def test_dei_namespace_cannot_use_financial_prefix_or_an_alias(self):
        from value_retrieval.source import parse_source
        for prefix in ('metadata', 'us-gaap'):
            metadata = (f'<{prefix}:DocumentType xmlns:{prefix}="http://xbrl.sec.gov/dei/2026" '
                        f'contextRef="d">10-K</{prefix}:DocumentType>')
            source = parse_source(instance(fact('Assets', '25') + metadata), cik=2488)
            self.assertFalse(any(r['concept'] == 'dei:DocumentType' for r in source.records))
