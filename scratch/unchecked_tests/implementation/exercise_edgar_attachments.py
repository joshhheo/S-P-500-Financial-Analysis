"""Compare the edgar attachment shortcut with direct parsing of 22 archived filings.

Original SEC documents are real evidence. Attachment objects are an offline
adapter harness with their content supplied locally; no network or database runs.
"""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from edgar.attachments import Attachment, Attachments
from value_retrieval.source import from_filing, parse_source

results = []
for row in json.loads((HERE / 'instance_manifest.json').read_text()):
    saved = json.loads((HERE.parent / 'extraction_audit' / f"{row['ticker']}-{row['end']}.json").read_text())
    attachments = []
    raw_documents = []
    instance = None
    documents = []
    for index, document in enumerate(row['documents']):
        filename = document['file'].split('__', 1)[1]
        content = (HERE / document['file']).read_text()
        assert hashlib.sha256(content.encode()).hexdigest() == document['sha256']
        if filename.endswith('_htm.xml'):
            kind = 'XML'
            instance = content
        else:
            kind = 'EX-101.SCH' if filename.endswith('.xsd') else 'EX-101.CAL'
            raw_documents.append(content)
        item = Attachment(str(index), 'saved SEC document', filename, False, urlparse(document['url']).path, kind, None)
        item.content = content
        attachments.append(item)
        documents.append(dict(url=document['url'], sha256=document['sha256']))
    filing = SimpleNamespace(attachments=Attachments([], attachments, []), accession_no=row['accession'])
    actual = from_filing(filing, saved['cik'])
    expected = parse_source(instance, raw_documents, cik=saved['cik'], accession=row['accession'], documents=documents)
    assert actual == expected, (row['ticker'], row['end'])
    results.append(dict(ticker=row['ticker'], period_end=row['end'], parsed_source_identical=True))

baseline = json.loads((HERE.parent / 'full_review/baseline_hashes.json').read_text())
csvs = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
        for name, expected in baseline.items() if name.startswith('data/')}
assert all(csvs.values())
result = dict(filings=results, production_csvs_unchanged=csvs, live_pipeline_run=False,
              live_database_access=False, network_used=False)
(HERE / 'edgar_shortcuts_comparison.json').write_text(json.dumps(result, indent=2) + '\n')
print(f'All {len(results)} archived filing sources match exactly through the edgar attachment path.')
