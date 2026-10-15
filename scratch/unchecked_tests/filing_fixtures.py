"""Load saved XBRL facts and relationships for offline regression tests."""
from types import SimpleNamespace
import pandas as pd
from edgar.xbrl.models import CalculationArc, CalculationTree


def _legacy_financials(data):
    class Query:
        def by_concept(self, concept, exact):
            assert exact
            self.concept = concept
            return self

        def to_dataframe(self):
            rows = []
            for fact in data["facts"]:
                if fact["concept"].replace("us-gaap_", "us-gaap:") == self.concept:
                    rows.append(fact)
            return pd.DataFrame(rows)

    def query(include_contexts=False):
        return Query()

    calculations = {}
    for role, relationships in data["calculations"].items():
        if not relationships:
            continue
        arcs = []
        for relationship in relationships:
            arcs.append(CalculationArc(
                parent_id=relationship["parent"], child_id=relationship["child"],
                weight=relationship["weight"]))
        calculations[role] = CalculationTree(
            role_uri=role, definition="", root_element_id=relationships[0]["parent"],
            all_arcs=arcs)
    return SimpleNamespace(xb=SimpleNamespace(
        query=query, calculation_trees=calculations))

# Adapt historical snapshots to the exact-source API. Real precision comes from
# archived SEC XML, never an invented decimals default for a real filing.


def financials(data):
    from pathlib import Path
    import json
    from value_retrieval.source import Source, parse_source
    fin = _legacy_financials(data)
    folder = Path(__file__).with_name('implementation')
    if data.get('ticker'):
        manifest = json.loads((folder/'instance_manifest.json').read_text())
        entry = next(r for r in manifest if r['ticker'] == data['ticker'] and r['end'] == data['end'])
        instance = next(d for d in entry['documents'] if d['file'].endswith('_htm.xml'))
        source = parse_source((folder/instance['file']).read_bytes(),
            [(folder/d['file']).read_bytes() for d in entry['documents'] if d is not instance],
            cik=data['cik'],accession=entry['accession'],documents=entry['documents'])
        # Apply explicit snapshot mutations to exact source facts. Unchanged
        # lexical values/precision remain the original XML values.
        originals = json.loads((folder.parent/'extraction_audit'/f"{data['ticker']}-{data['end']}.json").read_text())
        key = lambda r: (r['concept'],r['context_ref'])
        baseline = {key(r):r for r in originals['facts']}
        retained = {key(r):r for r in data['facts']}
        records=[]
        for r in source.records:
            if key(r) not in retained:
                continue
            changed=retained[key(r)]
            before=baseline[key(r)]
            r=dict(r)
            for field in ('is_dimensioned','period_instant','period_start','period_end','unit_ref'):
                if changed.get(field)!=before.get(field):
                    r[field]=changed.get(field)
            if changed.get('numeric_value')!=before.get('numeric_value'):
                value=changed.get('numeric_value')
                r.update(value='' if value is None else str(value),nil=value is None)
            records.append(r)
        source.records=records
        if data['calculations']!=originals['calculations']:
            source.equations={}
            for role,arcs in data['calculations'].items():
                for arc in arcs:
                    source.equations.setdefault((role,arc['parent']),[]).append((arc['child'],arc['weight']))
    else:
        import gzip
        registry = json.loads(gzip.decompress((folder/'standard_concepts_before_explicit_tags.json.gz').read_bytes()))
        records=[]
        for index, original in enumerate(data['facts']):
            r=dict(original)
            concept=r['concept'].replace('us-gaap_','us-gaap:')
            # Fixture periods come from archived schema data, independent of the
            # production allowlist (including intentionally unsupported tags).
            metadata=registry['2026']['concepts'].get(concept.removeprefix('us-gaap:'))
            value=r.get('value',r.get('numeric_value'))
            r.update(concept=concept,value='' if value is None else str(value),nil=value is None or value=='',
                entity_identifier=str(int(r.get('entity_identifier','2488'))),
                context_ref=r.get('context_ref',str(index)),fact_id=str(index))
            r.setdefault('decimals','0')  # Explicit constructed-fixture precision.
            if metadata and metadata['period']=='instant':
                r.update(period_start=None,period_end=None)
            elif metadata:
                r['period_instant']=None
            records.append(r)
        units={r['unit_ref']:r['unit_ref'].upper() for r in records if r.get('unit_ref')}
        source=Source('2026','2488',records,units)
        equations={}
        for role, arcs in data['calculations'].items():
            for arc in arcs:
                parent=arc['parent'].replace('us-gaap_','us-gaap:')
                child=arc['child'].replace('us-gaap_','us-gaap:')
                equations.setdefault((role,parent),[]).append((child,arc['weight']))
        source.equations=equations
    source.xb = fin.xb
    source.audit_source = source  # Historical test controls access this alias.
    return source
