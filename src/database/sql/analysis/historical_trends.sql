-- Current constituents and current sectors, grouped by calendar year of fiscal-period end.
-- Keep one latest period per ticker/year so shortened periods do not double-weight a company.
-- This is a changing observed sample, not a matched cohort or historical index membership.
WITH annual AS (
    SELECT DISTINCT ON (f.ticker, EXTRACT(YEAR FROM f.fiscal_period_end))
        c.sector,
        f.ticker,
        EXTRACT(YEAR FROM f.fiscal_period_end)::INTEGER AS period_end_year,
        f.debt_to_assets_ratio,
        f.interest_coverage_ratio
    FROM financials f
    JOIN companies c ON c.ticker = f.ticker
    WHERE c.is_current_constituent = TRUE
    ORDER BY f.ticker, EXTRACT(YEAR FROM f.fiscal_period_end), f.fiscal_period_end DESC
)
SELECT
    sector,
    period_end_year,
    COUNT(*) AS observed_companies,
    COUNT(debt_to_assets_ratio) AS leverage_available,
    COUNT(interest_coverage_ratio) AS interest_coverage_available,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY debt_to_assets_ratio) AS median_liabilities_to_assets,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY interest_coverage_ratio) AS median_interest_coverage
FROM annual
GROUP BY sector, period_end_year
ORDER BY sector, period_end_year DESC;
