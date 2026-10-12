from value_retrieval.get_equity import get_equity
from value_retrieval.get_value import (
    get_instant_value, get_reported_value, normalize_concept_name,
)

# reviewed categories used to classify branches in a filed equation.
LIABILITY_BRANCHES = {
    "Liabilities", "LiabilitiesCurrent", "LiabilitiesNoncurrent",
    "LongTermDebtNoncurrent", "OperatingLeaseLiabilityNoncurrent",
    "FinanceLeaseLiabilityNoncurrent", "DeferredIncomeTaxLiabilitiesNet",
    "DeferredIncomeTaxesAndOtherLiabilitiesNoncurrent", "OtherLiabilitiesNoncurrent",
}
EQUITY_BRANCHES = {
    "StockholdersEquity", "MinorityInterest",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    "RedeemableNoncontrollingInterestEquityCarryingAmount",
    "TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests",
}


def liabilities_from_balance_sheet(financial_data, period_end):
    # uses linkbase to derive value
    combined = get_reported_value(
        financial_data, "us-gaap:LiabilitiesAndStockholdersEquity", period_end
    )
    if combined is None:
        return None

    xb = financial_data.xb
    # role is network identifier
    # tree is calculation relationships for that network
    for role, tree in xb.calculation_trees.items():
        presentation = xb.presentation_trees.get(role)
        if presentation is None:
            continue
        # Require both balance-sheet totals in that presentation before
        # considering this network for the combined-equation fallback.
        concepts = set()
        for concept in presentation.all_nodes:
            concepts.add(normalize_concept_name(concept))
        if not {"us-gaap:Assets", "us-gaap:LiabilitiesAndStockholdersEquity"} <= concepts:
            continue
        # Collect only direct children of the combined total. Including their
        # descendants too could count the same amounts more than once.
        children = []
        for arc in tree.all_arcs:
            if normalize_concept_name(arc.parent_id) == "us-gaap:LiabilitiesAndStockholdersEquity":
                children.append(arc)
        # Start fresh totals for this equation; track whether both categories
        # occur and whether Liabilities itself is the amount to solve for.
        equity = 0
        liabilities = 0
        has_equity = False
        has_liabilities = False
        missing_total = False
        # Every monetary branch must be a reviewed standard concept with a
        # +1 weight. A break rejects this equation and allows the next network.
        for arc in children:
            concept = normalize_concept_name(arc.child_id)
            if not concept.startswith("us-gaap:") or arc.weight != 1:
                break
            name = concept.removeprefix("us-gaap:")
            # This specific caption may be skipped only when a matching blank,
            # nonnumeric fact exists in the presentation. It does not mean zero.
            if name == "CommitmentsAndContingencies":
                rows = xb.query().by_concept(concept, exact=True).to_dataframe()
                if rows.empty:
                    break
                rows = rows[rows["is_dimensioned"] == False]
                rows = rows[rows["period_instant"].astype(str).str[:10] == period_end]
                if (concept not in concepts or rows.empty
                        or rows["numeric_value"].notna().any()
                        or not rows["value"].fillna("").eq("").all()):
                    break
                continue
            # Reject unknown categories. If the child is the Liabilities total,
            # leave it unknown so it can be calculated from the other branches.
            if name not in LIABILITY_BRANCHES and name not in EQUITY_BRANCHES:
                break
            if name == "Liabilities":
                missing_total = True
                has_liabilities = True
                continue
            # Retrieve each remaining branch for the same date, then add it
            # to the appropriate subtotal. Missing amounts invalidate the equation.
            amount = get_instant_value(financial_data, concept, period_end)
            if amount is None:
                break
            if name in EQUITY_BRANCHES:
                equity += amount
                has_equity = True
            else:
                liabilities += amount
                has_liabilities = True
        else:
            # This else belongs to the for loop: it runs only if no break occurred.
            if has_equity and has_liabilities:
                # If the total itself is a child, solve its declared equation.
                # Otherwise use exactly the filed liability branches, never
                # their descendants or an assumed zero noncurrent subtotal.
                return combined - equity - liabilities if missing_total else liabilities
    # No network supplied a usable complete equation.
    return None

# retrieve liabilities without depending on assets, preventing fallback cycles
def get_liabilities_before_equity(financial_data, fiscal_period_end):
    # First try the reported total, then its own complete calculation equation.
    liabilities = get_instant_value(financial_data, "us-gaap:Liabilities", fiscal_period_end)
    if liabilities is None:
        # Next try identifying liabilities inside the combined balance-sheet total.
        liabilities = liabilities_from_balance_sheet(financial_data, fiscal_period_end)
    if liabilities is None:
        # Finally try current + noncurrent liabilities; both must be available.
        current = get_instant_value(financial_data, "us-gaap:LiabilitiesCurrent", fiscal_period_end)
        noncurrent = get_instant_value(financial_data, "us-gaap:LiabilitiesNoncurrent", fiscal_period_end)
        if current is not None and noncurrent is not None:
            liabilities = current + noncurrent
    return liabilities


def get_liabilities(financial_data, fiscal_period_end):
    # Import here because the asset module also uses the liability lookup above.
    from value_retrieval.get_assets import get_assets_before_equity

    # Exhaust the routes that do not rely on the separately retrieved Assets total.
    liabilities = get_liabilities_before_equity(financial_data, fiscal_period_end)
    if liabilities is None:
        # assets minus permanent and temporary equity
        assets = get_assets_before_equity(financial_data, fiscal_period_end)
        equity_values = get_equity(financial_data, fiscal_period_end)
        equity = equity_values[0]
        temporary_equity = equity_values[1]
        if assets is not None and equity is not None and temporary_equity is not None:
            liabilities = assets - equity - temporary_equity
    return liabilities
