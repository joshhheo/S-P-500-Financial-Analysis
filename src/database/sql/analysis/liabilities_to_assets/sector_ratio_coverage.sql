-- Availability of each ratio in the latest stored period per current company.
-- Uses all current companies in the sector as the denominator.
SELECT
    sector,
    ROUND(
        100.0 * COUNT(debt_to_assets_ratio) / COUNT(*), 2
    ) AS liabilities_to_assets_coverage_pct
FROM sector_leverage_rankings
GROUP BY sector
ORDER BY sector;
