"""Exact SEC extracted-instance input and effective filed calculation relationships.

No unit, taxonomy year, entity, or annual start is inferred from a ticker/name.
XML entity expansion and network access are disabled during parsing.
"""
from collections import defaultdict
from decimal import Decimal
from dataclasses import dataclass, field
import hashlib
import re
from urllib.parse import urlparse

from lxml import etree
from edgar.xbrl.parsers import XBRLParser
from value_retrieval.get_value import SelectionError
from value_retrieval.get_assets import SUPPORTED_CONCEPTS as ASSET_CONCEPTS
from value_retrieval.get_liabilities import SUPPORTED_CONCEPTS as LIABILITY_CONCEPTS
from value_retrieval.get_equity import SUPPORTED_CONCEPTS as EQUITY_CONCEPTS
from value_retrieval.get_interest_expense import SUPPORTED_CONCEPTS as INTEREST_CONCEPTS, CONCEPTS_FROM_2024
from value_retrieval.get_operating_income import SUPPORTED_CONCEPTS as OPERATING_CONCEPTS

# XML namespace prefixes used to read attributes and elements.
X = '{http://www.w3.org/1999/xlink}'
I = '{http://www.xbrl.org/2003/instance}'
L = '{http://www.xbrl.org/2003/linkbase}'
ISO = 'http://www.xbrl.org/2003/iso4217'


# Hardcoded identifiers for taxonomy versions reviewed before runtime.
# Namespace/schema URLs below are compared as strings, never downloaded.
# Definitions, source hashes and version differences are documented in README.
TAXONOMY_RELEASES = {
    '2021': '2021-01-31',
    '2022': '2022',
    '2023': '2023',
    '2024': '2024',
    '2025': '2025',
    '2026': '2026',
}
INSTANT_CONCEPTS = ASSET_CONCEPTS | LIABILITY_CONCEPTS | EQUITY_CONCEPTS
DURATION_CONCEPTS = INTEREST_CONCEPTS | OPERATING_CONCEPTS


def period_type(concept, year):
    """The reviewed concept's period, or None when outside supported coverage."""
    if year not in TAXONOMY_RELEASES or (year < '2024' and concept in CONCEPTS_FROM_2024):
        return None
    if concept in INSTANT_CONCEPTS:
        return 'instant'
    if concept in DURATION_CONCEPTS:
        return 'duration'
    return None


def parse_xml(content):
    if isinstance(content, str):
        content = content.encode()
    return etree.fromstring(content, etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True))


def expanded_name(node, text):
    if not text:
        return ''
    if ':' in text:
        prefix, local = text.split(':', 1)
    else:
        prefix, local = None, text
    return '{' + node.nsmap.get(prefix, '') + '}' + local


@dataclass
class Source:
    year: str
    cik: str
    records: list
    units: dict
    equations: dict = field(default_factory=dict)  # (role,parent) -> [(child,weight)]
    accession: str = ''
    documents: list = field(default_factory=list)
    calculation_issue: str | None = None

    @property
    def namespace(self):
        return 'http://fasb.org/us-gaap/' + TAXONOMY_RELEASES[self.year]

    @property
    def schema(self):
        return f'https://xbrl.fasb.org/us-gaap/{self.year}/elts/us-gaap-{TAXONOMY_RELEASES[self.year]}.xsd'

    def annual_start(self, end):
        """DEI facts in the required context, not a duration-length heuristic."""
        starts = set()
        by_period = defaultdict(lambda: defaultdict(set))
        for row in self.records:
            if (not row['is_dimensioned'] and row['entity_identifier'] == self.cik
                    and row['period_end'] == end and row['period_start']):
                by_period[row['period_start']][row['concept']].add(row['value'])
        required = {'dei:DocumentPeriodEndDate': end, 'dei:DocumentType': '10-K',
                    'dei:DocumentFiscalPeriodFocus': 'FY'}
        for start, facts in by_period.items():
            if any(len(facts[concept]) > 1 for concept in required):
                raise SelectionError('Conflicting DEI annual context facts', 'ambiguous_period')
            if all(facts[concept] == {value} for concept, value in required.items()):
                starts.add(start)
        if len(starts) != 1:
            raise SelectionError('Required annual context is absent or ambiguous', 'ambiguous_period')
        return starts.pop()

    def currencies(self, end, start=None):
        currencies = set()
        for row in self.records:
            if row['is_dimensioned'] or row['entity_identifier'] != self.cik:
                continue
            if row['period_instant'] != end and (row['period_start'], row['period_end']) != (start, end):
                continue
            if period_type(row['concept'], self.year) and row['value']:
                unit = self.units.get(row['unit_ref'])
                if unit:
                    currencies.add(unit)
        return sorted(currencies)

    def reporting_currency(self, end):
        values = {r['value'] for r in self.records
                  if r['concept'] == 'dei:EntityReportingCurrencyISOCode'
                  and not r['is_dimensioned'] and r['entity_identifier'] == self.cik
                  and r['period_end'] == end and r['value']}
        if len(values) > 1:
            raise SelectionError('Conflicting reporting currencies', 'incompatible_basis')
        return next(iter(values)) if values else None


