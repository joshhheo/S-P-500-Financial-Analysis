# S&P 500 financial risk pipeline

Extracts financial values from SEC 10-K filings for current S&P 500 constituents,
calculates liabilities/assets and interest coverage, and loads the results into
PostgreSQL (Neon) for users to query and analyze. The author's separate research
uses these outputs for sector distribution analysis and Tableau visualizations.

The project favors explicit accounting formulas and small modules with a single
purpose. Missing values remain missing throughout extraction, storage and analysis.

- [Metrics](#metrics)
- [Pipeline and storage](#pipeline-and-storage)
- [Setup and execution](#setup-and-execution)
- [Data analysis](#data-analysis)
- [Data rules and assumptions](#data-rules-and-assumptions)
- [Accounting fallbacks](#accounting-fallbacks)
- [Limitations](#limitations)
- [Tests and evidence](#tests-and-evidence)
- [Roadmap](#roadmap)
- [Analytical framework](#analytical-framework)
- [Design decisions](#design-decisions)

## Metrics

| Output | Formula | Meaning |
| --- | --- | --- |
| `liabilities_to_assets_ratio` | Total liabilities / total assets | Uses **all liabilities**, not only interest-bearing debt. |
| `interest_coverage_ratio` | Annual operating income / annual total interest expense | Total interest expense includes operating and nonoperating interest expense; the numerator is operating income, not a separately reconstructed EBIT. |

A missing required value or zero denominator produces `None`. Zero numerators and
negative reported amounts are not automatically rejected.

## Pipeline and storage

1. Read current S&P 500 constituents, CIKs and sectors from Wikipedia.
2. Use each CIK to retrieve up to five distinct original 10-K reporting periods,
   processing up to three companies concurrently.
3. Let Edgar parse each filing; search its facts using explicit concept names.
4. Retrieve each metric, trying its accounting fallbacks only when needed.
5. Calculate ratios, save CSVs, load the database and refresh sector views.

Extraction processes three companies concurrently, with each company's filings
processed sequentially. Results retain company-CSV order and are written after
all workers succeed. [Performance observations](#extraction-performance) are recorded below.

Historical results cover **current constituents**, not historical index membership.
Amended filings are excluded. The full run performs all five steps.

| Location | Purpose |
| --- | --- |
| [src/main.py](src/main.py) | Run the pipeline stages. |
| [src/wiki_pull.py](src/wiki_pull.py) | Retrieve the constituent list. |
| [src/table_data/](src/table_data/) | Build company and ratio CSVs. |
| [src/value_retrieval/get_value.py](src/value_retrieval/get_value.py) | Establish the annual start from DEI facts and retrieve exact concepts for specified dates. |
| [src/value_retrieval/](src/value_retrieval/) | Individual asset, liability, equity, interest and operating-income formulas. |
| [src/calculations/](src/calculations/) | Divide independently retrieved metrics. |
| [src/database/](src/database/) | Create tables, load CSVs and refresh views. |
| [scratch/tests/](scratch/tests/) | Repeatable behavior checks and archived filing fixtures. |
| [scratch/research/](scratch/research/) | Historical investigations and source evidence behind accounting decisions. |

The company CSV (`data/company_status.csv`) supplies ticker, CIK, name and sector
to `companies`, keyed by ticker. The ratios CSV (`data/financial_ratios.csv`)
supplies the reporting dates and two ratios to `financials`, keyed by ticker and
fiscal-period end. CIK is stored only in `companies`. The ratios CSV is written
directly after extraction finishes; there is no checkpoint or resume mechanism.
Sector views join by ticker, select the latest stored period for current
constituents and rank nonmissing ratios without substituting an older period.

The reusable tool provides these database outputs:

| Output | Purpose |
| --- | --- |
| `companies` | Company identity, current sector and constituent status. |
| `financials` | Stored financial ratios and fiscal periods for each ticker. |
| `sector_leverage_rankings` | Latest liabilities/assets ratios and within-sector ranks for current constituents. |
| `sector_interest_coverage_rankings` | Latest interest-coverage ratios and within-sector ranks for current constituents. |

Users can build their own queries, visualizations and research from these tables
and views, or use the CSV outputs directly. The SQL files defining the ranking
views are part of the tool; the queries under `sql/tableau_prep/` and the Tableau
presentation are the author's specific use of its data, not required tool stages.

## Setup and execution

Schema setup creates tables if absent; it does not migrate older schemas or delete
existing tables. The separate view-refresh stage creates the sector views.
For structural database changes, the project owner manually deletes the old
tables and dependent views in Neon, then reruns the pipeline to recreate and
load the current schema. No automatic schema migration is performed.

Run from the repository root. The development environment uses Python 3.13;
[requirements.txt](requirements.txt) pins dependencies, including EdgarTools 5.58.0.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Set these variables in an uncommitted `.env` file:

```dotenv
SEC_user_agent="Your name your-email@example.com"
db_connection_string="postgresql+psycopg2://USER:PASSWORD@HOST/DATABASE?sslmode=require"
```

Run the full pipeline **with network access, CSV replacement and database writes**:

```sh
.venv/bin/python src/main.py
```

To run an individual collection stage instead of the full pipeline, choose one
of the commands below. Both use network access and replace their output CSV;
neither loads the database or refreshes views.

Refresh the current company list in `data/company_status.csv`:

```sh
PYTHONPATH=src .venv/bin/python -m table_data.company_status
```

Read that company list, retrieve SEC filings and write `data/financial_ratios.csv`:

```sh
PYTHONPATH=src .venv/bin/python -m table_data.generate_ratios
```

`PYTHONPATH=src` lets Python find the project's modules. `.venv/bin/python` uses
the project's Python environment, and `-m` runs the named module.

## Data analysis

The author's research asks how financial-ratio distributions differ across sectors
and which companies stand out within their sector. The Tableau presentation is a
published snapshot, separate from the reusable pipeline. Tool users can work
directly with `companies`, `financials` and the sector-ranking views.

**Data snapshot: October 21, 2026.** The charts compare each company's Previous
and Latest comparable annual periods; those fiscal dates vary by company and are
separate from the snapshot date. Each sector uses the same matched tickers in
both periods, with matching performed independently for each metric.

[Explore the interactive Tableau workbook][tableau].
Open the workbook's sheet tabs for the two metrics and their zoomed views.
Each preview below links to the workbook.

Each dot represents one ticker in one annual period. Boxes show the middle 50%
of values, with the median inside each box. Whiskers end at the outermost observed
values within the 1.5 × IQR thresholds. Dot colors show distance from the sector
and period median in IQRs, not financial health. The zoomed views narrow the axis
range to make the boxes easier to compare; observations outside the range are
not shown, but remain in the matched sample and distribution calculations.

**Liabilities-to-assets distribution by sector**

**Zoomed view (0–1.5)**

[![Previous and Latest liabilities-to-assets distributions by sector, zoomed to 0–1.5](<docs/images/Liabilties-to-Assets-Distribution (0-1.5).png>)][tableau]

**Full-range view**

[![Previous and Latest liabilities-to-assets distributions by sector, full range](<docs/images/Liabilties-to-Assets-Distribution.png>)][tableau]

**Data coverage — liabilities-to-assets**

Coverage for the October 21, 2026 data snapshot, calculated from the repository
CSVs on October 22, 2026:
**401 of 503 ticker records have a ratio (79.72%); 102 are missing (20.28%).**

The paired-year export includes **396 matched tickers out of 503 (78.73%)**, or 792 rows across the two periods.
It excludes **107 tickers** without a complete, comparable annual pair.

| Sector | Latest available / total | Matched tickers | Excluded from paired plots | Matched % |
| --- | ---: | ---: | ---: | ---: |
| Communication Services | 11 / 22 | 11 | 11 | 50.00% |
| Consumer Discretionary | 35 / 47 | 35 | 12 | 74.47% |
| Consumer Staples | 26 / 34 | 25 | 9 | 73.53% |
| Energy | 11 / 21 | 11 | 10 | 52.38% |
| Financials | 74 / 76 | 74 | 2 | 97.37% |
| Health Care | 45 / 60 | 45 | 15 | 75.00% |
| Industrials | 66 / 83 | 64 | 19 | 77.11% |
| Information Technology | 67 / 75 | 66 | 9 | 88.00% |
| Materials | 17 / 24 | 17 | 7 | 70.83% |
| Real Estate | 29 / 30 | 29 | 1 | 96.67% |
| Utilities | 20 / 31 | 19 | 12 | 61.29% |

Latest availability counts use each current ticker’s latest financial period,
including tickers with no financial record. Matched counts require an available
ratio in both consecutive full annual periods. Missing values never become zero,
and older periods never replace a missing latest value. Both paired plots use
the same tickers. Share classes count separately. Zooming the axis hides extreme
values without changing the matched sample.

These counts were checked against the repository CSV inputs, not a fresh Neon
query. The published Tableau extract has not been independently reconciled
against them. October 21 is the data snapshot date; October 22 is the coverage
calculation date.
[Coverage source record](scratch/research/liabilities_to_assets_coverage.json).

Hover in Tableau for company details, ratio, fiscal dates and annual percentage
change on Latest points with a positive prior ratio. Read the distributions
alongside sector sample sizes, especially for interest coverage.

**Interest-coverage distribution by sector**

Interest coverage is operating income divided by annual total interest expense,
expressed as a multiple (×).

**Zoomed view (−10–65×)**

[![Previous and Latest interest-coverage distributions by sector, zoomed to −10–65 times](<docs/images/Interest Coverage Ratio Distribution (-10-65).png>)][tableau]

**Full-range view**

[![Previous and Latest interest-coverage distributions by sector, full range](<docs/images/Interest Coverage Ratio Distribution.png>)][tableau]

**Data coverage — interest coverage**

Coverage for the October 21, 2026 data snapshot, calculated from the repository
CSVs on October 22, 2026:
**96 of 503 ticker records have a ratio (19.09%); 407 are missing (80.91%).**

The paired-year export includes **94 matched tickers out of 503 (18.69%)**, or 188 rows across the two periods.
It excludes **409 tickers** without a complete, comparable annual pair.

| Sector | Latest available / total | Matched tickers | Excluded from paired plots | Matched % |
| --- | ---: | ---: | ---: | ---: |
| Communication Services | 6 / 22 | 6 | 16 | 27.27% |
| Consumer Discretionary | 9 / 47 | 8 | 39 | 17.02% |
| Consumer Staples | 9 / 34 | 9 | 25 | 26.47% |
| Energy | 3 / 21 | 3 | 18 | 14.29% |
| Financials | 2 / 76 | 2 | 74 | 2.63% |
| Health Care | 14 / 60 | 14 | 46 | 23.33% |
| Industrials | 13 / 83 | 13 | 70 | 15.66% |
| Information Technology | 15 / 75 | 15 | 60 | 20.00% |
| Materials | 7 / 24 | 7 | 17 | 29.17% |
| Real Estate | 7 / 30 | 7 | 23 | 23.33% |
| Utilities | 11 / 31 | 10 | 21 | 32.26% |

The counting rules and snapshot limitations above also apply here. Sectors
with only two or three observations cannot support a representative sector
distribution, even if Tableau can draw a box plot.
[Coverage source record](scratch/research/interest_coverage_counts.json).

[tableau]: https://public.tableau.com/views/SP500FinancialAnalysisOctober212026Data/Liabilties-to-Assets-Distribution?:language=en-US&:sid=&:redirect=auth&:display_count=n&:origin=viz_share_link

<details>
<summary>Tableau data preparation and color definitions</summary>

| Location | Purpose |
| --- | --- |
| [src/database/sql/](src/database/sql/) | Create reusable sector-ranking views for the tool. |
| [tableau_prep/](src/database/sql/tableau_prep/) | Prepare datasets for the author's Tableau charts. |

The read-only distribution queries are `liabilities_to_assets_distribution.sql`
and `interest_coverage_distribution.sql`. Each returns two rows per matched
current ticker, labeled `Previous` and `Latest`, with their own fiscal dates and
ratio values. The same companies appear in both periods for a fair comparison.
The matching is independent for each metric, so the two metrics can have
different matched samples.

The prior period must end the day before the latest period starts, and both
periods must span 364–371 days (calendar years or 52/53-week years). Both ratios
must be available for that metric. Gaps, missing dates, shorter transition
periods or missing ratios exclude the company from both plotted periods; no
older valid observation is substituted. The coverage tables above disclose
those exclusions against all current tickers.

`comparison_period` labels the two distributions as Previous and Latest.
Quartiles and median-distance scores are calculated separately for each sector and comparison period, using only the matched sample.

Each row contains its own fiscal dates and ratio. The Latest row also includes
year-over-year percentage change; this field is NULL on Previous rows.
Percentage change is `100 × (latest − previous) / previous`, calculated only
when the prior ratio is positive. A zero or negative baseline gives NULL for
percentage change, but its company remains in both plots. For example,
liabilities/assets rising from 0.60 to 0.66 is +10%, equivalent to a
6-percentage-point increase.

Run the selected query in Neon's SQL editor after loading the `companies` and
`financials` tables, then export a CSV for Tableau Public. Google Sheets is not needed.
These queries do not change stored data and are not run by `main`; publishing
Tableau is separate from running the tool.

**Gradient:** `median_distance_iqr` is the absolute difference between a company's
ratio and its sector median, divided by sector IQR (P75 − P25). A score of 0 is at
the median; 1 is one IQR away on either side. Missing ratios or zero IQR produce
NULL. Use Average on Color as a continuous measure, with green for low distances
and red for high distances. The liabilities/assets snapshots use a color range
of 0–4; the interest-coverage snapshots use 0–5. Values above each range share
the strongest red. Color indicates statistical distance, not financial
health or an exact outlier cutoff.

**Outliers:** Tableau's native box plot uses the 1.5 × IQR setting.
Whiskers end at the most extreme observed values within the limits;
points beyond them are outliers. No outlier flag is exported by the SQL.
Outliers identify review candidates, not financial distress or extraction errors.

In Tableau, place sector followed by `comparison_period` on Columns, the ratio
on Rows and ticker on Detail. Manually sort `comparison_period` to put Previous
before Latest. Use the built-in box plot with the 1.5 × IQR setting and an average
reference line per cell. Add year-over-year change to Tooltip; it is populated
only for Latest rows. Keep the SQL and Tableau samples consistent: filtering companies can
change Tableau's statistics while the exported scores remain fixed. To zoom,
change the axis range rather than filtering out extreme company values.

</details>

## Data rules and assumptions

- Use explicit standard concepts according to the reviewed definitions. Do not
  interpret company-specific custom concepts or substitute vaguely similar tags.
- Trust compliant filing structures, correct namespace bindings and Edgar's
  parsing. Exact concept searching is not an independent taxonomy validator.
- Select non-dimensioned facts from the requested filing. Match the exact instant
  date or both duration dates. There is no separate context-CIK equality check.
- Treat USD as a scope assumption for the selected companies and consolidated
  concepts. **The code does not check units or convert currencies.** Permitted
  non-USD reporting exceptions are outside supported coverage and are not detected.
- Use the reported value first, then the explicit accounting fallbacks below.
  Return the first successful result, including zero. Do not reconcile alternatives.
- Preserve missing results as blank CSV cells and SQL `NULL`, not zero. The loader
  uses pandas' inferred numeric types and converts missing cells to Python `None`.
  Missing results do not distinguish undisclosed inputs from unsupported structures.
- Require every input to a formula. An absent component does not automatically
  mean zero; this includes noncontrolling interest and temporary equity.
- Trust compliant duplicate facts and accepted rounding differences. Use Edgar's
  dataframe duplicate handling, then the first nonmissing matching row. No independent
  precision ranking or conflicting-value reconciliation is performed.
- Convert numeric text to Python `float` and use ordinary arithmetic for these
  analytical ratios. No Decimal module or custom arithmetic context is used.

Annual starts come from the matching `DocumentType`, `DocumentFiscalPeriodFocus`
and `DocumentPeriodEndDate` contexts. Exactly one shared start must be found.
This avoids assuming that every annual reporting period is 350–380 days long.

These are retrieval policies under a defined scope, not a promise to validate
arbitrary filings. Missing or unusable selected data returns `None`; unexpected
parser, network or malformed-input errors are not all converted to `None`.

## Accounting fallbacks

Exact concept names are written in the respective metric modules. Definitions
were reviewed against the US GAAP 2026 baseline; standards research is done
beforehand, not downloaded at runtime.

| Metric | Order after its direct concept is unavailable |
| --- | --- |
| Assets | Current + noncurrent assets; liabilities-and-equity total; liabilities + net assets; liabilities + inclusive permanent equity + temporary equity. |
| Liabilities | Current + noncurrent liabilities; assets − net assets; assets − inclusive permanent equity − temporary equity. |
| Inclusive permanent equity | Inclusive permanent partners’ capital; parent equity + noncontrolling interest; derived partners’ capital; equity before treasury stock − treasury stock. |
| Inclusive temporary equity | Parent temporary equity + redeemable noncontrolling equity. |
| Total interest expense | Operating + nonoperating expense; total interest income − total net interest; incurred interest − capitalized interest; total income − operating net − nonoperating net; operating expense + derived nonoperating expense. Every term is required. |
| Operating income | Subject to the explicit-zero restriction below: gross profit − operating expenses; revenues − costs and expenses; the same identities with gross profit or operating expenses reconstructed using cost of revenue. |

The operating-income fallbacks require both other operating income/expense and
operating government-assistance income to be established as zero, directly or
through complete compatible inputs. Missing or nonzero adjustments remain
unsupported by these fallbacks. This is a conservative implementation restriction,
not an SEC requirement to report zero facts.

Assets and liabilities use helpers excluding the final equity identity to avoid
circular calls. Intermediate values with their own fallbacks have separate modules;
shared components use one implementation. The retained research evidence records
the reviewed definitions and scope restrictions.

## Limitations

- **Ticker changes:** database records are keyed by ticker, and ticker changes
  are not automatically reconciled. Later loads can retain rows under the old
  ticker while adding rows under the new ticker, splitting or duplicating a
  company's stored history. Filing retrieval still uses CIK; the retained CIK
  column in `companies` can identify the connection between those records.
- **Unverified fallback coverage:** supported SG&A, regulated/unregulated revenue
  and LLC members' equity identities have constructed tests, but their recovery
  of actual missing S&P 500 results has not been established by the samples.
- **Coverage gaps:** additional justified accounting fallbacks and permitted
  standard filing structures remain to be implemented. Returning `None` does not
  automatically make an amount unobtainable.
- **Unverified coverage:** all S&P 500 issuers and periods, complete historical
  semantic comparability, and deployed PostgreSQL/view behavior have not been
  comprehensively established by the current tests.
- **Intentional exclusions:** custom-concept interpretation, malformed or
  misbound data, permitted non-USD reporting exceptions, calculation-linkbase
  retrieval and amended filings are outside current supported behavior.
- **Known filing-tag issue:** Vistra's FY2025 interest-coverage result is about
  −22.42×. Its filing tags a $40 million plant-restoration cost as incurred
  interest; subtracting $125 million capitalized interest produces a −$85 million
  denominator. The stored ratio has not been corrected. Investigate the source
  mismatch before interpreting this point; do not remove negative ratios generally.
  [Source filing](https://www.sec.gov/Archives/edgar/data/1692819/000169281926000006/vistra-20251231.htm).
- **Information limits:** compliant filings need not disclose every component
  required for our ratios. A net amount may not determine its gross components,
  and rounded amounts may not determine a unique underlying value.

## Tests and evidence

- **Offline unit tests:** 41 checks cover retrieval and accounting fallbacks,
  concurrent extraction order, failure handling, database loading with NULLs and
  Tableau preparation. The seven Tableau checks cover latest-period selection,
  current membership, calendar and 52/53-week years, missing observations, annual
  gaps, nonpositive baselines, separate period statistics and zero IQR.
- **Archived filings:** four financial inputs and both ratios are compared with
  the frozen baseline across 22 filings from six companies, including missing
  states. This verifies regression consistency, not universal accounting correctness.
- **SQL limits:** Tableau tests use SQLite percentile substitutes and integer
  date ordinals. They do not verify live PostgreSQL execution or precision.

Run both checks offline, without replacing production CSVs or writing the database:

```sh
PYTHONPATH=src .venv/bin/python -B -m unittest discover -s scratch/tests -p 'test_*.py'
.venv/bin/python -B scratch/tests/verify_archived_filings.py
```

[scratch/tests/](scratch/tests/) contains the tests and archived filing fixtures.
The fixture ZIP and instance manifest are required for the archived check.
[scratch/research/](scratch/research/) retains the two coverage records,
[accounting research evidence](scratch/research/research_evidence.json) and its
[source manifest](scratch/research/source_manifest.json). Historical research
includes observations whose exploratory runners and source downloads are no
longer retained; it is not all independently rerunnable or owner-reviewed.

## Roadmap

| Measure or feature | Planned definition and scope |
| --- | --- |
| Current ratio | Current assets / current liabilities. |
| Revenue growth | Change in annual revenue relative to the preceding comparable annual period. Establish the revenue concepts, comparison basis and zero/missing prior-period treatment before implementation. |
| Operating margin | Annual operating income / annual revenue, using the same reporting period and scope. |
| Free cash flow (FCF) | Operating cash flow minus a clearly defined capital-expenditure measure. Establish which expenditures are included and normalize the cash-outflow sign before implementing the subtraction. |
| FCF margin | Potential extension: defined free cash flow / revenue for the same period. |
| Calculation-linkbase retrieval | Revisit recovery of missing values if the coverage benefit warrants the additional code; preserve the applicable relationship semantics. |

Revenue retrieval is a shared prerequisite for revenue growth, operating margin
and any FCF margin. The planned metrics are not implemented yet. Their exact
standard concepts, component boundaries and fallback rules still require review;
listing a formula here does not approve every possible tag substitution.

The liabilities/assets measure uses **total liabilities** as its numerator.
Interest-bearing debt must not silently replace it when extending the project.

Both metrics' matched Previous/Latest distributions and zoomed counterparts are
published on Tableau Public, with linked previews above for the October 21, 2026
data snapshot. Next steps are to reconcile coverage with the published extracts
and review the distributions before writing findings. Automatic Tableau updates
are outside the tool's scope. Further research questions are:

| Analysis | Question and scope |
| --- | --- |
| Annual company changes | Which companies' liabilities/assets ratios changed most? Calculate percentage-point differences between comparable consecutive annual periods; preserve missing observations and flag gaps. |
| Matched-company sector trends | Are changes widespread within sectors? Compare the same companies across periods, reporting median company change and the share with an increase. |
| Company position within its sector | How does each company's latest ratio compare with its sector median and percentile? Keep the reporting period visible. |
| Interest-coverage histories | How does available coverage change within each company? Preserve gaps and avoid inferring the cause of negative ratios without the underlying amounts. |
| Correlation exploration (deferred) | Potential future analysis of liabilities/assets versus interest coverage within sectors, using company-level scatter plots and correlation summaries. Inspect the patterns and validate inputs before deciding whether Pearson, Spearman or another approach is appropriate. |

Correlation is deferred while the current analysis focuses on matched annual
box plots. No correlation analysis is currently implemented; validate inputs
before pursuing it.

**Potential correlation data coverage (calculated separately from the repository
CSV snapshot):** only **69 of 503 ticker records (13.72%)** have both ratios for
their latest stored period. Sector samples are smaller still, and available
companies may not represent those with missing ratios. Fiscal dates can differ
between tickers, and share classes remain separate observations. Total liabilities
also include non-interest-bearing obligations, so a relationship with interest
coverage is indirect. Any future analysis should report sample sizes and coverage
separately and should not interpret correlation as causation.

## Analytical framework

The project is organized around four questions:

1. **Likelihood of failure:** how vulnerable is a company to financial distress or default?
2. **Loss or recovery conditional on failure:** how protected is a stakeholder if failure occurs?
3. **Likelihood of growth or contraction:** which direction might the business move?
4. **Magnitude of growth or contraction:** how large might the upside or downside be?

The implemented and planned measures provide accounting inputs for investigating these questions.
They are not calibrated probabilities, recovery estimates or forecasts. The
framework is the analytical objective; the pipeline currently produces historical
financial measures.

Liabilities/assets, interest coverage and the planned current ratio support the
assessment of financial vulnerability. Revenue growth and operating margin will
add business-direction and profitability measures; free cash flow will add a
measure of cash generation after defined capital expenditures. These are intended
uses, not claims that one ratio answers a framework question by itself.

Stakeholder recovery and the magnitude of future outcomes remain separate analysis
problems. Book assets are not a liquidation valuation, and the current pipeline
does not model claim priority, stakeholder-specific recovery or future scenarios.

## Design decisions

The pipeline uses Edgar for filing retrieval and parsing, with explicit concept
searches and accounting formulas in small Python modules. It does not implement
custom XML parsing, a runtime taxonomy engine or a general inference framework.

- **Accounting boundaries:** parent-only equity is not inclusive equity; cash
  interest paid is not accrued interest expense; a net interest amount alone does
  not establish gross expense. Operating-income fallbacks retain their explicit
  zero-adjustment restriction. Reviewed but unsupported equations stay out of
  production.
- **Historical comparability:** definitions were reviewed against the 2026
  taxonomy and selected 2021–2026 releases. Some interest concepts first appear
  in 2024. There is no runtime taxonomy-version gate or guarantee of equivalent
  meaning across all years.
- **Calculation linkbases:** retrieval is deferred to keep the implementation
  small. In an earlier comparison, disabling it removed liabilities/assets for
  ten AMD and Walmart filings. This is a known coverage tradeoff, not evidence
  that missing values are impossible to recover.

Detailed definition histories, candidate equations, filing observations and
rejected substitutions remain in the [research evidence](scratch/research/research_evidence.json).
Official definitions and reporting guidance are linked below.

<details>
<summary>Extraction performance</summary>

<a id="extraction-performance"></a>

The three-worker setting is based on user-reported extraction runs: 2,023 seconds
with one worker versus 1,671 seconds with three, about 17% faster. Two workers took
1,689 seconds; higher worker counts were slower. These were individual runs with
potentially different cache and network conditions, not a controlled benchmark.
EdgarTools shares a 9-request/second limiter across threads, below the
[SEC limit](https://www.sec.gov/about/developer-resources).

</details>

## Official references

- [SEC accepted standard taxonomies](https://www.sec.gov/data-research/structured-data/taxonomies-schemas/standard-taxonomies)
- [US GAAP 2026 definitions](https://xbrl.fasb.org/us-gaap/2026/elts/us-gaap-doc-2026.xml)
- [US GAAP 2026 schema](https://xbrl.fasb.org/us-gaap/2026/elts/us-gaap-2026.xsd)
- [SEC XBRL Guide](https://www.sec.gov/files/edgar/xbrl-guide.pdf)
- [SEC interactive-data interpretations and FAQs](https://www.sec.gov/data-research/structured-data/office-structured-disclosure-staff-observations-guidance-trends/staff-interpretations-faqs-related-interactive-data-disclosure)
- [S&P U.S. Indices Methodology](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-indices.pdf): index eligibility and domestic reporting criteria.
- [Regulation S-X 3-20(a)(2)](https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol3/pdf/CFR-2025-title17-vol3-sec210-3-20.pdf): general USD reporting requirement for non-foreign-private issuers.
- [SEC Financial Reporting Manual §6640](https://www.sec.gov/about/divisions-offices/division-corporation-finance/financial-reporting-manual/frm-topic-6): limited staff exceptions to USD reporting.
- [Regulation S-X §4-02](https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol3/pdf/CFR-2025-title17-vol3-sec210-4-04.pdf): immaterial amounts need not be separately presented; omission alone does not establish zero.
