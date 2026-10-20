# Handoff

The current focus is SQL analysis, then Tableau/BI integration. Major pipeline
redesign is not requested; the README describes the metrics and data policies.

## Next steps

1. Confirm the live database state. The user planned to delete the old tables;
   this has not been verified. Schema creation now assumes the final schema and
   does not migrate old tables. Recreate/load as needed with user authorization.
2. Check loaded row counts, missing ratios and sector views.
3. Build useful SQL analysis: sector comparisons, historical trends, outliers and
   missing-data coverage. Then connect Tableau.

## Preferences and boundaries

- Keep code minimal, readable and separated by purpose. Prefer explicit SQL and
  ordinary loops/if-else over dynamic query generation or compact expressions.
- Preserve the user's comments. Explain changes simply; avoid unnecessary checks,
  wrappers, classes or architectural changes.
- Preserve established metric definitions and fallbacks. Missing is not zero.
  Debt-to-assets uses total liabilities, not interest-bearing debt.
- Ticker remains the database key; ticker changes are a documented limitation.
  CIK is stored in companies, not financials or the ratios CSV.
- Do not run live extraction, overwrite production CSVs or write to the live
  database without authorization. Existing working-tree changes are intentional;
  do not reset them.

## Verification

Extraction now uses four company threads with EdgarTools’ shared request limiter.
A one-worker mode is available through generate_ratios(max_workers=1). No live
speedup has been measured; compare equivalent workloads and cache conditions.
The last full offline run passed 34 tests and 22 archived-filing comparisons.
The latest loader simplifications also passed both isolated storage tests.
Live PostgreSQL behavior has not been verified after the schema simplification.
Tests and research are under scratch/; supporting conclusions are in README.md.
