"""Constructed, offline evidence for which edgar interfaces can replace raw parsing.

This is an implementation comparison, not evidence from a company filing.
"""
import importlib.metadata
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from test_source_evidence import instance, fact, calculation, END
from edgar.xbrl.parsers.calculation import CalculationParser
from edgar.xbrl.parsers.instance import InstanceParser
from value_retrieval.source import parse_source
from value_retrieval.get_value import retrieve

arcrole = 'http://www.xbrl.org/2003/arcrole/summation-item'
prohibition = f'''<calculationArc xmlns:xlink="http://www.w3.org/1999/xlink"
 xlink:arcrole="{arcrole}" xlink:from="a" xlink:to="c"
 weight="1" priority="2" use="prohibited"/>'''
results = dict(evidence_type='constructed offline examples', edgartools_version=importlib.metadata.version('edgartools'))
for name, xml in [('prohibited_relationship', calculation(arcrole, prohibition)),
                  ('custom_schema_standard_looking_fragment', calculation(arcrole, custom=True))]:
    trees = {}
    parser = CalculationParser({}, trees, {}, {})
    parser.parse_calculation_content(xml)
    arcs = []
    for tree in trees.values():
        arcs.extend(arc.model_dump() for arc in tree.all_arcs)
    source = parse_source(instance(fact('AssetsCurrent', '25')), [xml], cik=2488)
    amount = retrieve(source, 'us-gaap:Assets', END)
    results[name] = dict(library_arcs=arcs, current_asset_result=None if amount is None else str(amount.value))

facts = {}
parser = InstanceParser({}, facts, {}, {}, {}, {}, [], {})
parser.parse_instance_content(instance(fact('Assets', '9007199254740993', decimals='INF') +
    '<us-gaap:Assets contextRef="i" unitRef="u" xsi:nil="true"/>'))
results['fact_fields'] = [fact.model_dump() for fact in facts.values()]
(HERE / 'library_interface_probe.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results, indent=2))
