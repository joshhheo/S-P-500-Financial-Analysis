"""Edgar filing facts, explicit selection metadata, and effective calculations."""
from collections import defaultdict
from dataclasses import dataclass, field
import re

from edgar.xbrl.parsers import InstanceParser
from value_retrieval.get_value import SelectionError
from value_retrieval.calculation_linkbase import read_calculations

I = '{http://www.xbrl.org/2003/instance}'


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
# Reviewed parser/calculation coverage, not metric aliases or fallback formulas.
INSTANT_CONCEPTS = {
    'us-gaap:AccountsPayableCurrent',
    'us-gaap:AccountsReceivableNetCurrent',
    'us-gaap:AccruedIncomeTaxesNoncurrent',
    'us-gaap:Assets',
    'us-gaap:AssetsCurrent',
    'us-gaap:AssetsNoncurrent',
    'us-gaap:Cash',
    'us-gaap:CashAndCashEquivalentsAtCarryingValue',
    'us-gaap:CommitmentsAndContingencies',
    'us-gaap:ContractWithCustomerLiabilityNoncurrent',
    'us-gaap:DeferredIncomeTaxAssetsNet',
    'us-gaap:DeferredIncomeTaxLiabilitiesNet',
    'us-gaap:DeferredIncomeTaxesAndOtherLiabilitiesNoncurrent',
    'us-gaap:DeferredRevenueNoncurrent',
    'us-gaap:EquityMethodInvestments',
    'us-gaap:FinanceLeaseLiabilityNoncurrent',
    'us-gaap:FinanceLeaseRightOfUseAsset',
    'us-gaap:FiniteLivedIntangibleAssetsNet',
    'us-gaap:Goodwill',
    'us-gaap:IntangibleAssetsNetExcludingGoodwill',
    'us-gaap:Liabilities',
    'us-gaap:LiabilitiesAndStockholdersEquity',
    'us-gaap:LiabilitiesCurrent',
    'us-gaap:LiabilitiesNoncurrent',
    'us-gaap:LongTermDebtNoncurrent',
    'us-gaap:LongTermInvestments',
    'us-gaap:MinorityInterest',
    'us-gaap:OperatingLeaseLiabilityNoncurrent',
    'us-gaap:OperatingLeaseRightOfUseAsset',
    'us-gaap:OtherAssetsNoncurrent',
    'us-gaap:OtherLiabilitiesNoncurrent',
    'us-gaap:PropertyPlantAndEquipmentNet',
    'us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount',
    'us-gaap:StockholdersEquity',
    'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
    'us-gaap:TemporaryEquityCarryingAmountAttributableToParent',
    'us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests',
}

DURATION_CONCEPTS = {
    'us-gaap:CostOfRevenue',
    'us-gaap:FinanceLeaseInterestExpense',
    'us-gaap:ForeignCurrencyTransactionGainLossBeforeTax',
    'us-gaap:GainLossOnDerivativeInstrumentsNetPretax',
    'us-gaap:GainLossOnInvestments',
    'us-gaap:GeneralAndAdministrativeExpense',
    'us-gaap:GrossProfit',
    'us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest',
    'us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments',
    'us-gaap:InterestCostsCapitalized',
    'us-gaap:InterestCostsIncurred',
    'us-gaap:InterestExpense',
    'us-gaap:InterestExpenseNonoperating',
    'us-gaap:InterestExpenseOperating',
    'us-gaap:InterestIncomeExpenseNet',
    'us-gaap:InterestIncomeOperating',
    'us-gaap:InvestmentIncomeInterestAndDividend',
    'us-gaap:InvestmentIncomeNet',
    'us-gaap:NonoperatingIncomeExpense',
    'us-gaap:OperatingExpenses',
    'us-gaap:OperatingIncomeLoss',
    'us-gaap:OtherNonoperatingIncomeExpense',
    'us-gaap:ResearchAndDevelopmentExpense',
    'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax',
    'us-gaap:Revenues',
    'us-gaap:SellingAndMarketingExpense',
}

CONCEPTS_FROM_2024 = {
    'us-gaap:InterestExpenseNonoperating',
    'us-gaap:InterestExpenseOperating',
}



def period_type(concept, year):
    """The reviewed concept's period, or None when outside supported coverage."""
    if year not in TAXONOMY_RELEASES or (year < '2024' and concept in CONCEPTS_FROM_2024):
        return None
    if concept in INSTANT_CONCEPTS:
        return 'instant'
    if concept in DURATION_CONCEPTS:
        return 'duration'
    return None


class FilingInstance(InstanceParser):
    """Let Edgar parse once; retain namespace identities it otherwise discards.

    These two hooks depend on pinned edgartools 5.58.0. Neither changes its
    parsing rules, fact values, duplicate handling or context associations.
    """
    def _extract_facts(self, root):
        self.root = root
        self.namespaces = {prefix: uri for prefix, uri in root.nsmap.items() if prefix}
        super()._extract_facts(root)

    def _resolve_prefix(self, namespace, element, prefix_map, claimed):
        prefix = super()._resolve_prefix(namespace, element, prefix_map, claimed)
        self.namespaces[prefix] = namespace
        return prefix


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
    parsed = FilingInstance(contexts={}, facts={}, units={}, footnotes={},
                            calculation_trees={}, entity_info={},
                            reporting_periods=[], context_period_map={})
    parsed.parse_instance_content(instance)
    supported_namespaces = {}
    for year, release in TAXONOMY_RELEASES.items():
        # Match the identifier written in the filing; this does not open a URL.
        supported_namespaces['http://fasb.org/us-gaap/' + release] = year
    namespaces = set(parsed.namespaces.values()).intersection(supported_namespaces)
    if len(namespaces) != 1:
        raise SelectionError('Missing, unsupported or multiple US GAAP taxonomy versions', 'unsupported_taxonomy')
    namespace = namespaces.pop()
    year = supported_namespaces[namespace]
    cik = str(int(cik))
    contexts = read_contexts(parsed, parsed.root)
    # Only reviewed monetary concepts use these units. In a compliant filing
    # their simple measure is an ISO currency (XBRL 2.1 section 4.8.2).
    units = {key: unit['measure'].strip().split(':')[-1] for key, unit in parsed.units.items()
             if unit['type'] == 'simple'}
    records = read_facts(parsed, contexts, namespace, year)
    source = Source(year, cik, records, units, accession=accession, documents=list(documents))
    source.equations = read_calculations(calculations, source)
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


def read_facts(parsed, contexts, namespace, year):
    """Adapt Edgar objects to the fields used by selection; never reread fact XML."""
    records = []
    dei_concepts = {'DocumentType', 'DocumentFiscalPeriodFocus',
                    'DocumentPeriodEndDate', 'EntityReportingCurrencyISOCode'}
    for fact in parsed.facts.values():
        prefix, local = fact.element_id.split(':', 1)
        uri = parsed.namespaces[prefix]
        if uri == namespace:
            concept = 'us-gaap:' + local
            if period_type(concept, year) is None:
                continue
        elif (re.fullmatch(r'https?://xbrl.sec.gov/dei/\d{4}(q[1-4]|-\d\d-\d\d)?', uri)
              and local in dei_concepts):
            concept = 'dei:' + local
        else:
            continue
        context = contexts.get(fact.context_ref)
        if context is None:
            continue
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
        documents.append(dict(url=attachment.url))
        if attachment is instance:
            instance_content = content
        else:
            contents.append(content)
    return parse_source(instance_content, contents, cik=cik, accession=filing.accession_no, documents=documents)
