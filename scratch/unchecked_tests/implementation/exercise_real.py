"""Offline production extraction over original SEC XML; no pipeline or DB call."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from value_retrieval.source import parse_source
from calculations.debt_to_asset_ratio import calculate_debt_to_assets
from calculations.interest_coverage_ratio import calculate_interest_coverage

from table_data.generate_ratios import filing_ratio

OUT = Path(__file__).resolve().parent
results = []
for row in json.loads((OUT/'instance_manifest.json').read_text()):
    saved = json.loads((OUT.parent/'extraction_audit'/f"{row['ticker']}-{row['end']}.json").read_text())
    files = row['documents']
    instance = next(f for f in files if f['file'].endswith('_htm.xml'))
    calculations = [(OUT/f['file']).read_bytes() for f in files if f is not instance]
    source = parse_source((OUT/instance['file']).read_bytes(),calculations,cik=saved['cik'],
                          accession=row['accession'],documents=files)
    start = source.annual_start(row['end'])
    assert start == saved['start'], (row['ticker'],start,saved['start'])
    debt = filing_ratio(calculate_debt_to_assets, source,row['end'])
    interest = filing_ratio(calculate_interest_coverage, source,start,row['end'])
    result = dict(ticker=row['ticker'],end=row['end'],start=start,debt=dict(value=None if debt[0] is None else str(debt[0]),status=debt[1]),interest=dict(value=None if interest[0] is None else str(interest[0]),status=interest[1]))
    results.append(result)
    print(row['ticker'],row['end'],*debt,*interest,flush=True)
(OUT/(sys.argv[1] if len(sys.argv) > 1 else 'real_minimal_results.json')).write_text(json.dumps(results,indent=2)+'\n')
