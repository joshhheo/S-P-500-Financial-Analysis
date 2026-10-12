"""Load saved XBRL facts and relationships for offline regression tests."""
from types import SimpleNamespace
import pandas as pd
from edgar.xbrl.models import CalculationArc, CalculationTree


def financials(data):
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
    presentations = {}
    for role, nodes in data["presentations"].items():
        concepts = {}
        for node in nodes:
            concepts[node["concept"]] = node
        presentations[role] = SimpleNamespace(all_nodes=concepts)
    return SimpleNamespace(xb=SimpleNamespace(
        query=query, calculation_trees=calculations, presentation_trees=presentations))
