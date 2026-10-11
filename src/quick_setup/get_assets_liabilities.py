from quick_setup.get_calculated_value import (
    get_value, get_reported_value, matching_facts, standard_concept,
)


# Exact categories reviewed against the official US GAAP definitions. These are
# classifications of branches in a filed equation, not a list to sum blindly.
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
    """Identify liabilities within a complete filed liabilities-and-equity sum."""
    if financial_data is None:
        return None
    xb = financial_data.xb
    combined = get_reported_value(
        financial_data, "us-gaap:LiabilitiesAndStockholdersEquity", period_end
    )
    if combined is None:
        return None

    for role, tree in xb.calculation_trees.items():
        presentation = xb.presentation_trees.get(role)
        if presentation is None:
            continue
        concepts = {standard_concept(c) for c in presentation.all_nodes}
        if not {"us-gaap:Assets", "us-gaap:LiabilitiesAndStockholdersEquity"} <= concepts:
            continue
        children = [a for a in tree.all_arcs if standard_concept(a.parent_id)
                    == "us-gaap:LiabilitiesAndStockholdersEquity"]
        equity = 0
        liabilities = 0
        has_equity = False
        has_liabilities = False
        missing_total = False
        for arc in children:
            concept = standard_concept(arc.child_id)
            if not concept.startswith("us-gaap:") or arc.weight != 1:
                break
            name = concept.removeprefix("us-gaap:")
            if name == "CommitmentsAndContingencies":
                # This exact taxonomy concept is a balance-sheet caption, not a
                # monetary category. Excluding its blank caption does NOT mean
                # commitments are zero. No other missing/nil child is skipped.
                rows = matching_facts(financial_data, concept, period_end)
                if (concept not in concepts or rows is None or rows.empty
                        or rows["numeric_value"].notna().any()
                        or not rows["value"].fillna("").eq("").all()):
                    break
                continue
            if name not in LIABILITY_BRANCHES | EQUITY_BRANCHES:
                break
            if name == "Liabilities":
                missing_total = True
                has_liabilities = True
                continue
            amount = get_value(financial_data, concept, period_end)
            if amount is None:
                break
            if name in EQUITY_BRANCHES:
                equity += amount
                has_equity = True
            else:
                liabilities += amount
                has_liabilities = True
        else:
            if has_equity and has_liabilities:
                # If the total itself is a child, solve its declared equation.
                # Otherwise use exactly the filed liability branches, never
                # their descendants or an assumed zero noncurrent subtotal.
                return combined - equity - liabilities if missing_total else liabilities
    return None


def get_assets_liabilities(financial_data, fiscal_period_end):
    assets = get_value(
        financial_data, "us-gaap:Assets", fiscal_period_end
    )
    liabilities = get_value(
        financial_data, "us-gaap:Liabilities", fiscal_period_end
    )

    if liabilities is None:
        liabilities = liabilities_from_balance_sheet(financial_data, fiscal_period_end)

    # assets fallback: current + noncurrent
    if assets is None:
        current_assets = get_value(
            financial_data, "us-gaap:AssetsCurrent", fiscal_period_end
        )
        noncurrent_assets = get_value(
            financial_data, "us-gaap:AssetsNoncurrent", fiscal_period_end
        )

        if current_assets is not None and noncurrent_assets is not None:
            assets = current_assets + noncurrent_assets

    # liabilities fallback: current + noncurrent
    if liabilities is None:
        current_liabilities = get_value(
            financial_data, "us-gaap:LiabilitiesCurrent", fiscal_period_end
        )
        noncurrent_liabilities = get_value(
            financial_data, "us-gaap:LiabilitiesNoncurrent", fiscal_period_end
        )

        if current_liabilities is not None and noncurrent_liabilities is not None:
            liabilities = current_liabilities + noncurrent_liabilities

    # assets fallback: liabilities + equity
    if assets is None:
        assets = get_value(
            financial_data,
            "us-gaap:LiabilitiesAndStockholdersEquity",
            fiscal_period_end,
        )

    # fallback for assets or liabilities: equity
    if assets is None or liabilities is None:
        equity = get_value(
            financial_data,
            "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
            fiscal_period_end,
        )
        # fallback for equity: parent + noncontrolling
        if equity is None:
            parent_equity = get_value(
                financial_data, "us-gaap:StockholdersEquity", fiscal_period_end
            )
            noncontrolling_equity = get_value(
                financial_data, "us-gaap:MinorityInterest", fiscal_period_end
            )

            if parent_equity is not None and noncontrolling_equity is not None:
                equity = parent_equity + noncontrolling_equity

        temporary_equity = get_value(
            financial_data,
            "us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests",
            fiscal_period_end,
        )

        if equity is not None and temporary_equity is not None:
            if liabilities is None and assets is not None:
                liabilities = assets - equity - temporary_equity

            if assets is None and liabilities is not None:
                assets = liabilities + equity + temporary_equity

    return {"assets": assets, "liabilities": liabilities}
