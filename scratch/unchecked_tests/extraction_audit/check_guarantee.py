"""Recheck all complete equations and exhibit the limit of rounded inputs."""
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from scratch.unchecked_tests.extraction_audit.analyze import value

root=Path(__file__).resolve().parent
checks=[]
for path in sorted(root.glob('*-*.json')):
    d=json.loads(path.read_text())
    for target in ['Assets','Liabilities','OperatingIncomeLoss','InterestExpense']:
        reported=value(d,'us-gaap:'+target)
        if reported is None:continue
        for role,arcs in d['calculations'].items():
            children=[a for a in arcs if a['parent']=='us-gaap:'+target]
            if not children:continue
            if any(not a['child'].startswith('us-gaap:') for a in children):continue
            vals=[value(d,a['child']) for a in children]
            if any(v is None for v in vals):continue
            total=sum(a['weight']*v for a,v in zip(children,vals))
            checks.append(dict(ticker=d['ticker'],date=d['end'],target=target,role=role,reported=reported,calculated=total,equal=total==reported))

# Two different ledgers can produce the same correctly rounded component facts.
# Units are millions. This is a constructed numerical example, not an SEC filing.
round_million=lambda x:Decimal(x).quantize(Decimal('1'),rounding=ROUND_HALF_UP)
worlds=[('1.1','1.1'),('1.4','1.4')]
reported_components=[tuple(round_million(v) for v in pair) for pair in worlds]
reported_totals=[round_million(sum(Decimal(v) for v in pair)) for pair in worlds]
assert reported_components[0]==reported_components[1]==(Decimal(1),Decimal(1))
assert reported_totals==[Decimal(2),Decimal(3)]
# Gross interest cannot be identified from a net amount alone.
interest_worlds=[(120,20),(150,50)]
assert [expense-income for expense,income in interest_worlds]==[100,100]
assert interest_worlds[0][0]!=interest_worlds[1][0]
amd=json.loads((root/'AMD-2025-12-27.json').read_text())
assert value(amd,'us-gaap:LiabilitiesNoncurrent') is None
current=value(amd,'us-gaap:LiabilitiesCurrent')
known_liabilities=13927000000
assert known_liabilities-current==4472000000
summary={'omission_counterexample':{'company':'AMD','date':'2025-12-27','noncurrent_subtotal':None,'known_noncurrent_components':4472000000},'complete_role_equations_checked':len(checks),'matched':sum(c['equal'] for c in checks),'mismatches':[c for c in checks if not c['equal']], 'by_target':{t:sum(c['target']==t for c in checks) for t in ['Assets','Liabilities','OperatingIncomeLoss','InterestExpense']},'net_interest_counterexample':{'net_expense':100,'possible_gross_expenses':[120,150]},'rounding_counterexample':{'reported_components_millions':[1,1],'possible_rounded_totals_millions':[2,3],'conclusion':'Component facts do not uniquely determine a missing total at the same reporting precision.'}}
(root/'guarantee_checks.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
