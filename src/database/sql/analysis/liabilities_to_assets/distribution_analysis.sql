
WITH sector_observed_companies AS (
    SELECT
        sector,
        COUNT(liabilities_to_assets_ratio) AS sector_observed_companies
    FROM sector_leverage_rankings
    GROUP BY sector
), 
    
    sector_min_max AS (
    SELECT
        sector,
        MIN(liabilities_to_assets_ratio) AS sector_min,
        MAX(liabilities_to_assets_ratio) AS sector_max
    FROM sector_leverage_rankings
    GROUP BY sector
), 
    
    sector_mean AS (
    SELECT
        sector,
        AVG(liabilities_to_assets_ratio) AS sector_mean
    FROM sector_leverage_rankings
    GROUP BY sector
), 
    
    sector_quartiles AS (
    SELECT
        sector,
        PERCENTILE_CONT(0.25) WITHIN GROUP (
            ORDER BY liabilities_to_assets_ratio
        -- csv stores strings only
        )::NUMERIC AS sector_p25,
        PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY liabilities_to_assets_ratio
        )::NUMERIC AS sector_median,
        PERCENTILE_CONT(0.75) WITHIN GROUP (
            ORDER BY liabilities_to_assets_ratio
        )::NUMERIC AS sector_p75
    FROM sector_leverage_rankings
    GROUP BY sector
), 

    sector_whiskers AS (
    SELECT
        sector,
        sector_p75 - sector_p25 AS sector_iqr,
        sector_p25 - 1.5 * (sector_p75 - sector_p25) AS lower_whisker,
        sector_p75 + 1.5 * (sector_p75 - sector_p25) AS upper_whisker
    FROM sector_quartiles
),

    sector_statistics AS (
    SELECT *
    FROM sector_observed_companies
    JOIN sector_min_max USING (sector)
    JOIN sector_mean USING (sector)
    JOIN sector_quartiles USING (sector)
    JOIN sector_whiskers USING (sector)
)

SELECT
    c.ticker,
    c.company_name,
    c.sector,
    c.fiscal_period_start,
    c.fiscal_period_end,
    c.liabilities_to_assets_ratio,
    s.sector_observed_companies,
    s.sector_mean,
    s.sector_min,
    s.sector_p25,
    s.sector_median,
    s.sector_p75,
    s.sector_max,
    s.sector_iqr,
    s.lower_whisker,
    s.upper_whisker,
    CASE
        WHEN c.liabilities_to_assets_ratio IS NULL THEN NULL
        ELSE c.liabilities_to_assets_ratio < s.lower_whisker
            OR c.liabilities_to_assets_ratio > s.upper_whisker
    END AS is_outlier
FROM sector_leverage_rankings c
LEFT JOIN sector_statistics s ON c.sector = s.sector
ORDER BY c.sector, c.liabilities_to_assets_ratio DESC NULLS LAST, c.ticker;
