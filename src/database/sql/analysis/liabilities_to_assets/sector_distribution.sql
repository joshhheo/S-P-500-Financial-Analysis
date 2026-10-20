-- Liabilities/assets distribution for each sector using the latest stored periods.
-- Missing ratios are excluded from percentiles; each company has equal weight.
SELECT
    sector,
    PERCENTILE_CONT(0.25) WITHIN GROUP (
        ORDER BY debt_to_assets_ratio
    ) AS liabilities_to_assets_p25,
    PERCENTILE_CONT(0.5) WITHIN GROUP (
        ORDER BY debt_to_assets_ratio
    ) AS median_liabilities_to_assets,
    PERCENTILE_CONT(0.75) WITHIN GROUP (
        ORDER BY debt_to_assets_ratio
    ) AS liabilities_to_assets_p75
FROM sector_leverage_rankings
GROUP BY sector
ORDER BY sector;
