-- Latest stored period per current constituent; NULL never falls back to an older value.
-- Medians describe reporting companies, not the full sector or an asset-weighted ratio.
SELECT
    sector,
    COUNT(*) AS current_companies,
    COUNT(fiscal_period_end) AS companies_with_financials,
    MIN(fiscal_period_end) AS earliest_latest_period,
    MAX(fiscal_period_end) AS latest_period,
    COUNT(debt_to_assets_ratio) AS leverage_available,
    ROUND(100.0 * COUNT(debt_to_assets_ratio) / COUNT(*), 2) AS leverage_coverage_pct,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY debt_to_assets_ratio) AS median_liabilities_to_assets,
    COUNT(interest_coverage_ratio) AS interest_coverage_available,
    ROUND(100.0 * COUNT(interest_coverage_ratio) / COUNT(*), 2) AS interest_coverage_pct,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY interest_coverage_ratio) AS median_interest_coverage
FROM sector_leverage_rankings
GROUP BY sector
ORDER BY sector;
