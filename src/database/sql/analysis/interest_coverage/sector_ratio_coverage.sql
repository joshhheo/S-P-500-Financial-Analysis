
SELECT
    sector,
    ROUND(
        100.0 * COUNT(interest_coverage_ratio) / COUNT(*), 2
    ) AS interest_coverage_pct
FROM sector_interest_coverage_rankings
GROUP BY sector
ORDER BY sector;
