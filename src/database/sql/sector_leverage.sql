CREATE OR REPLACE VIEW sector_leverage_rankings AS
WITH latest_financials AS (
    SELECT DISTINCT ON (ticker)
        ticker,
        fiscal_period_end,
        fiscal_period_start,
        debt_to_assets_ratio,
        interest_coverage_ratio
    FROM financials
    ORDER BY ticker, fiscal_period_end DESC
)
SELECT
    c.ticker,
    c.company_name,
    c.sector,
    f.debt_to_assets_ratio AS debt_to_assets_ratio,
    CASE
        WHEN f.debt_to_assets_ratio IS NOT NULL THEN
            RANK() OVER (
                PARTITION BY c.sector
                ORDER BY f.debt_to_assets_ratio DESC NULLS LAST
            )
    END AS sector_rank,
    f.fiscal_period_end,
    f.interest_coverage_ratio AS interest_coverage_ratio,
    c.cik, f.fiscal_period_start
FROM companies c
LEFT JOIN latest_financials f ON c.ticker = f.ticker
WHERE c.is_current_constituent = TRUE;
