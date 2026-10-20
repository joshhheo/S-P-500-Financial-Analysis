-- Two-sided sector IQR flags are review candidates, not errors or distress predictions.
-- Require at least eight observed companies and a nonzero IQR for each metric.
WITH metrics AS (
    SELECT ticker, company_name, sector, fiscal_period_end,
        'liabilities_to_assets' AS metric, debt_to_assets_ratio AS value
    FROM sector_leverage_rankings
    UNION ALL
    SELECT ticker, company_name, sector, fiscal_period_end,
        'interest_coverage' AS metric, interest_coverage_ratio AS value
    FROM sector_interest_coverage_rankings
), quartiles AS (
    SELECT sector, metric, COUNT(value) AS observed_companies,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY value) AS q1,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY value) AS q3
    FROM metrics
    GROUP BY sector, metric
)
SELECT m.*, q.observed_companies,
    q.q1 - 1.5 * (q.q3 - q.q1) AS lower_fence,
    q.q3 + 1.5 * (q.q3 - q.q1) AS upper_fence
FROM metrics m
JOIN quartiles q ON q.sector = m.sector AND q.metric = m.metric
WHERE q.observed_companies >= 8 AND q.q3 > q.q1
    AND (m.value < q.q1 - 1.5 * (q.q3 - q.q1)
         OR m.value > q.q3 + 1.5 * (q.q3 - q.q1))
ORDER BY m.metric, m.sector, m.value DESC;
