"""Read original Apple tags and save precision evidence; never run the pipeline."""
import json
import os
from decimal import Decimal
from pathlib import Path
import sys

import httpx
from dotenv import load_dotenv
from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
LINK = 'https://www.sec.gov/Archives/edgar/data/320193/000032019321000105/aapl-20210925.htm'


def collect():
    load_dotenv(ROOT / '.env')
    response = httpx.get(LINK, headers={'User-Agent': os.environ['SEC_user_agent']}, timeout=60)
    response.raise_for_status()
    document = etree.fromstring(response.content, parser=etree.XMLParser(resolve_entities=False, no_network=True))
    contexts = {}
    for node in document.xpath('//*[local-name()="context"]'):
        instants = node.xpath('.//*[local-name()="instant"]/text()')
        starts = node.xpath('.//*[local-name()="startDate"]/text()')
        ends = node.xpath('.//*[local-name()="endDate"]/text()')
        dimensions = node.xpath('.//*[local-name()="explicitMember" or local-name()="typedMember"]')
        contexts[node.get('id')] = {'instant': instants, 'start': starts, 'end': ends, 'dimensioned': bool(dimensions)}
    facts = []
    for tag in document.xpath('//*[local-name()="nonFraction"]'):
        concept = tag.get('name', '')
        if not concept.startswith('us-gaap:'):
            continue
        context = contexts[tag.get('contextRef')]
        if context['dimensioned']:
            continue
        if context['instant'] != ['2021-09-25']:
            if context['start'] != ['2020-09-27'] or context['end'] != ['2021-09-25']:
                continue
        if tag.get('{http://www.w3.org/2001/XMLSchema-instance}nil') == 'true':
            continue
        raw = ''.join(tag.itertext()).strip()
        transform = tag.get('format', '').split(':')[-1]
        if transform != 'num-dot-decimal':
            continue
        number = Decimal(raw.replace(',', '')) * Decimal(10) ** int(tag.get('scale', '0'))
        if tag.get('sign') == '-':
            number = -number
        facts.append({'concept': concept, 'value': str(number), 'decimals': tag.get('decimals'),
                      'context_ref': tag.get('contextRef'), 'unit_ref': tag.get('unitRef'),
                      'raw_text': raw, 'scale': tag.get('scale'), 'id': tag.get('id')})
    result = {'source': LINK, 'accession': '0000320193-21-000105',
              'scope': 'Undimensioned standard numeric facts for 2021 instant or full annual duration; num-dot-decimal transform only',
              'facts': facts}
    output = Path(__file__).with_name('duplicate_precision_evidence.json')
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(f'Saved {len(facts)} original fact tags with decimals to {output}')


if __name__ == '__main__':
    collect()
