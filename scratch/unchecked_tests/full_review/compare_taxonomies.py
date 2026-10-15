"""Compare every explicitly named production concept against official releases."""
import ast
import json
from pathlib import Path
from lxml import etree

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
names = {'CommitmentsAndContingencies'}
for path in (ROOT / 'src/value_retrieval').glob('*.py'):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value.startswith('us-gaap:') and len(node.value) > 8:
                names.add(node.value.split(':')[1])
    if path.name == 'get_liabilities.py':
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Set):
                names.update(ast.literal_eval(node.value))
# Additional possible structures, kept separate from approved production concepts.
extras = {'AccountsPayableCurrent','DeferredRevenueNoncurrent',
          'TemporaryEquityCarryingAmountAttributableToParent',
          'InterestCostsIncurred','InterestCostsCapitalized','InterestAndDebtExpense'}
result = {}
for year in range(2021, 2027):
    doc = etree.parse(str(OUT / f'gaap{year}-doc.xml'))
    labels = {e.get('{http://www.w3.org/1999/xlink}label')[4:]: e.text
              for e in doc.xpath('//*[local-name()="label"]')}
    schema = etree.parse(str(OUT / f'gaap{year}.xsd'))
    elements = {e.get('name'):dict(e.attrib) for e in schema.xpath('//*[local-name()="element"]')}
    result[str(year)] = {n:dict(definition=labels.get(n), attributes=elements.get(n))
                         for n in sorted(names | extras)}
changes = []
for year in range(2021, 2026):
    for name in sorted(names | extras):
        a,b = result[str(year)][name],result['2026'][name]
        keys = ['type','{http://www.xbrl.org/2003/instance}periodType','{http://www.xbrl.org/2003/instance}balance','abstract','nillable']
        if a['definition'] != b['definition'] or any((a['attributes'] or {}).get(k) != (b['attributes'] or {}).get(k) for k in keys):
            changes.append(dict(year=year,concept=name,old=a,new=b))
(OUT / 'taxonomy_comparison.json').write_text(json.dumps(dict(production_concepts=sorted(names),additional_review_concepts=sorted(extras),versions=result,differences_from_2026=changes),indent=2)+'\n')
print(len(names),'production concepts;',len(changes),'year/concept differences')
for change in changes:
    print(change['year'],change['concept'],change['old']['definition'],'=>',change['new']['definition'])
