"""Refresh raw unit/accuracy evidence for six constituent filings, read-only SEC access."""
import csv
from decimal import Decimal
import json
import os
from pathlib import Path
import time

from dotenv import load_dotenv
import httpx
from lxml import etree

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SAMPLES = ['AMD', 'AAPL', 'MSFT', 'WMT', 'JPM', 'BRK-B']


def collect():
    load_dotenv(ROOT / '.env')
    members = {}
    with (ROOT / 'data/company_status.csv').open() as stream:
        for row in csv.DictReader(stream):
            members[row['ticker']] = row
    with httpx.Client(headers={'User-Agent': os.environ['SEC_user_agent']}, timeout=60, follow_redirects=True) as client:
        for ticker in SAMPLES:
            member = members[ticker]
            paths = sorted((OUT.parent / 'extraction_audit').glob(ticker + '-*.json'))
            saved = json.loads(paths[-1].read_text())
            assert int(member['cik']) == saved['cik']
            destination = OUT / paths[-1].name
            if destination.exists():
                print(ticker, 'already collected', flush=True)
                continue
            response = client.get(f"https://data.sec.gov/submissions/CIK{saved['cik']:010d}.json")
            response.raise_for_status()
            recent = response.json()['filings']['recent']
            index = recent['accessionNumber'].index(saved['accession'])
            document = recent['primaryDocument'][index]
            assert recent['form'][index] == '10-K'
            url = f"https://www.sec.gov/Archives/edgar/data/{saved['cik']}/{saved['accession'].replace('-', '')}/{document}"
            time.sleep(0.2)
            response = client.get(url)
            response.raise_for_status()
            doc = etree.fromstring(response.content, parser=etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True))
            units = {}
            for node in doc.xpath('//*[local-name()="unit"]'):
                units[node.get('id')] = etree.tostring(node, encoding='unicode')
            contexts = {}
            for node in doc.xpath('//*[local-name()="context"]'):
                instant = node.xpath('.//*[local-name()="instant"]/text()')
                start = node.xpath('.//*[local-name()="startDate"]/text()')
                end = node.xpath('.//*[local-name()="endDate"]/text()')
                dimensions = node.xpath('.//*[local-name()="explicitMember" or local-name()="typedMember"]')
                contexts[node.get('id')] = dict(instant=instant, start=start, end=end, dimensioned=bool(dimensions))
            facts = []
            skipped = {}
            for tag in doc.xpath('//*[local-name()="nonFraction"]'):
                concept = tag.get('name', '')
                context = contexts[tag.get('contextRef')]
                if context['dimensioned']:
                    continue
                if context['instant'] != [saved['end']]:
                    if context['start'] != [saved['start']] or context['end'] != [saved['end']]:
                        continue
                if tag.get('{http://www.w3.org/2001/XMLSchema-instance}nil') == 'true':
                    continue
                raw = ''.join(tag.itertext()).strip()
                transform = tag.get('format', '').split(':')[-1]
                if transform in ('num-dot-decimal', 'numdotdecimal', ''):
                    number = Decimal(raw.replace(',', '').replace('\u00a0', '').replace(' ', ''))
                elif transform in ('numdash', 'zerodash', 'fixed-zero'):
                    number = Decimal(0)
                else:
                    skipped[transform] = skipped.get(transform, 0) + 1
                    continue
                number *= Decimal(10) ** int(tag.get('scale', '0'))
                if tag.get('sign') == '-':
                    number = -number
                facts.append(dict(concept=concept, value=str(number), decimals=tag.get('decimals'),
                                  context_ref=tag.get('contextRef'), unit_ref=tag.get('unitRef'),
                                  instant=context['instant'], start=context['start'], end=context['end']))
            result = dict(ticker=ticker, cik=saved['cik'], accession=saved['accession'],
                          source=url, start=saved['start'], end=saved['end'],
                          membership=member, units=units, facts=facts, unsupported_transforms=skipped)
            destination.write_text(json.dumps(result, indent=2) + '\n')
            print(ticker, len(facts), 'facts; unsupported transforms:', skipped, flush=True)
            time.sleep(0.2)


if __name__ == '__main__':
    collect()