def parse_source(instance, calculations=(), *, cik, accession='', documents=()):
    root = parse_xml(instance)
    supported_namespaces = {}
    for year, release in TAXONOMY_RELEASES.items():
        # Match the identifier written in the filing; this does not open a URL.
        supported_namespaces['http://fasb.org/us-gaap/' + release] = year
    namespaces = set(root.nsmap.values()).intersection(supported_namespaces)
    if len(namespaces) != 1:
        raise SelectionError('Missing, unsupported or multiple US GAAP taxonomy versions', 'unsupported_taxonomy')
    namespace = namespaces.pop()
    year = supported_namespaces[namespace]
    cik = str(int(cik))
    parsed = XBRLParser()
    parsed.parse_instance_content(instance)
    contexts = read_contexts(parsed, root)
    units = read_units(root)
    records = read_facts(parsed, root, contexts, namespace)
    source = Source(year, cik, records, units, accession=accession, documents=list(documents))
    calculations = list(calculations)
    source.equations = effective_equations(calculations, source)
    # A supplied fragment of a referenced linkbase cannot establish a complete
    # equation. Loading unsupported DTS arrangements is a coverage gap.
    supplied = set()
    for document in documents:
        filename = urlparse(document.get('url', '')).path.rsplit('/', 1)[-1]
        supplied.add(filename)
    if documents:
        for content in calculations:
            for reference in parse_xml(content).iter(L+'linkbaseRef'):
                if reference.get(X+'role') == 'http://www.xbrl.org/2003/role/calculationLinkbaseRef':
                    filename = urlparse(reference.get(X+'href', '')).path.rsplit('/', 1)[-1]
                    if filename not in supplied:
                        source.calculation_issue = 'Referenced calculation document was not supplied'

    return source



def read_contexts(parsed, root):
    """Use Edgar's company/dates; supplement dimensions outside its segment reader."""
    dimensioned = {
        node.get('id') for node in root.findall(I+'context')
        if node.xpath('.//*[local-name()="explicitMember" or local-name()="typedMember"]')
    }
    return {
        key: dict(entity_identifier=str(int(context.entity['identifier'])),
                  is_dimensioned=bool(context.dimensions) or key in dimensioned,
                  period_instant=context.period.get('instant'),
                  period_start=context.period.get('startDate'),
                  period_end=context.period.get('endDate'))
        for key, context in parsed.contexts.items()
        if context.entity.get('scheme') == 'http://www.sec.gov/CIK'
    }


def read_units(root):
    """Resolve monetary units to their ISO currency codes."""
    units = {}
    for node in root.findall(I+'unit'):
        measures = node.findall(I+'measure')
        if len(measures) == 1 and node.find(I+'divide') is None:
            measure = expanded_name(measures[0], measures[0].text)
            if measure.startswith('{'+ISO+'}'):
                currency = measure.split('}', 1)[1]
                if re.fullmatch('[A-Z]{3}', currency):
                    units[node.get('id')] = currency
    return units


