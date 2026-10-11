"""Direct standard facts, then complete filing-declared parent sums.

Fixed accounting formulas stay in the component modules. Calculations use
immediate reported children only: no recursion or rearranging equations.
"""


def standard_concept(element_id):
    if element_id.startswith("us-gaap_"):
        return "us-gaap:" + element_id[len("us-gaap_"):]
    return element_id


def matching_facts(financial_data, concept, period_end, period_start=None):
    if financial_data is None or not concept.startswith("us-gaap:"):
        return None

    xb = financial_data.xb
    facts = xb.query(include_contexts=True).by_concept(concept, exact=True).to_dataframe()
    if facts.empty:
        return None

    matches = facts[facts["is_dimensioned"] == False]
    entity = matches["entity_identifier"].astype(str).str.lstrip("0")
    matches = matches[entity == str(xb.entity_info["identifier"]).lstrip("0")]
    if period_start is None:
        matches = matches[
            matches["period_instant"].astype(str).str[:10] == period_end
        ]
    else:
        matches = matches[
            (matches["period_start"].astype(str).str[:10] == period_start)
            & (matches["period_end"].astype(str).str[:10] == period_end)
        ]
    return matches


def get_reported_value(financial_data, concept, period_end, period_start=None):
    matches = matching_facts(financial_data, concept, period_end, period_start)
    if matches is None or matches.empty:
        return None
    matches = matches.dropna(subset=["numeric_value"])
    if matches.empty:
        return None
    return matches.iloc[0]["numeric_value"]


def get_calculated_value(financial_data, concept, period_end, period_start=None):
    if financial_data is None or not concept.startswith("us-gaap:"):
        return None

    # Keep each role separate. Use the first complete equation in filing order.
    for tree in financial_data.xb.calculation_trees.values():
        children = [
            arc for arc in tree.all_arcs
            if standard_concept(arc.parent_id) == concept
        ]
        if not children:
            continue

        total = 0
        for arc in children:
            value = get_reported_value(
                financial_data, standard_concept(arc.child_id), period_end, period_start
            )
            if value is None:
                break
            total += arc.weight * value
        else:
            return total
    return None


def get_value(financial_data, concept, period_end, period_start=None):
    value = get_reported_value(financial_data, concept, period_end, period_start)
    if value is not None:
        return value
    return get_calculated_value(financial_data, concept, period_end, period_start)
