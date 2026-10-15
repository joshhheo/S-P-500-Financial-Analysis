"""Real archived regression against the pre-removal disabled-linkbase baseline."""
import json
import sys
import zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'src'))
from edgar.xbrl import XBRL
from value_retrieval.get_reporting_period import get_annual_start
from value_retrieval.get_assets import get_assets
from value_retrieval.get_liabilities import get_liabilities
from value_retrieval.get_operating_income import get_operating_income
from value_retrieval.get_interest_expense import get_interest_expense
from calculations.debt_to_asset_ratio import calculate_debt_to_assets
from calculations.interest_coverage_ratio import calculate_interest_coverage
from table_data.generate_ratios import filing_ratio
baseline=json.loads((HERE/'linkbase_dependency_results.json').read_text())['filings']
rows=[]
for entry in json.loads((HERE/'instance_manifest.json').read_text()):
 instance=next(d for d in entry['documents'] if d['file'].endswith('_htm.xml'))
 source=XBRL()
 with zipfile.ZipFile(HERE/'filing_documents.zip') as documents:
  source.parser.parse_instance_content(documents.read(instance['file']).decode())
 end=entry['end'];start=get_annual_start(source,end)
 result={}
 result['USD']=dict(assets=get_assets(source,end),liabilities=get_liabilities(source,end),operating_income=get_operating_income(source,start,end),interest_expense=get_interest_expense(source,start,end))
 result['ratios']=dict(debt_to_assets=filing_ratio(calculate_debt_to_assets,source,end)[0],interest_coverage=filing_ratio(calculate_interest_coverage,source,start,end)[0])
 result=json.loads(json.dumps(result,default=str))
 expected=next(r['disabled'] for r in baseline if (r['ticker'],r['end'])==(entry['ticker'],end))
 assert result==expected,(entry['ticker'],end,result,expected)
 rows.append(dict(ticker=entry['ticker'],end=end,values=result))
(HERE/'simple_retrieval_results.json').write_text(json.dumps(rows,indent=2)+'\n')
print(f'{len(rows)} archived filings match the frozen disabled-linkbase baseline.')
