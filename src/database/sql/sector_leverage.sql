CREATE OR REPLACE VIEW sector_leverage_rankings AS
WITH

latest_financials AS (
    SELECT DISTINCT ON (ticker)
        ticker,
        fiscal_period_start,
        fiscal_period_end,
        liabilities_to_assets_ratio,
        interest_coverage_ratio
    FROM financials
    ORDER BY ticker, fiscal_period_end DESC
)

SELECT
    c.ticker,
    c.cik,
    c.company_name,
    c.sector,
    f.fiscal_period_start,
    f.fiscal_period_end,
    f.liabilities_to_assets_ratio,
    f.interest_coverage_ratio,
    CASE
        WHEN f.liabilities_to_assets_ratio IS NOT NULL THEN
            RANK() OVER (
                PARTITION BY c.sector
                ORDER BY f.liabilities_to_assets_ratio DESC NULLS LAST
            )
    END AS sector_rank
FROM companies c
LEFT JOIN latest_financials f ON c.ticker = f.ticker
WHERE c.is_current_constituent = TRUE;
