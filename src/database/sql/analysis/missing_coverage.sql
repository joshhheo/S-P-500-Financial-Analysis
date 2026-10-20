-- Distinguish no financial row from a missing ratio in the latest stored row.
SELECT
    sector,
    COUNT(*) AS current_companies,
    COUNT(*) FILTER (WHERE fiscal_period_end IS NULL) AS no_financial_history,
    COUNT(*) FILTER (WHERE fiscal_period_end IS NOT NULL AND debt_to_assets_ratio IS NULL) AS latest_leverage_missing,
    COUNT(*) FILTER (WHERE fiscal_period_end IS NOT NULL AND interest_coverage_ratio IS NULL) AS latest_interest_coverage_missing,
    ROUND(100.0 * COUNT(*) FILTER (WHERE debt_to_assets_ratio IS NULL) / COUNT(*), 2) AS leverage_missing_pct,
    ROUND(100.0 * COUNT(*) FILTER (WHERE interest_coverage_ratio IS NULL) / COUNT(*), 2) AS interest_coverage_missing_pct
FROM sector_leverage_rankings
GROUP BY sector
ORDER BY interest_coverage_missing_pct DESC, sector;