def read_facts(parsed, root, contexts, namespace):
    """Use Edgar facts by XML ID, supplementing namespace identity and nil.

    Facts without IDs cannot be joined to XML metadata by ID. Read those directly
    rather than assume the library's duplicate ordering or namespace prefix.
    """
    facts_by_id = {fact.fact_id: fact for fact in parsed.facts.values() if fact.fact_id}
    records = []
    for node in root.iter():
        context = contexts.get(node.get('contextRef'))
        if context is None or not isinstance(node.tag, str):
            continue
        qname = etree.QName(node)
        if qname.namespace == namespace:
            concept = 'us-gaap:' + qname.localname
        elif qname.namespace and re.fullmatch(r'https?://xbrl.sec.gov/dei/\d{4}(q[1-4]|-\d\d-\d\d)?', qname.namespace):
            concept = 'dei:' + qname.localname
        else:
            continue
        nil = node.get('{http://www.w3.org/2001/XMLSchema-instance}nil') in ('true', '1')
        fact = facts_by_id.get(node.get('id'))
        value = fact.value if fact else ''.join(node.itertext()).strip()
        records.append(dict(context, concept=concept, context_ref=node.get('contextRef'),
            value='' if nil else value, nil=nil,
            unit_ref=fact.unit_ref if fact else node.get('unitRef'),
            decimals=fact.decimals if fact else node.get('decimals'), fact_id=node.get('id')))
    return records


def effective_equations(contents, source):
    """Resolve duplicate/prohibited arcs across supplied calculation documents.

    Source locators must name the official schema for this filing's version.
    A custom locator remains custom even if its fragment imitates a standard ID.
    """
    grouped = defaultdict(list)
    expected_path = urlparse(source.schema).path
    for content in contents:
        root = parse_xml(content)
        for link in root.iter(L+'calculationLink'):
            role = link.get(X+'role')
            locators = defaultdict(list)
            for loc in link.findall(L+'loc'):
                href = loc.get(X+'href', '')
                parsed = urlparse(href)
                name = href
                if (parsed.hostname in ('xbrl.fasb.org', 'fasb.org', 'www.fasb.org')
                        and parsed.path == expected_path and parsed.fragment.startswith('us-gaap_')):
                    name = 'us-gaap:' + parsed.fragment[len('us-gaap_'):]
                locators[loc.get(X+'label')].append(name)
            for arc in link.findall(L+'calculationArc'):
                arcrole = arc.get(X+'arcrole')
                if arcrole not in ('http://www.xbrl.org/2003/arcrole/summation-item',
                                   'https://xbrl.org/2023/arcrole/summation-item'):
                    source.calculation_issue = 'Unsupported calculation arcrole'
                    continue
                weight = Decimal(arc.get('weight'))
                if weight not in (Decimal(1), Decimal(-1)):
                    source.calculation_issue = 'Unsupported calculation weight'
                    continue
                for parent in locators[arc.get(X+'from')]:
                    for child in locators[arc.get(X+'to')]:
                        grouped[(role, arcrole, parent, child, int(weight))].append(
                            (int(arc.get('priority', '0')), arc.get('use') == 'prohibited'))
    equations = defaultdict(list)
    for (role, arcrole, parent, child, weight), arcs in grouped.items():
        priority = max(p for p, _ in arcs)
        if any(prohibited for p, prohibited in arcs if p == priority):
            continue
        network = role
        if not arcrole.endswith('2003/arcrole/summation-item'):
            network = role + ' [Calculations 1.1]'
        equations[(network, parent)].append((child, weight))
    return dict(equations)


def from_filing(filing, cik):
    """Read filing attachments only. Does not write files or touch a database."""
    from edgar.xbrl.xbrl import XBRLAttachments
    attachments = filing.attachments
    adapter = XBRLAttachments(attachments)
    if not adapter.has_instance_document:
        attachments = filing.homepage.attachments
        adapter = XBRLAttachments(attachments)
    if not adapter.has_instance_document:
        raise SelectionError('SEC extracted instance unavailable', 'missing_instance')
    instance = adapter.get('instance')
    contents, documents = [], []
    seen = set()
    # Select documents only: edgar does not choose facts or apply metric fallbacks here.
    calculation_documents = attachments.query(
        "document_type in ['EX-101.CAL', 'EX-101.SCH']"
    )
    for attachment in [instance] + list(calculation_documents):
        if attachment.url in seen:
            continue
        seen.add(attachment.url)
        content = attachment.content
        raw = content.encode() if isinstance(content, str) else content
        documents.append(dict(url=attachment.url, sha256=hashlib.sha256(raw).hexdigest()))
        if attachment is instance:
            instance_content = content
        else:
            contents.append(content)
    return parse_source(instance_content, contents, cik=cik, accession=filing.accession_no, documents=documents)
