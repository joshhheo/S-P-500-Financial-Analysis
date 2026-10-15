# unchecked test
from pathlib import Path
import sys


def normalize_concept_name(concept):
    """Convert the library's schema ID spelling, without label/alias matching."""
    if concept.startswith("us-gaap_"):
        return "us-gaap:" + concept[len("us-gaap_"):]
    return concept


def matching_facts(xb, concept, end, start, cik):
    facts = xb.query(include_contexts=True).by_concept(concept, exact=True).to_dataframe()
    if facts.empty:
        return facts
    matches = facts[facts["is_dimensioned"] == False]
    entity = matches["entity_identifier"].astype(str).str.lstrip("0")
    matches = matches[entity == str(cik).lstrip("0")]
    if start is None:
        matches = matches[
            matches["period_instant"].astype(str).str[:10] == end
        ]
    else:
        matches = matches[
            (matches["period_start"].astype(str).str[:10] == start)
            & (matches["period_end"].astype(str).str[:10] == end)
        ]
    return matches


def inspect_calculations(financial_data, target, end, cik, start=None):
    """Print role-specific equations and fact availability, without solving them.

Only immediate children are inspected. No recursive or inverse reconstruction
is attempted. A complete equation is a candidate for review, not an automatic
decision that the role is applicable to the requested consolidated amount.
"""
    xb = financial_data.xb

    def describe(element_id):
        concept = normalize_concept_name(element_id)
        if not concept.startswith("us-gaap:"):
            return "CUSTOM/OUT OF SCOPE", False
        facts = matching_facts(xb, concept, end, start, cik).dropna(subset=["numeric_value"])
        if facts.empty:
            return "MISSING matching consolidated fact", False
        fact = facts.iloc[0]
        return (
            f"value={fact['numeric_value']:,}; context={fact['context_ref']}",
            True,
        )

    print(f"Target: {target}; CIK: {cik}; period: {start or 'instant'} → {end}")
    print(f"Direct target: {describe(target)[0]}")
    print(f"Calculation networks: {len(xb.calculation_trees)}")
    target_roles = 0
    target_parent_roles = 0
    anchors = {target}
    if target == "us-gaap:Liabilities":
        anchors.update({
            "us-gaap:LiabilitiesAndStockholdersEquity",
            "us-gaap:LiabilitiesCurrent",
            "us-gaap:LiabilitiesNoncurrent",
        })

    for role, tree in xb.calculation_trees.items():
        # all_arcs preserves weights per relationship; node.weight does not.
        arcs = tree.all_arcs
        target_arcs = [a for a in arcs if target in {
            normalize_concept_name(a.parent_id), normalize_concept_name(a.child_id)
        }]
        target_roles += bool(target_arcs)
        target_parent_roles += any(
            normalize_concept_name(a.parent_id) == target for a in arcs
        )
        parents = {
            a.parent_id for a in arcs
            if normalize_concept_name(a.parent_id) in anchors
            or normalize_concept_name(a.child_id) == target
        }
        if not parents:
            continue
        print(f"\nROLE: {role}\nDefinition: {tree.definition}")
        for parent in sorted(parents):
            children = sorted(
                (a for a in arcs if a.parent_id == parent),
                key=lambda a: a.order,
            )
            print(f"  Parent {normalize_concept_name(parent)}: {describe(parent)[0]}")
            complete = True
            for arc in children:
                status, available = describe(arc.child_id)
                complete = complete and available
                print(f"    {arc.weight:+g} × {normalize_concept_name(arc.child_id)}: {status}")
            print(f"  All immediate children available and standard: {complete}")

    print(f"\nNetworks containing target: {target_roles}")
    print(f"Networks with target as summation parent: {target_parent_roles}")
    if target_parent_roles == 0:
        print("No target-parent equation exposed: direct parent summation cannot reconstruct it.")
    print("Inspection only: no recursive solving, inverse solving, or extraction changes.")



def main():
    from edgar import Company

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    from setup_sec_identity import setup_sec_identity

    setup_sec_identity()
    filing = Company(2488).get_filings(
        form="10-K",
        amendments=False,
        accession_number="0000002488-26-000018",
    )[0]
    annual_report = filing.obj()  # Parse once and reuse its financial data.
    inspect_calculations(
        annual_report.financials,
        target="us-gaap:Liabilities",
        end=str(filing.period_of_report)[:10],
        cik=2488,
    )



if __name__ == "__main__":
    main()
