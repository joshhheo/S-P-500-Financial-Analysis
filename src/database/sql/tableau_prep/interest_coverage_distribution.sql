WITH sector_quartiles AS (
    SELECT
        sector,
        PERCENTILE_CONT(0.25) WITHIN GROUP (
            ORDER BY interest_coverage_ratio
        )::NUMERIC AS sector_p25,
        PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY interest_coverage_ratio
        )::NUMERIC AS sector_median,
        PERCENTILE_CONT(0.75) WITHIN GROUP (
            ORDER BY interest_coverage_ratio
        )::NUMERIC AS sector_p75
    FROM sector_interest_coverage_rankings
    GROUP BY sector
)
SELECT
    c.ticker,
    c.company_name,
    c.sector,
    c.fiscal_period_start,
    c.fiscal_period_end,
    c.interest_coverage_ratio,
    ABS(c.interest_coverage_ratio - s.sector_median)
        / NULLIF(s.sector_p75 - s.sector_p25, 0) AS median_distance_iqr,
    CASE
        WHEN c.interest_coverage_ratio IS NULL THEN NULL
        WHEN c.interest_coverage_ratio < s.sector_p25 - 1.5 * (s.sector_p75 - s.sector_p25)
            OR c.interest_coverage_ratio > s.sector_p75 + 1.5 * (s.sector_p75 - s.sector_p25)
            THEN TRUE
        ELSE FALSE
    END AS is_outlier
FROM sector_interest_coverage_rankings c
LEFT JOIN sector_quartiles s ON c.sector = s.sector
ORDER BY c.sector, c.ticker;
