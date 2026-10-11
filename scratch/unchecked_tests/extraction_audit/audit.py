"""Read-only filing investigation; writes evidence, never production ratios."""
import json
from pathlib import Path
import sys

import pandas as pd
from edgar import Company

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from quick_setup.setup_sec_identity import setup_sec_identity
from quick_setup.get_calculated_value import standard_concept

OUT = Path(__file__).resolve().parent
setup_sec_identity()
for ticker, cik in [('AMD',2488),('AAPL',320193),('MSFT',789019),('WMT',104169),('JPM',19617),('BRK-B',1067983)]:
    periods = set()
    for filing in Company(cik).get_filings(form='10-K', amendments=False):
        end = str(filing.period_of_report)[:10]
        if not filing.period_of_report or end in periods:
            continue
        periods.add(end)
        dest = OUT / f'{ticker}-{end}.json'
        if not dest.exists():
            xb = filing.obj().financials.xb
            annual = [p for p in xb.reporting_periods if p['type']=='duration' and p.get('period_type')=='Annual' and p['end_date']==end]
            start = annual[0]['start_date'] if annual else None
            facts = xb.query(include_contexts=True).to_dataframe()
            mask = (facts.period_instant.astype(str).str[:10]==end) | ((facts.period_start.astype(str).str[:10]==start)&(facts.period_end.astype(str).str[:10]==end))
            selected = facts[mask]
            cols = ['concept','numeric_value','value','is_dimensioned','entity_identifier','context_ref','period_instant','period_start','period_end','unit_ref']
            rows = json.loads(selected[cols].to_json(orient='records'))
            for row in rows:
                if isinstance(row['value'], str) and len(row['value']) > 500:
                    row['value'] = row['value'][:500]
                    row['text_preview_truncated'] = True
            trees = {role:[dict(parent=standard_concept(a.parent_id),child=standard_concept(a.child_id),weight=a.weight) for a in tree.all_arcs] for role,tree in xb.calculation_trees.items()}
            presentations = {}
            for role,tree in xb.presentation_trees.items():
                if 'us-gaap:Assets' not in {standard_concept(x) for x in tree.all_nodes}:
                    continue
                presentations[role] = [dict(concept=standard_concept(n.element_id),parent=standard_concept(n.parent) if n.parent else None,label=n.standard_label,abstract=n.is_abstract,children=[standard_concept(c) for c in n.children]) for n in tree.all_nodes.values()]
            dest.write_text(json.dumps(dict(ticker=ticker,cik=cik,end=end,start=start,accession=filing.accession_no,facts=rows,calculations=trees,presentations=presentations),indent=2))
        print(f'{ticker} {end}: evidence saved',flush=True)
        if len(periods)==(1 if ticker in ['JPM','BRK-B'] else 5):
            break
