
SELECT
    sector,
    MIN(fiscal_period_end) FILTER (
        WHERE debt_to_assets_ratio IS NOT NULL
    ) AS earliest_ratio_period_end,
    MAX(fiscal_period_end) FILTER (
        WHERE debt_to_assets_ratio IS NOT NULL
    ) AS latest_ratio_period_end
FROM sector_leverage_rankings
GROUP BY sector
ORDER BY sector;
