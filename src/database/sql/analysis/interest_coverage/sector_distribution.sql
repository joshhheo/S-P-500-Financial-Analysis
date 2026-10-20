
SELECT
    sector,
    PERCENTILE_CONT(0.25) WITHIN GROUP (
        ORDER BY interest_coverage_ratio
    ) AS interest_coverage_p25,
    PERCENTILE_CONT(0.5) WITHIN GROUP (
        ORDER BY interest_coverage_ratio
    ) AS median_interest_coverage,
    PERCENTILE_CONT(0.75) WITHIN GROUP (
        ORDER BY interest_coverage_ratio
    ) AS interest_coverage_p75
FROM sector_interest_coverage_rankings
GROUP BY sector
ORDER BY sector;
