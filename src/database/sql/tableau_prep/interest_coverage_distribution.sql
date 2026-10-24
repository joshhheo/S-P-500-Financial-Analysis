WITH

latest_financials AS (
    SELECT
        f.ticker,
        f.fiscal_period_start,
        f.fiscal_period_end,
        f.interest_coverage_ratio
    FROM financials f
    WHERE f.fiscal_period_end = (
        SELECT MAX(fiscal_period_end)
        FROM financials
        WHERE ticker = f.ticker
    )
),

matched_companies AS (
    SELECT
        c.ticker,
        c.company_name,
        c.sector,
        f.fiscal_period_start,
        f.fiscal_period_end,
        f.interest_coverage_ratio,
        p.fiscal_period_start AS previous_fiscal_period_start,
        p.fiscal_period_end AS previous_fiscal_period_end,
        p.interest_coverage_ratio AS previous_interest_coverage_ratio
    FROM companies c
    JOIN latest_financials f ON c.ticker = f.ticker
    JOIN financials p
        ON c.ticker = p.ticker
        AND p.fiscal_period_end = f.fiscal_period_start - 1
        -- accounts for 52 or 53 week fiscal years
        AND f.fiscal_period_end - f.fiscal_period_start + 1 BETWEEN 364 AND 371
        AND p.fiscal_period_end - p.fiscal_period_start + 1 BETWEEN 364 AND 371
    WHERE c.is_current_constituent = TRUE
        AND f.interest_coverage_ratio IS NOT NULL
        AND p.interest_coverage_ratio IS NOT NULL
),

period_ratios AS (
    SELECT
        ticker,
        company_name,
        sector,
        'Previous' AS comparison_period,
        previous_fiscal_period_start AS fiscal_period_start,
        previous_fiscal_period_end AS fiscal_period_end,
        previous_interest_coverage_ratio AS interest_coverage_ratio,
        NULL AS interest_coverage_change
    FROM matched_companies

    UNION ALL

    SELECT
        ticker,
        company_name,
        sector,
        'Latest' AS comparison_period,
        fiscal_period_start,
        fiscal_period_end,
        interest_coverage_ratio,
        CASE
            WHEN previous_interest_coverage_ratio > 0 THEN
                100.0 * (interest_coverage_ratio - previous_interest_coverage_ratio)
                    / previous_interest_coverage_ratio
        END AS interest_coverage_change
    FROM matched_companies
),

sector_quartiles AS (
    SELECT
        sector,
        comparison_period,
        PERCENTILE_CONT(0.25) WITHIN GROUP (
            ORDER BY interest_coverage_ratio
        )::NUMERIC AS sector_p25,
        PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY interest_coverage_ratio
        )::NUMERIC AS sector_median,
        PERCENTILE_CONT(0.75) WITHIN GROUP (
            ORDER BY interest_coverage_ratio
        )::NUMERIC AS sector_p75
    FROM period_ratios
    GROUP BY sector, comparison_period
)

SELECT
    c.ticker,
    c.company_name,
    c.sector,
    c.comparison_period,
    c.fiscal_period_start,
    c.fiscal_period_end,
    c.interest_coverage_ratio,
    c.interest_coverage_change,
    ABS(c.interest_coverage_ratio - s.sector_median)
        / NULLIF(s.sector_p75 - s.sector_p25, 0) AS median_distance_iqr
FROM period_ratios c
JOIN sector_quartiles s
    ON c.sector = s.sector
    AND c.comparison_period = s.comparison_period
ORDER BY c.sector, c.comparison_period DESC, c.ticker;
