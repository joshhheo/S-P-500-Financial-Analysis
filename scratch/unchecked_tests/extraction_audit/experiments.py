"""Evidence tests only. Reviewed concept classes are not universal fallback lists."""
import copy
import csv
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
from edgar.xbrl.models import CalculationArc, CalculationTree

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from quick_setup.get_calculated_value import get_calculated_value
from scratch.unchecked_tests.extraction_audit.analyze import lookup, value

ROOT=Path(__file__).resolve().parent
U='us-gaap:'
EQUITY={U+'StockholdersEquity',U+'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',U+'MinorityInterest'}
TEMP={U+'RedeemableNoncontrollingInterestEquityCarryingAmount',U+'TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests'}
LIABILITY={U+x for x in ['Liabilities','LiabilitiesCurrent','LiabilitiesNoncurrent','LongTermDebtNoncurrent','OperatingLeaseLiabilityNoncurrent','FinanceLeaseLiabilityNoncurrent','DeferredIncomeTaxLiabilitiesNet','DeferredIncomeTaxesAndOtherLiabilitiesNoncurrent','OtherLiabilitiesNoncurrent']}
CAPTION=U+'CommitmentsAndContingencies'

def snapshot(d):
    class Query:
        def by_concept(self, concept, exact):
            assert exact
            self.concept=concept
            return self
        def to_dataframe(self):
            return pd.DataFrame([f for f in d['facts'] if f['concept'].replace('us-gaap_',U)==self.concept])
    def query(include_contexts=False):
        assert include_contexts
        return Query()
    return SimpleNamespace(xb=SimpleNamespace(query=query,entity_info={'identifier':str(d['cik'])},calculation_trees={r:CalculationTree(role_uri=r,definition='',root_element_id=a[0]['parent'],all_arcs=[CalculationArc(parent_id=x['parent'],child_id=x['child'],weight=x['weight']) for x in a]) for r,a in d['calculations'].items() if a}))

def reconstruct(d):
    """Experiment: classify complete filed balance-sheet children, then subtract equity.

    The target Liabilities value is never read. Unknown concepts and missing
    monetary components stop this experiment. Only the reviewed caption pattern
    is excluded. Classification comes from exact reviewed concepts, not labels.
    """
    for role,nodes in d['presentations'].items():
        concepts={n['concept'] for n in nodes}
        if not {U+'Assets',U+'LiabilitiesAndStockholdersEquity'} <= concepts:
            continue
        arcs=[a for a in d['calculations'].get(role,[]) if a['parent']==U+'LiabilitiesAndStockholdersEquity']
        if not arcs:continue
        equity=0; liability_sum=0; has_target=False; has_equity=False; caption=False
        for a in arcs:
            child=a['child']; amount=value(d,child)
            if child==CAPTION:
                rows=lookup(d,child)
                if child not in concepts or not rows or any(f['numeric_value'] is not None or f['value'] not in [None,''] for f in rows):break
                caption=True
                continue
            if child not in EQUITY|TEMP|LIABILITY or a['weight']!=1:break
            if child==U+'Liabilities':
                has_target=True
                continue
            if amount is None:break
            if child in EQUITY|TEMP:
                equity+=amount;has_equity=True
            else:liability_sum+=amount
        else:
            combined=value(d,U+'LiabilitiesAndStockholdersEquity')
            if combined is not None and has_equity and (has_target or liability_sum):
                return dict(liabilities=combined-equity,component_sum=None if has_target else liability_sum,role=role,caption=caption)
    return None


def main():
    rows=[]; controls=0; asset_checks=0; liability_checks=0; op_checks=0
    datasets=[json.loads(p.read_text()) for p in sorted(ROOT.glob('*-*.json'))]
    for d in datasets:
        fin=snapshot(d)
        for target in ['Assets','Liabilities','OperatingIncomeLoss']:
            actual=value(d,U+target)
            computed=get_calculated_value(fin,U+target,d['end'],d['start'] if target=='OperatingIncomeLoss' else None)
            if actual is not None and computed is not None:
                assert computed==actual,(d['ticker'],d['end'],target,computed,actual)
                if target=='Assets':asset_checks+=1
                elif target=='Liabilities':liability_checks+=1
                else:op_checks+=1
        hidden=copy.deepcopy(d)
        hidden['facts']=[f for f in hidden['facts'] if f['concept'].replace('us-gaap_',U)!=U+'Liabilities']
        result=reconstruct(hidden)
        direct=value(d,U+'Liabilities')
        if result:
            if direct is not None:
                assert result['liabilities']==direct
                controls+=1
            if result['component_sum'] is not None:
                assert result['component_sum']==result['liabilities']
        rows.append(dict(ticker=d['ticker'],end=d['end'],accession=d['accession'],assets=value(d,U+'Assets'),direct_liabilities=direct,reconstructed_liabilities=result['liabilities'] if result else None,component_sum=result['component_sum'] if result else None,role=result['role'] if result else None,permanent_equity_only_overstatement=value(d,U+'RedeemableNoncontrollingInterestEquityCarryingAmount')))
    # Negative tests operate on real WMT data, changing exactly one condition.
    wmt=next(d for d in datasets if d['ticker']=='WMT' and d['end']=='2026-01-31')
    for concept in [U+'RedeemableNoncontrollingInterestEquityCarryingAmount',U+'FinanceLeaseLiabilityNoncurrent',CAPTION]:
        mutated=copy.deepcopy(wmt)
        mutated['facts']=[f for f in mutated['facts'] if f['concept']!=concept]
        assert reconstruct(mutated) is None,concept
    for change in ['custom','unknown_standard','numeric_caption','wrong_entity','wrong_date','dimensioned']:
        mutated=copy.deepcopy(wmt)
        if change in ['custom','unknown_standard']:
            new='wmt:Unreviewed' if change=='custom' else U+'Unreviewed'
            for arcs in mutated['calculations'].values():
                for a in arcs:
                    if a['parent']==U+'LiabilitiesAndStockholdersEquity' and a['child']==U+'FinanceLeaseLiabilityNoncurrent':a['child']=new
        else:
            for f in mutated['facts']:
                if change=='numeric_caption' and f['concept']==CAPTION:f['numeric_value']=1
                if change=='wrong_entity' and f['concept']==U+'FinanceLeaseLiabilityNoncurrent':f['entity_identifier']='1'
                if change=='wrong_date' and f['concept']==U+'FinanceLeaseLiabilityNoncurrent':f['period_instant']='2020-01-31'
                if change=='dimensioned' and f['concept']==U+'FinanceLeaseLiabilityNoncurrent':f['is_dimensioned']=True
        assert reconstruct(mutated) is None,change
    with (ROOT/'results.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
    summary=dict(filings=len(datasets),direct_assets_matched_by_calculation=asset_checks,direct_liabilities_matched_by_calculation=liability_checks,direct_operating_income_matched_by_calculation=op_checks,residual_rule_matches_to_hidden_direct_totals=controls,missing_liabilities_reconstructed=sum(r['direct_liabilities'] is None and r['reconstructed_liabilities'] is not None for r in rows),negative_cases_passed=9)
    (ROOT/'test_summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
    for r in rows:print(r['ticker'],r['end'],'direct',r['direct_liabilities'],'experiment',r['reconstructed_liabilities'])

if __name__=='__main__':main()
