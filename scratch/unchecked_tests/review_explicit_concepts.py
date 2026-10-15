"""Offline source verification for the explicit production allowlist.

Uses archived official FASB schemas/documentation and checks their recorded hashes.
Writes review data only under scratch/unchecked_tests. It never generates code.
"""
import hashlib
import json
from pathlib import Path
import sys
from lxml import etree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'src'))
from value_retrieval.source import INSTANT_CONCEPTS, DURATION_CONCEPTS, TAXONOMY_RELEASES, Source, period_type


def review():
    folder = HERE / 'full_review'
    manifest = {item['file']: item for item in json.loads((folder / 'source_manifest.json').read_text())}
    versions = {}
    for year in TAXONOMY_RELEASES:
        filenames = [f'gaap{year}.xsd', f'gaap{year}-doc.xml']
        for filename in filenames:
            assert hashlib.sha256((folder / filename).read_bytes()).hexdigest() == manifest[filename]['sha256']
        schema = etree.parse(str(folder / filenames[0]))
        doc = etree.parse(str(folder / filenames[1]))
        source = Source(year, '1', [], {})
        assert schema.getroot().get('targetNamespace') == source.namespace
        assert manifest[filenames[0]]['url'] == source.schema
        elements = {e.get('name'): e for e in schema.xpath('//*[local-name()="element"]')}
        definitions = {e.get('{http://www.w3.org/1999/xlink}label')[4:]: e.text
                       for e in doc.xpath('//*[local-name()="label"]')}
        concepts = {}
        for concept in sorted(INSTANT_CONCEPTS | DURATION_CONCEPTS):
            name = concept.removeprefix('us-gaap:')
            element = elements.get(name)
            actual_period = None if element is None else element.get('{http://www.xbrl.org/2003/instance}periodType')
            if year == '2026':
                assert actual_period == period_type(concept), (year, concept, actual_period)
            if element is not None:
                assert element.get('type') == 'xbrli:monetaryItemType', (year, concept)
                assert element.get('abstract') != 'true'
                assert definitions.get(name), (year, concept)
            concepts[name] = dict(period=actual_period, definition=definitions.get(name))
        versions[year] = dict(sources=[manifest[f] for f in filenames], concepts=concepts)
    differences = []
    for year, version in versions.items():
        for name, details in version['concepts'].items():
            latest = versions['2026']['concepts'][name]
            if details != latest:
                differences.append(dict(year=year, concept=name, older=details, version_2026=latest))
    return dict(concept_count=len(INSTANT_CONCEPTS | DURATION_CONCEPTS),
                versions=versions, differences_from_2026=differences)


if __name__ == '__main__':
    result = review()
    (HERE / 'implementation/explicit_concept_review.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f"Verified {result['concept_count']} explicit concepts against the 2026 baseline; compared six official releases.")
    for item in result['differences_from_2026']:
        print(item['year'], item['concept'], item['older']['definition'], '=>', item['version_2026']['definition'])
