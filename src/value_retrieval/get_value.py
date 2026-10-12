
# concept tags sometimes have underscores instead of colons
def normalize_concept_name(concept):
    if concept.startswith("us-gaap_"):
        return "us-gaap:" + concept[len("us-gaap_"):]
    return concept

# get values from concept seraching
def get_reported_value(financial_data, concept, period_end, period_start=None):
    
    if financial_data is None or not concept.startswith("us-gaap:"):
        return None

    # xb gives access to XBRL stucture
    xb = financial_data.xb
    facts = xb.query().by_concept(concept, exact=True).to_dataframe()
    if facts.empty:
        return None

    matches = facts[facts["is_dimensioned"] == False]
    if period_start is None:
        matches = matches[
            matches["period_instant"].astype(str).str[:10] == period_end
        ]
    else:
        matches = matches[
            matches["period_start"].astype(str).str[:10] == period_start
        ]
        matches = matches[
            matches["period_end"].astype(str).str[:10] == period_end
        ]
    matches = matches.dropna(subset=["numeric_value"])
    if matches.empty:
        return None
    # first row selection is arbritary
    return matches.iloc[0]["numeric_value"]

# get values using calculation trees
def get_calculated_value(financial_data, concept, period_end, period_start=None):
    if financial_data is None or not concept.startswith("us-gaap:"):
        return None

    for tree in financial_data.xb.calculation_trees.values():
        immediate_children = []
        for arc in tree.all_arcs:
            if normalize_concept_name(arc.parent_id) == concept:
                immediate_children.append(arc)
        if not immediate_children:
            continue

        total = 0
        for arc in immediate_children:
            value = get_reported_value(
                financial_data, normalize_concept_name(arc.child_id), period_end, period_start
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


def get_instant_value(financial_data, concept, period_end):
    return get_value(financial_data, concept, period_end)


def get_duration_value(financial_data, concept_name, period_start, period_end):
    if period_start is None or period_end is None:
        return None
    return get_value(financial_data, concept_name, period_end, period_start)
