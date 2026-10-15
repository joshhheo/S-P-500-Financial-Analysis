"""Edgar filing facts and the metadata used to select them."""
from collections import defaultdict
from dataclasses import dataclass
import re

from edgar.xbrl.parsers import InstanceParser

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
# Reviewed concepts used by direct retrieval and explicit accounting formulas.
INSTANT_CONCEPTS = {
    'us-gaap:Assets',
    'us-gaap:AssetsCurrent',
    'us-gaap:AssetsNoncurrent',
    'us-gaap:CommitmentsAndContingencies',
    'us-gaap:Liabilities',
    'us-gaap:LiabilitiesAndStockholdersEquity',
    'us-gaap:LiabilitiesCurrent',
    'us-gaap:LiabilitiesNoncurrent',
    'us-gaap:MinorityInterest',
    'us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount',
    'us-gaap:StockholdersEquity',
    'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
    'us-gaap:TemporaryEquityCarryingAmountAttributableToParent',
    'us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests',
}

DURATION_CONCEPTS = {
    'us-gaap:InterestExpense',
    'us-gaap:InterestExpenseNonoperating',
    'us-gaap:InterestExpenseOperating',
    'us-gaap:InterestIncomeExpenseNet',
    'us-gaap:InterestIncomeOperating',
    'us-gaap:OperatingIncomeLoss',
}

def period_type(concept):
    if concept in INSTANT_CONCEPTS:
        return 'instant'
    if concept in DURATION_CONCEPTS:
        return 'duration'
    return None


class FilingInstance(InstanceParser):
    """Keep the taxonomy version and apply our explicit fact-prefix policy."""
    def _extract_facts(self, root):
        self.taxonomy_namespace = root.nsmap.get('us-gaap')
        # Check the spelling in the filing before Edgar normalizes aliases.
        # Only US GAAP financial facts and DEI metadata are in this reader's scope.
        for element in list(root):
            if element.get('contextRef') and (
                element.prefix not in ('us-gaap', 'dei')
                or (element.prefix == 'us-gaap' and not element.tag.startswith('{http://fasb.org/us-gaap/'))
                or (element.prefix == 'dei' and not re.match(r'\{https?://xbrl.sec.gov/dei/', element.tag))
            ):
                root.remove(element)
            elif element.get('contextRef') and element.prefix == 'us-gaap':
                self.taxonomy_namespace = element.nsmap['us-gaap']
        super()._extract_facts(root)


@dataclass
class Source:
    year: str
    cik: str
    records: list
    units: dict
    accession: str = ''

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
            if all(facts[concept] == {value} for concept, value in required.items()):
                starts.add(start)
        if len(starts) != 1:
            return None
        return starts.pop()

    def currencies(self, end, start=None):
        currencies = set()
        for row in self.records:
            if row['is_dimensioned'] or row['entity_identifier'] != self.cik:
                continue
            if row['period_instant'] != end and (row['period_start'], row['period_end']) != (start, end):
                continue
            if period_type(row['concept']) and row['value']:
                unit = self.units.get(row['unit_ref'])
                if unit:
                    currencies.add(unit)
        return sorted(currencies)

    def reporting_currencies(self, end):
        values = {r['value'] for r in self.records
                  if r['concept'] == 'dei:EntityReportingCurrencyISOCode'
                  and not r['is_dimensioned'] and r['entity_identifier'] == self.cik
                  and r['period_end'] == end and r['value']}
        return values


def parse_source(instance, *, cik, accession=''):
    parsed = FilingInstance(contexts={}, facts={}, units={}, footnotes={},
                            calculation_trees={}, entity_info={},
                            reporting_periods=[], context_period_map={})
    parsed.parse_instance_content(instance)
    supported_namespaces = {'http://fasb.org/us-gaap/' + release: year
                            for year, release in TAXONOMY_RELEASES.items()}
    year = supported_namespaces.get(parsed.taxonomy_namespace)
    if year is None:
        return None
    cik = str(int(cik))
    contexts = read_contexts(parsed)
    # Only reviewed monetary concepts use these units. In a compliant filing
    # their simple measure is an ISO currency (XBRL 2.1 section 4.8.2).
    units = {key: unit['measure'].strip().split(':')[-1] for key, unit in parsed.units.items()
             if unit['type'] == 'simple'}
    records = read_facts(parsed, contexts)
    return Source(year, cik, records, units, accession=accession)


def read_contexts(parsed):
    """Edgar supplies entity, dates and explicit/typed segment dimensions.

    SEC-compliant contexts do not use scenario elements (Guide 8.5).
    """
    return {
        key: dict(entity_identifier=str(int(context.entity['identifier'])),
                  is_dimensioned=bool(context.dimensions),
                  period_instant=context.period.get('instant'),
                  period_start=context.period.get('startDate'),
                  period_end=context.period.get('endDate'))
        for key, context in parsed.contexts.items()
    }


def read_facts(parsed, contexts):
    """Adapt Edgar objects to the fields used by selection; never reread fact XML."""
    records = []
    dei_concepts = {'dei:DocumentType', 'dei:DocumentFiscalPeriodFocus',
                    'dei:DocumentPeriodEndDate', 'dei:EntityReportingCurrencyISOCode'}
    for fact in parsed.facts.values():
        # The prefix policy already admitted only US GAAP/DEI facts. Edgar may
        # choose another declared alias for the same namespace internally.
        local = fact.element_id.split(':', 1)[-1]
        concept = 'dei:' + local if 'dei:' + local in dei_concepts else 'us-gaap:' + local
        if period_type(concept) is None and concept not in dei_concepts:
            continue
        context = contexts[fact.context_ref]
        # All reviewed US GAAP concepts are monetary: valid numeric content is
        # either a number or nil. An empty string is never interpreted as zero.
        records.append(dict(context, concept=concept, context_ref=fact.context_ref,
            value=fact.value, nil=concept.startswith('us-gaap:') and fact.value == '',
            unit_ref=fact.unit_ref, decimals=fact.decimals, fact_id=fact.fact_id))
    return records


def from_filing(filing, cik):
    """Read filing attachments only. Does not write files or touch a database."""
    from edgar.xbrl.xbrl import XBRLAttachments
    attachments = filing.attachments
    adapter = XBRLAttachments(attachments)
    if not adapter.has_instance_document:
        attachments = filing.homepage.attachments
        adapter = XBRLAttachments(attachments)
    if not adapter.has_instance_document:
        return None
    instance = adapter.get('instance')
    return parse_source(instance.content, cik=cik, accession=filing.accession_no)
