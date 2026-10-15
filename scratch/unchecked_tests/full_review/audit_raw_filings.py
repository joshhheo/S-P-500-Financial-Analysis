"""Independently decode saved SEC Inline XBRL; compare with saved pipeline facts.

Only explicitly supported transformations are decoded. Unsupported occurrences
are counted and retained as coverage limitations, never coerced to zero.
No live pipeline, network, or database calls occur here.
"""
import csv
from decimal import Decimal
import json
from pathlib import Path
import sys

from lxml import etree

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(OUT.parent))
from filing_fixtures import financials
from legacy_api import get_assets
from legacy_api import get_liabilities
from legacy_api import get_operating_income
from legacy_api import get_interest_expense

with (ROOT / 'data/company_status.csv').open() as stream:
    members = {row['ticker']: row for row in csv.DictReader(stream)}
versions = json.loads((OUT / 'filing_versions.json').read_text())
results = []
for source in versions:
    name = source['ticker'] + '-' + source['end']
    saved = json.loads((OUT.parent / 'extraction_audit' / (name + '.json')).read_text())
    assert int(members[source['ticker']]['cik']) == saved['cik']
    doc = etree.parse(str(OUT / (name + '.htm')), etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True))
    contexts = {}
    for node in doc.xpath('//*[local-name()="context"]'):
        def content(local):
            values = node.xpath('.//*[local-name()=$name]/text()', name=local)
            return values[0] if values else None
        contexts[node.get('id')] = dict(
            period_instant=content('instant'), period_start=content('startDate'),
            period_end=content('endDate'), entity_identifier=content('identifier'),
            is_dimensioned=bool(node.xpath('.//*[local-name()="explicitMember" or local-name()="typedMember"]')))
    units = {}
    for node in doc.xpath('//*[local-name()="unit"]'):
        measures = []
        for measure in node.xpath('.//*[local-name()="measure"]'):
            prefix, local = measure.text.split(':')
            measures.append('{' + measure.nsmap[prefix] + '}' + local)
        units[node.get('id')] = measures
    facts = []
    unsupported = {}
    for node in doc.xpath('//*[local-name()="nonFraction"]'):
        concept = node.get('name', '')
        if not concept.startswith('us-gaap:'):
            continue
        context = contexts[node.get('contextRef')]
        if context['period_instant'] != saved['end']:
            if (context['period_start'], context['period_end']) != (saved['start'], saved['end']):
                continue
        raw = ''.join(node.itertext()).strip()
        transform = node.get('format', '').split(':')[-1]
        nil = node.get('{http://www.w3.org/2001/XMLSchema-instance}nil') in ('true','1')
        number = None
        if not nil:
            if transform in ('num-dot-decimal','numdotdecimal',''):
                number = Decimal(raw.replace(',', '').replace('\u00a0','').replace(' ',''))
            elif transform in ('numdash','zerodash','fixed-zero'):
                number = Decimal(0)
            else:
                unsupported[transform] = unsupported.get(transform,0) + 1
                continue
            number *= Decimal(10) ** int(node.get('scale','0'))
            if node.get('sign') == '-':
                number = -number
        row = dict(context, concept=concept, context_ref=node.get('contextRef'),
                   unit_ref=node.get('unitRef'), decimals=node.get('decimals'),
                   numeric_value=number, value='' if nil else str(number))
        facts.append(row)
    fresh = financials(dict(facts=facts, calculations=saved['calculations']))
    old = financials(saved)
    values = {}
    for metric, function, args in [
        ('assets', get_assets, [saved['end']]),
        ('liabilities', get_liabilities, [saved['end']]),
        ('operating_income', get_operating_income, [saved['start'], saved['end']]),
        ('interest_expense', get_interest_expense, [saved['start'], saved['end']])]:
        actual, previous = function(fresh, *args), function(old, *args)
        assert actual == previous, (name, metric, actual, previous)
        values[metric] = actual
    direct_checks = []
    for metric, concept in [('assets','Assets'),('liabilities','Liabilities'),
                            ('operating_income','OperatingIncomeLoss'),('interest_expense','InterestExpense')]:
        matching = [r for r in facts if not r['is_dimensioned'] and r['concept'] == 'us-gaap:' + concept and r['numeric_value'] is not None]
        if matching:
            most_precise = max(matching, key=lambda row: Decimal(row['decimals']))
            assert Decimal(str(values[metric])) == most_precise['numeric_value']
            direct_checks.append(concept)
    annual_candidates = sorted({c['period_start'] for c in contexts.values()
                                if c['period_end'] == saved['end'] and not c['is_dimensioned']
                                and c['period_start'] is not None})
    results.append(dict(filing=name, accession=saved['accession'], source=source['source'],
                        taxonomy=source['gaap_namespace'], membership=members[source['ticker']],
                        facts_decoded=len(facts), unsupported_transforms=unsupported,
                        values=values, direct_raw_checks=direct_checks,
                        undimensioned_duration_starts=annual_candidates,
                        selected_entity_ids=sorted({r['entity_identifier'] for r in facts if not r['is_dimensioned']}),
                        selected_unit_measures=sorted({m for r in facts if not r['is_dimensioned'] for m in units.get(r['unit_ref'],[])})))
    print(name, values, flush=True)
(OUT / 'raw_filing_results.json').write_text(json.dumps(results,indent=2)+'\n')
print('Matched', len(results)*4, 'metric values; independent direct checks:', sum(len(r['direct_raw_checks']) for r in results))
