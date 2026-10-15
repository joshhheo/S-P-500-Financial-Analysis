# Retained verification and research

Run the two test modules with the offline verification command in the project README.

- `test_simple_retrieval.py`: constructed cases for current retrieval, accounting fallbacks, ratios and filing-loop wiring.
- `test_storage.py`: isolated SQLite handoff and temporary-directory CSV checkpoint checks. No live database or production CSV writes.
- `implementation/verify_simple_retrieval.py`: reads archived instances from `filing_documents.zip` and compares 22 real filings with the frozen linkbase-disabled baseline. This is regression evidence, not independent proof of correctness.
- `implementation/instance_manifest.json`: original filing provenance and document hashes.
- `implementation/linkbase_dependency_results.json` and `liability_identity_comparison.json`: historical coverage tradeoffs and candidate identities, including their limitations.
- `implementation/foreign_currency_evidence.json`: currency research supporting the documented scope assumption.
- `research_evidence.json`: consolidated duplicate/precision observations, independent raw-filing results, reviewed definitions and liability-identity inputs.
- `full_review/official_sources.zip`: preserved official taxonomy and guidance documents plus original filing source documents. `source_manifest.json`, `filing_versions.json` and `taxonomy_comparison.json` explain provenance and version differences.
- `full_review/baseline_hashes.json`: production CSV fingerprints recorded before the review.

Retired-architecture tests, duplicate snapshots and repeated run logs were removed.
The retained historical results are not rerunnable tests of retired implementations.
The current test logs and per-filing results are overwritten when verification is recorded,
rather than keeping a separate file for every revision. Sample coverage is not universal coverage.
