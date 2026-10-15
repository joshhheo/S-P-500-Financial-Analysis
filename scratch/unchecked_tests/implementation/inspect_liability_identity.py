"""Inspect direct identity inputs in the original AMD/WMT archived instances."""
import json
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'src'))
from value_retrieval.source import parse_source
from value_retrieval.get_value import get_reported_amount
concepts=['Assets','Liabilities','LiabilitiesCurrent','LiabilitiesNoncurrent','StockholdersEquity','MinorityInterest','StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest','TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests','TemporaryEquityCarryingAmountAttributableToParent','RedeemableNoncontrollingInterestEquityCarryingAmount']
rows=[]
for row in json.loads((HERE/'instance_manifest.json').read_text()):
 if row['ticker'] not in ('AMD','WMT'): continue
 saved=json.loads((HERE.parent/'extraction_audit'/f"{row['ticker']}-{row['end']}.json").read_text())
 doc=next(d for d in row['documents'] if d['file'].endswith('_htm.xml'))
 source=parse_source((HERE/doc['file']).read_bytes(),cik=saved['cik'])
 values={c:get_reported_amount(source,'us-gaap:'+c,row['end'],currency='USD') for c in concepts}
 rows.append(dict(ticker=row['ticker'],end=row['end'],values=values))
(HERE/'liability_identity_inputs.json').write_text(json.dumps(rows,default=str,indent=2)+'\n')
print(json.dumps(rows,default=str,indent=2))
