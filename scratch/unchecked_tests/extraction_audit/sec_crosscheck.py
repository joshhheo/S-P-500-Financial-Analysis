import json
import os
from pathlib import Path
import sys
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[3] / 'src'))
from setup_sec_identity import setup_sec_identity
from analyze import value
setup_sec_identity()
root=Path(__file__).resolve().parent
checks=[]
for cik in [2488,320193,789019,104169,19617,1067983]:
    response=httpx.get(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010}.json',headers={'User-Agent':os.environ['SEC_user_agent']},timeout=60)
    response.raise_for_status()
    facts=response.json()['facts']['us-gaap']
    for path in root.glob('*-*.json'):
        d=json.loads(path.read_text())
        if d['cik']!=cik:continue
        for concept in ['Assets','Liabilities']:
            reported=value(d,'us-gaap:'+concept)
            api=[f['val'] for f in facts.get(concept,{}).get('units',{}).get('USD',[]) if f['accn']==d['accession'] and f['end']==d['end']]
            if reported is not None and api:
                assert reported in api,(d['ticker'],d['end'],concept)
            checks.append(dict(ticker=d['ticker'],end=d['end'],concept=concept,parsed=reported,sec_api_values=api))
    print(cik,'SEC API checked',flush=True)
(root/'sec_crosscheck.json').write_text(json.dumps(checks,indent=2))
print('Matched numeric facts:',sum(x['parsed'] is not None and bool(x['sec_api_values']) for x in checks))
