"""Download official sample instances and calculation linkbases into scratch only."""
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.parse import urljoin
import requests
from dotenv import load_dotenv

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
load_dotenv(ROOT / '.env')
client = requests.Session()
client.headers['User-Agent'] = os.environ['SEC_user_agent']
manifest = []
for row in json.loads((OUT.parent / 'full_review/filing_versions.json').read_text()):
    base = row['source'].rsplit('/', 1)[0] + '/'
    name = row['ticker'] + '-' + row['end']
    index = client.get(base + 'index.json', timeout=45)
    index.raise_for_status()
    files = [item['name'] for item in index.json()['directory']['item']]
    instance = [f for f in files if f.endswith('_htm.xml')]
    schemas = [f for f in files if f.endswith('.xsd')]
    calculations = [f for f in files if f.endswith(('_cal.xml','-cal.xml','.cal.xml'))]
    assert len(instance) == 1, (name, instance)
    docs = []
    for filename in instance + schemas + calculations:
        dest = OUT / (name + '__' + filename)
        url = urljoin(base,filename)
        if not dest.exists():
            response = client.get(url,timeout=45)
            response.raise_for_status()
            dest.write_bytes(response.content)
            time.sleep(.2)
        docs.append(dict(file=dest.name,url=url,sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
    manifest.append(dict(row,documents=docs))
    (OUT / 'instance_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(name, len(docs), flush=True)
