CREATE OR REPLACE VIEW sector_interest_coverage_rankings AS
WITH latest_financials AS (
    SELECT DISTINCT ON (ticker)
        ticker,
        fiscal_period_end,
        cik, accession, fiscal_period_start, debt_to_assets_status, interest_coverage_status, extraction_evidence,
        interest_coverage_ratio
    FROM financials
    ORDER BY ticker, fiscal_period_end DESC
)
SELECT
    c.ticker,
    c.company_name,
    c.sector,
    CASE WHEN f.interest_coverage_status = 'available' THEN f.interest_coverage_ratio END AS interest_coverage_ratio,
    CASE
        WHEN f.interest_coverage_status = 'available' AND f.interest_coverage_ratio IS NOT NULL THEN
            RANK() OVER (
                PARTITION BY c.sector
                ORDER BY CASE WHEN f.interest_coverage_status = 'available' THEN f.interest_coverage_ratio END DESC NULLS LAST
            )
    END AS sector_rank,
    f.fiscal_period_end,
    f.cik, f.accession, f.fiscal_period_start,
    f.debt_to_assets_status, f.interest_coverage_status, f.extraction_evidence
FROM companies c
LEFT JOIN latest_financials f ON c.ticker = f.ticker
WHERE c.is_current_constituent = TRUE;
