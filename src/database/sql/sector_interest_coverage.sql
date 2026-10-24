CREATE OR REPLACE VIEW sector_interest_coverage_rankings AS
WITH

latest_financials AS (
    SELECT DISTINCT ON (ticker)
        ticker,
        fiscal_period_start,
        fiscal_period_end,
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
    f.interest_coverage_ratio,
    CASE
        WHEN f.interest_coverage_ratio IS NOT NULL THEN
            RANK() OVER (
                PARTITION BY c.sector
                ORDER BY f.interest_coverage_ratio DESC NULLS LAST
            )
    END AS sector_rank
FROM companies c
LEFT JOIN latest_financials f ON c.ticker = f.ticker
WHERE c.is_current_constituent = TRUE;
