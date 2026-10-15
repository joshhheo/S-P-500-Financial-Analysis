"""Reproduce the historical broad index in scratch; production no longer uses it."""
import gzip
import hashlib
import json
from pathlib import Path
from lxml import etree

ROOT = Path(__file__).resolve().parents[3]
INPUT = ROOT / 'scratch/unchecked_tests/full_review'
versions = {}
for year in range(2021,2027):
    schema = INPUT / f'gaap{year}.xsd'
    documentation = INPUT / f'gaap{year}-doc.xml'
    tree = etree.parse(str(schema))
    concepts = {}
    for element in tree.xpath('//*[local-name()="element"]'):
        if element.get('type') != 'xbrli:monetaryItemType' or element.get('abstract') == 'true':
            continue
        concepts[element.get('name')] = dict(
            period=element.get('{http://www.xbrl.org/2003/instance}periodType'))
    suffix = '-01-31' if year == 2021 else ''
    versions[str(year)] = dict(namespace=tree.getroot().get('targetNamespace'),
        schema=f'https://xbrl.fasb.org/us-gaap/{year}/elts/us-gaap-{year}{suffix}.xsd',
        documentation=f'https://xbrl.fasb.org/us-gaap/{year}/elts/us-gaap-doc-{year}{suffix}.xml',
        schema_sha256=hashlib.sha256(schema.read_bytes()).hexdigest(),
        documentation_sha256=hashlib.sha256(documentation.read_bytes()).hexdigest(),
        concepts=concepts)
destination = Path(__file__).with_name('standard_concepts_rebuilt.json.gz')
destination.write_bytes(gzip.compress(json.dumps(versions,sort_keys=True,separators=(',',':')).encode(),mtime=0))
print(destination, destination.stat().st_size)
