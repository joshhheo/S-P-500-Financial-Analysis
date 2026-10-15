"""Record actual ISO non-USD facts, distinct from custom noncurrency units."""
import json
import sys
from pathlib import Path
from lxml import etree
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'src'))
from value_retrieval.source import INSTANT_CONCEPTS,DURATION_CONCEPTS
X='{http://www.xbrl.org/2003/instance}'
rows=[]
for filing in json.loads((HERE/'instance_manifest.json').read_text()):
 doc=next(d for d in filing['documents'] if d['file'].endswith('_htm.xml'))
 root=etree.fromstring((HERE/doc['file']).read_bytes())
 units={}
 for u in root.findall(X+'unit'):
  m=u.find(X+'measure')
  if m is None or ':' not in m.text:continue
  prefix,currency=m.text.split(':',1)
  if m.nsmap.get(prefix)=='http://www.xbrl.org/2003/iso4217' and currency!='USD':units[u.get('id')]=currency
 contexts={c.get('id'):c for c in root.findall(X+'context')}
 for fact in root:
  if fact.get('unitRef') not in units:continue
  q=etree.QName(fact);concept=('us-gaap:' if q.namespace.startswith('http://fasb.org/us-gaap/') else str(q.namespace)+':')+q.localname
  context=contexts[fact.get('contextRef')]
  dimensioned=any(etree.QName(e).localname in ('explicitMember','typedMember') for e in context.iter())
  rows.append(dict(ticker=filing['ticker'],end=filing['end'],url=doc['url'],concept=concept,value=fact.text,currency=units[fact.get('unitRef')],context=fact.get('contextRef'),dimensioned=dimensioned,current_reviewed_concept=concept in INSTANT_CONCEPTS|DURATION_CONCEPTS))
(HERE/'foreign_currency_evidence.json').write_text(json.dumps(rows,indent=2)+'\n')
print('Foreign currency facts:',len(rows))
print('Current reviewed concepts:',[r for r in rows if r['current_reviewed_concept']])
for ticker,end in [('MSFT','2025-06-30'),('WMT','2024-01-31'),('AAPL','2024-09-28')]:
 print(json.dumps([r for r in rows if (r['ticker'],r['end'])==(ticker,end)],indent=2))
