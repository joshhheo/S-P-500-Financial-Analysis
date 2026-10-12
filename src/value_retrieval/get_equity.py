from value_retrieval.get_value import get_instant_value


def get_equity(financial_data, fiscal_period_end):
    equity = get_instant_value(
        financial_data,
        "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        fiscal_period_end,
    )
    # fallback for equity: parent + noncontrolling
    if equity is None:
        parent_equity = get_instant_value(
            financial_data, "us-gaap:StockholdersEquity", fiscal_period_end
        )
        noncontrolling_equity = get_instant_value(
            financial_data, "us-gaap:MinorityInterest", fiscal_period_end
        )

        if parent_equity is not None and noncontrolling_equity is not None:
            equity = parent_equity + noncontrolling_equity

    temporary_equity = get_instant_value(
        financial_data,
        "us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests",
        fiscal_period_end,
    )

    return equity, temporary_equity
