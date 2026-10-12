"""Helpers for historical SEC/equation comparisons; production checks live in test_*.py."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
TARGETS=['Assets','Liabilities','OperatingIncomeLoss','InterestExpense','InterestExpenseOperating','InterestExpenseNonoperating','InterestIncomeOperating','InterestIncomeExpenseNet','StockholdersEquity','StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest','MinorityInterest','TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests']
def lookup(d,concept):
    return [f for f in d['facts'] if f['concept'].replace('us-gaap_', 'us-gaap:')==concept and not f['is_dimensioned'] and str(f['entity_identifier']).lstrip('0')==str(d['cik']) and (f['period_instant']==d['end'] or (f['period_start']==d['start'] and f['period_end']==d['end']))]
def value(d,concept):
    return next((f['numeric_value'] for f in lookup(d,concept) if f['numeric_value'] is not None),None)
if __name__=='__main__':
 for path in sorted(ROOT.glob('*-*.json')):
    d=json.loads(path.read_text()); print('\n',path.stem,d['accession'])
    print({t:value(d,'us-gaap:'+t) for t in TARGETS})
    for role,arcs in d['calculations'].items():
        for parent in ['Assets','Liabilities','LiabilitiesAndStockholdersEquity','InterestExpense','OperatingIncomeLoss']:
            children=[a for a in arcs if a['parent']=='us-gaap:'+parent]
            if not children:continue
            available=[(a['child'],a['weight'],value(d,a['child'])) for a in children]
            missing=[c for c,w,v in available if v is None]
            total=sum(w*v for c,w,v in available if v is not None)
            print(role.split('/')[-1],parent,'sum_known',total,'parent',value(d,'us-gaap:'+parent),'missing',missing)
            if parent=='LiabilitiesAndStockholdersEquity' and d['ticker'] in ['AMD','WMT']:print(available)
