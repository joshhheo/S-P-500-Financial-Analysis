"""Read official sources; all writes are confined to this scratch directory."""
import hashlib
import json
import os
from pathlib import Path
import time

from dotenv import load_dotenv
from lxml import etree
import requests

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
load_dotenv(ROOT / '.env')
client = requests.Session()
client.headers['User-Agent'] = os.environ['SEC_user_agent']
manifest = []

def fetch(url, name):
    path = OUT / name
    if not path.exists():
        response = client.get(url, timeout=45)
        response.raise_for_status()
        path.write_bytes(response.content)
        time.sleep(.25)
    content = path.read_bytes()
    manifest.append(dict(url=url, file=name, sha256=hashlib.sha256(content).hexdigest()))
    return content

for year in range(2021, 2027):
    for suffix, ext in [('-doc', 'xml'), ('', 'xsd')]:
        fetch(f'https://xbrl.fasb.org/us-gaap/{year}/elts/us-gaap{suffix}-{year}{"-01-31" if year == 2021 else ""}.{ext}',
              f'gaap{year}{suffix}.{ext}')
    print('taxonomy', year, flush=True)

for name, url in [
    ('guide.pdf', 'https://www.sec.gov/files/edgar/xbrl-guide.pdf'),
    ('faq.html', 'https://www.sec.gov/data-research/structured-data/office-structured-disclosure-staff-observations-guidance-trends/staff-interpretations-faqs-related-interactive-data-disclosure'),
    ('accepted.html', 'https://www.sec.gov/data-research/structured-data/taxonomies-schemas/standard-taxonomies'),
    ('operating-companies.html', 'https://www.sec.gov/data-research/structured-data/taxonomies-schemas/standard-taxonomies/operating-companies'),
]:
    fetch(url, name)

versions = []
for path in sorted((OUT.parent / 'extraction_audit').glob('*-*.json')):
    saved = json.loads(path.read_text())
    ticker, end = saved['ticker'], saved['end']
    latest = OUT.parent / 'selection_audit' / path.name
    if latest.exists():
        url = json.loads(latest.read_text())['source']
    else:
        document = ticker.lower() + '-' + end.replace('-', '') + '.htm'
        if ticker == 'MSFT' and end == '2022-06-30':
            document = 'msft-10k_20220630.htm'
        url = f"https://www.sec.gov/Archives/edgar/data/{saved['cik']}/{saved['accession'].replace('-', '')}/{document}"
    try:
        raw = fetch(url, path.stem + '.htm')
        doc = etree.fromstring(raw, etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True))
        versions.append(dict(ticker=ticker, end=end, accession=saved['accession'], source=url,
                             gaap_namespace=doc.nsmap.get('us-gaap'),
                             schema_refs=doc.xpath('//*[local-name()="schemaRef"]/@*[local-name()="href"]')))
        print(ticker, end, doc.nsmap.get('us-gaap'), flush=True)
    except Exception as error:
        versions.append(dict(ticker=ticker,end=end,source=url,error=str(error)))
        print(ticker,end,type(error).__name__,flush=True)
(OUT / 'filing_versions.json').write_text(json.dumps(versions, indent=2)+'\n')
(OUT / 'source_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
