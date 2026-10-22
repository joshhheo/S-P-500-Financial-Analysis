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

**Liabilities-to-assets distribution by sector**

[![Liabilities-to-assets distribution by sector, zoomed to ratios from 0 to 1.5](<docs/images/Liabilities-to-Assets Distribution by Sector (0-1.5).png>)](https://public.tableau.com/shared/F7QJ9GZWD?:display_count=n&:origin=viz_share_link)

[Explore the interactive charts on Tableau Public](https://public.tableau.com/shared/F7QJ9GZWD?:display_count=n&:origin=viz_share_link)

The zoomed view makes the sector distributions easier to compare; values outside
0–1.5 are not displayed. Each dot represents a ticker with an available ratio.
Boxes show the middle 50% of values, with the median inside each box. Whiskers
end at the outermost observed values within the 1.5 × IQR thresholds. Dot colors
show distance from the sector median in IQRs, not financial health.

<details>
<summary>View the full-range chart, including extreme outliers</summary>

[![Full-range liabilities-to-assets distribution by sector](<docs/images/Liabilities-to-Assets Distribution by Sector.png>)](https://public.tableau.com/shared/F7QJ9GZWD?:display_count=n&:origin=viz_share_link)

</details>


**Data coverage — liabilities-to-assets**

Coverage calculated on October 22, 2026 from the repository CSV snapshot:
**401 of 503 ticker records have a ratio (79.72%); 102 are missing (20.28%).**

| Sector | Available / total | Missing | Missing % |
| --- | ---: | ---: | ---: |
| Communication Services | 11 / 22 | 11 | 50.00% |
| Consumer Discretionary | 35 / 47 | 12 | 25.53% |
| Consumer Staples | 26 / 34 | 8 | 23.53% |
| Energy | 11 / 21 | 10 | 47.62% |
| Financials | 74 / 76 | 2 | 2.63% |
| Health Care | 45 / 60 | 15 | 25.00% |
| Industrials | 66 / 83 | 17 | 20.48% |
| Information Technology | 67 / 75 | 8 | 10.67% |
| Materials | 17 / 24 | 7 | 29.17% |
| Real Estate | 29 / 30 | 1 | 3.33% |
| Utilities | 20 / 31 | 11 | 35.48% |

Counts use each current ticker’s latest financial period, including tickers
with no financial record. A missing latest ratio is not filled from an older
period. Multiple share classes count separately, matching the chart’s ticker
grain. Missing ratios are omitted from the plotted distribution; the zoomed
axis also hides values outside 0–1.5 without changing this availability count.

These counts describe the repository inputs, not a fresh Neon query. The
published Tableau extract has not been independently reconciled against them.
The calculation date above is not a confirmed chart export date.
[Coverage source record](docs/data/liabilities_to_assets_coverage.json).

Each company uses its latest stored financial period, which can differ from other
companies' periods. Hover in Tableau for company details, ratio, fiscal dates and
outlier status. The financial-period dates describe the data, not the export date.
Coverage varies by sector, so read the distributions alongside available sample
sizes, especially for interest coverage. Missing ratios are excluded from the
chart, never treated as zero.

<details>
<summary>Tableau data preparation and color definitions</summary>

| Location | Purpose |
| --- | --- |
| [src/database/sql/](src/database/sql/) | Create reusable sector-ranking views for the tool. |
| [tableau_prep/](src/database/sql/tableau_prep/) | Prepare datasets for the author's Tableau charts. |

The read-only queries are `liabilities_to_assets_distribution.sql` and
`interest_coverage_distribution.sql`. They share one folder so future charts can
combine both ratios. Each returns one row per current ticker: company name,
sector, fiscal-period dates, the selected ratio, `median_distance_iqr` and
`is_outlier`. A missing latest ratio is not replaced with an older observation.
Missing ratios remain in the export to support coverage calculations.

Run the selected query in Neon's SQL editor after loading the tables and creating
the views, then export a CSV for Tableau Public. Google Sheets is not needed.
These queries do not change stored data and are not run by `main`; publishing
Tableau is separate from running the tool.

**Gradient:** `median_distance_iqr` is the absolute difference between a company's
ratio and its sector median, divided by sector IQR (P75 − P25). A score of 0 is at
the median; 1 is one IQR away on either side. Missing ratios or zero IQR produce
NULL. Use Average on Color as a continuous measure, with green for low distances
and red for high distances. The snapshots use a color range of 0–5; values above
5 share the strongest red. Color indicates statistical distance, not financial
health or an exact outlier cutoff.

**Outliers:** `is_outlier` is TRUE below P25 − 1.5 × IQR or above P75 + 1.5 × IQR,
FALSE within those limits (including the boundaries), and NULL for missing ratios.
With zero IQR, a value different from the common quartile is an outlier even
though its normalized distance is NULL. Quartiles exclude missing ratios.
Outliers identify review candidates, not financial distress or extraction errors.

In Tableau, place sector on Columns, the ratio on Rows and ticker on Detail.
Use the built-in box plot with the 1.5 × IQR setting and an average reference line
per sector. Keep the SQL and Tableau samples consistent: filtering companies can
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
shared components use one implementation. The detailed review below records the
identities, scope restrictions and evidence behind these choices.

## Limitations

- **Ticker changes:** database records are keyed by ticker, and ticker changes
  are not automatically reconciled. Later loads can retain rows under the old
  ticker while adding rows under the new ticker, splitting or duplicating a
  company's stored history. Filing retrieval still uses CIK; the retained CIK
  column in `companies` can identify the connection between those records.
- **Implemented additions with unverified recovery:** the explicit SG&A
  complement, total regulated/unregulated operating revenue and inclusive LLC
  members' equity were absent. They now have direct-first, complete-input
  fallbacks. Their presence in the official taxonomy is established; recovery
  for actual missing S&P 500 results is not established by the samples.
- **Coverage gaps:** additional justified accounting fallbacks and permitted
  standard filing structures remain to be implemented. Returning `None` does not
  automatically make an amount unobtainable.
- **Unverified coverage:** all S&P 500 issuers and periods, complete historical
  semantic comparability, and deployed PostgreSQL/view behavior have not been
  comprehensively established by the current tests.
- **Intentional exclusions:** custom-concept interpretation, malformed or
  misbound data, permitted non-USD reporting exceptions, calculation-linkbase
  retrieval and amended filings are outside current supported behavior.
- **Information limits:** compliant filings need not disclose every component
  required for our ratios. A net amount may not determine its gross components,
  and rounded amounts may not determine a unique underlying value.

## Tests and evidence

- **Tests:** all 34 offline constructed and isolated checks pass, including
  concurrent extraction order, failure handling and database loading with NULLs.
  All four metrics and both ratios also match the frozen baseline across 22
  archived filings from six companies, including missing states. These establish
  tested behavior and regression consistency, not universal accounting correctness
  or complete deployed PostgreSQL behavior.
- **Investigations:** official-definition reviews established the explicit
  accounting fallbacks above and rejected substitutions with incompatible scope.
  A historical 30-filing null audit identified unavailable total-interest inputs
  and operating-income facts as immediate blockers; it did not demonstrate a
  selection or arithmetic bug explaining those nulls. Taxonomy changes explained
  some interest-coverage gaps, and no general missing-tag-equals-zero rule was
  established. Disney's negative expense was traced to the source tag, not Edgar's
  parsing. These samples do not establish full-index coverage or current null rates.
- **Tableau preparation:** these queries are separate from the Python test
  suite. Earlier distribution prototypes were compared using read-only synthetic
  PostgreSQL inputs, but those comparisons do not validate the current export
  queries or independently verify every company's source values.

The October 19, 2026 read-only SQL check reported 503 current ticker rows, 500 with
financial history, 401 latest liabilities/assets values and 96 latest
interest-coverage values. HONA, VYLR and XOM had no financial rows in that snapshot.
These are historical observations, not a fresh database check or a count of
unique issuers. The notebook and result export were removed; the
[Tableau preparation queries](src/database/sql/tableau_prep/) remain available
for a new export.

Scratch retains executable checks, diagnostic scripts, filing fixtures and source
evidence. Explanatory summaries belong here rather than in separate scratch reports.

[Tests and archived fixtures](scratch/tests/) are separate from
[research evidence](scratch/research/research_evidence.json) and its
[source manifest](scratch/research/source_manifest.json). The research includes
historical observations whose exploratory runners were removed; it is not all
rerunnable from the retained files. The broader AI-assisted analysis has not been
independently reviewed by the owner. The owner's small diagnostic scripts in
`scratch/research/` use live Edgar data; the checks below run offline without
writing production CSVs or the live database. The binary fixture archive,
`filing_documents.zip`, contains saved SEC filing XML; `instance_manifest.json`
records source metadata and expected results. Keep both for offline verification.

```sh
PYTHONPATH=src .venv/bin/python -B -m unittest discover -s scratch/tests -p 'test_*.py'
.venv/bin/python -B scratch/tests/verify_archived_filings.py
```

## Roadmap

| Measure or feature | Planned definition and scope |
| --- | --- |
| Current ratio | Current assets / current liabilities. Previously discussed; interest coverage became the immediate implementation priority. |
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

The liabilities-to-assets distribution is published on Tableau Public, with
linked previews above. Next steps are to document the confirmed export date,
reconcile the coverage disclosure with the published extract and develop the
written findings. Automated
dashboard updates are not required for the reusable tool. Further research
questions are:

| Analysis | Question and scope |
| --- | --- |
| Annual company changes | Which companies' liabilities/assets ratios changed most? Calculate percentage-point differences between comparable consecutive annual periods; preserve missing observations and flag gaps. |
| Matched-company sector trends | Are changes widespread within sectors? Compare the same companies across periods, reporting median company change and the share with an increase. |
| Company position within its sector | How does each company's latest ratio compare with its sector median and percentile? Keep the reporting period visible. |
| Interest-coverage histories | How does available coverage change within each company? Preserve gaps and avoid inferring the cause of negative ratios without the underlying amounts. |
| Combined ratio comparison | How do liabilities/assets and interest coverage relate where both are available for the same company and period? Include sample size and sector context. |

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

Current policies are summarized above. The detailed reviews below preserve the
reasoning, tested observations, rejected candidates and remaining uncertainty.
Earlier test counts and sample results describe those review stages.

<details>
<summary>Design decisions and retrieval assumptions</summary>

The original pipeline used short Edgar concept searches and separate metric files.
The review examined whether its selections and formulas were justified by official
concept definitions and permitted filing structures. A broader implementation
then added custom parsing, taxonomy metadata, linkbase traversal, reconciliation
and detailed diagnostics. We subsequently separated what is necessary to obtain
our defined values from what would be needed to validate arbitrary filings.
The current code returns to the simpler structure while retaining the selection
and accounting rules established by that review.

This distinction matters: **an official requirement, a tested observation and an
accepted scope assumption are different kinds of support.** Research established
the reporting rules and concept meanings; tests checked particular behaviors;
the project owner chose the coverage and precision tradeoffs. Neither the research
nor a passing sample establishes that every possible filing is handled.

### Company scope and the USD assumption

The [S&P methodology](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-indices.pdf)
requires U.S. domicile for index purposes and domestic periodic reporting.
This does not require every constituent to be incorporated in the United States.
[Regulation S-X 3-20(a)(2)](https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol3/pdf/CFR-2025-title17-vol3-sec210-3-20.pdf)
sets the general USD financial-reporting requirement for non-foreign-private
issuers. Our target is their consolidated financial amounts and defined accounting
components, rather than foreign-currency debt terms or subsidiary disclosures.
That combination supports USD as the normal reporting basis for this project.

We checked the apparent counterexamples. Microsoft and Walmart have actual
non-USD standard-tag debt disclosures, but the documented examples are dimensioned
and outside our current concept list. The scan of 22 archived filings found 38
non-USD facts and none using that list. Targeted external research did not establish
a qualifying S&P 500 consolidated counterexample for our selected values. This
is supporting evidence, not an exhaustive proof. [Recorded facts and contexts](scratch/research/research_evidence.json)

[SEC staff guidance §6640](https://www.sec.gov/about/divisions-offices/division-corporation-finance/financial-reporting-manual/frm-topic-6)
also documents limited non-USD reporting exceptions. We explicitly exclude those
from supported coverage. Initially the code enforced USD with a unit filter; the
owner then chose to trust the scoped reporting assumption instead. Currency
selection, conversion and unit checks were removed for that reason—not because
currency has no meaning or all facts anywhere in a 10-K must be USD.

### Trust Edgar to parse; keep accounting decisions explicit

The review distinguished parsing from interpreting a metric. Edgar can turn the
filing into searchable facts without deciding which alternative concept should
represent our total. We use its filing objects and exact concept queries, but
keep the metric names and accounting fallbacks in our own readable functions.
This avoids adopting a library convenience metric's unreviewed substitutions.

Manual XML readers and the `Source`/`FilingInstance` classes were removed because
we chose to trust compliant structure and correct standard namespace bindings.
An exact search matches a concept spelling; it is not a separate validation that
its prefix points to the correct official namespace. Custom tags are not searched
or interpreted, and deliberately misleading bindings are outside our assumptions.
The current design does not claim to detect them.

The CIK chooses the filing. We do not additionally require each fact context's
CIK to equal that requested CIK: the [SEC XBRL Guide](https://www.sec.gov/files/edgar/xbrl-guide.pdf),
§6.2.7, permits co-registrants to use a chosen CIK for their consolidated entity.
The earlier review did not demonstrate that our filing-specific searches returned
an unrelated company's facts. Dimension selection remains because consolidated
and component disclosures can coexist within the same filing. Selecting the
non-dimensioned default scope is our current retrieval policy; it is not a claim
that all dimensioned facts are noncompliant or never useful.

### Dates remain necessary even when the filing is correct

A valid annual filing contains comparative years and facts for different periods.
Selecting the right company and concept therefore does not establish the right
date. The later original pipeline already matched requested dates correctly; we
kept that behavior rather than treating it as a defect requiring a new framework.

The separate question was how to choose the annual start. The inspected Edgar
version labels durations of 350–380 days as Annual. That is a useful classification,
but it is not the filing's explicit declaration of the required reporting period.
The small DEI-based helper preserves reported starts, including shortened periods,
and returns `None` when it cannot identify one. Constructed tests cover this
behavior; no wrong numeric result from the earlier annual-label selection was
established in the 22-filing sample.

### Definitions establish formulas; omission does not establish zero

The [accepted taxonomy list](https://www.sec.gov/data-research/structured-data/taxonomies-schemas/standard-taxonomies)
establishes which taxonomies the SEC accepts. The
[FASB definitions](https://xbrl.fasb.org/us-gaap/2026/elts/us-gaap-doc-2026.xml)
establish concept meanings. Neither makes every combination of standard tags a
valid equation. We reviewed component scope and wrote the supported formulas
explicitly; custom-tag interpretation and guessed net-to-gross substitutions were
excluded.

For example, the project does not use parent-only equity as inclusive equity merely
because a noncontrolling-interest tag is absent. The initial suggestion that zero
NCI is normally omitted did not establish the reverse implication that every
omission means zero. [Regulation S-X §4-02](https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol3/pdf/CFR-2025-title17-vol3-sec210-4-04.pdf)
permits immaterial amounts to be combined rather than separately presented.
Likewise, `GrossProfit − OperatingExpenses` was not retained as a universal
operating-income formula: the selected expense concept must actually represent
the appropriate nonoverlapping component. These are reasons for requiring complete,
well-defined inputs, not reasons to build a general inference engine.

### Standards research happens before runtime

We reviewed official definitions and schemas for the 2026 baseline and compared
relevant earlier releases used by the archived filings. The
[historical comparison](scratch/research/research_evidence.json)
records differences; for example, the operating/nonoperating interest concepts
first appear in 2024 in the checked releases. Those differences were not erased
by simplifying the code.

The decision was to put reviewed concept names directly in metric modules and
document the baseline, rather than download standards, maintain a runtime concept
registry or reject filings through a namespace-year gate. This reduces machinery
but leaves future definition changes and some historical comparability unverified.
Updating the baseline requires another explicit review.

### Duplicate selection and alternative fallbacks are deliberate tradeoffs

Under the compliant-input assumption, equal reported facts and consistent rounded
duplicates do not require an independent reconciliation framework for this project.
We accepted Edgar's duplicate handling and first-nonmissing-row selection, rather than
preserving precision intervals and dependency graphs. That is an implementation
choice with accepted rounding differences, not an SEC mandate to select the first
row. The [SEC XBRL Guide](https://www.sec.gov/files/edgar/xbrl-guide.pdf) discusses
numeric duplicate consistency and accuracy; the project does not independently
revalidate those conditions.

After scope and period filtering, retrieval skips missing values and empty strings,
then returns the first remaining value. Zero is retained. If no value remains,
it returns `None`; a blank match no longer discards another numeric match. This
is our selection policy under the documented scope assumptions, not an SEC rule.

Similarly, direct values take precedence and later fallback results are not
compared after one succeeds. A returned zero is a result, not a reason to continue.
Retrieval and ratios use ordinary Python floats. Detailed missing-reason objects and
provenance classes were removed in favor of values/`None`, with reporting dates retained in the financial output and CIK in company data.

### Why calculation-linkbase support was deferred

We implemented and tested filed calculation relationships, then measured what
happens without them. Disabling the linkbase while keeping the same direct facts
and accounting fallbacks removed liabilities and liabilities-to-assets for AMD and Walmart
in five filings each. Other outputs did not change in the sample.
[Measured comparison](scratch/research/research_evidence.json)

Simple candidate formulas reproduced all ten liabilities numerically. However,
missing equity categories prevented us from proving those candidates complete as
general accounting fallbacks. The test therefore demonstrated dependence on the
then-current implementation, not that the values were mathematically impossible
to derive another way. [Candidate identity comparison](scratch/research/research_evidence.json)

The owner chose simpler code and reduced coverage over calculation-network
parsing, priority/prohibition handling and traversal. Those features were removed,
including their supporting architecture. The affected values currently remain
missing. This is a known recoverable coverage gap and a future feature—not proof
that linkbases have negligible value or that `None` resolves the gap.

</details>

<details>
<summary>Accounting derivations, module structure and research findings</summary>

### Full inventory and nested-derivation review: completed work and remaining scope

The next review downloaded the complete official
[US GAAP 2026 archive](https://xbrl.fasb.org/us-gaap/2026/us-gaap-2026.zip) and
[SRT 2026 companion archive](https://xbrl.fasb.org/srt/2026/srt-2026.zip).
Their URLs and SHA-256 hashes are retained with the research. These are offline
research inputs, not pipeline dependencies.

The recorded [inventory results](scratch/research/research_evidence.json) cover
**17,802 schema elements, including 7,542 monetary elements**, and
**1,845 reference calculation groups**. Starting with the four main metrics,
following parent-to-component relationships reaches 1,851 concepts in seven passes.
Allowing traversal through relationships in either direction reaches 4,024 concepts
in thirteen passes. The next pass adds nothing. This traversal is candidate
discovery, **not validation of those equations or a runtime calculation engine**.

The [ledger](scratch/research/research_evidence.json) records
54 reviewed equation boundaries, their definitions and reference-group locations.
Every reference group immediately touching a current production concept has a
recorded parent decision. The full per-element inventory was removed during test
cleanup; the counts and conclusion-specific relationships remain. Nonmonetary elements are not direct monetary
inputs; that does not prove they cannot participate in a more elaborate formula.

The sequential first pass has now read **all 7,485 US GAAP monetary definitions**,
the **57 SRT monetary definitions**, and **1,158 other numeric/rate definitions**
(1,081 US GAAP and 77 SRT). The
[review record](scratch/research/research_evidence.json) retains
the inclusive ranges and candidate dispositions. The ledger separates a definition
having been read from an equation having been approved. Text, axes and other
nonnumeric elements were inventoried, not individually read in this numeric pass.

**This completes that definition-screening pass, not a proof of every possible
derivation.** The reference graph is finite, but its relationships are not a
complete specification of accounting identities. Many definitions describe a
component without establishing a complete, disjoint partition of its parent.
Those cases remain unverified coverage, rather than being relabeled as filing
errors or unavoidable missing information. Other accepted SEC taxonomy families
were not exhaustively reviewed; this pass covers the project's US GAAP/SRT scope.

The definition review did establish these additional nested identities:

| Intermediate value | Complete-input identity | Important scope detail |
| --- | --- | --- |
| Inclusive partners' equity | `PartnersCapital + PartnersCapitalAttributableToNoncontrollingInterest` | Temporary equity remains separate. |
| Treasury stock | `TreasuryStockCommonValue + TreasuryStockPreferredValue` | Both carrying amounts required; absence is not zero. |
| Inclusive permanent equity | `StockholdersEquityBeforeTreasuryStock − TreasuryStockValue` | The before-treasury definition already includes noncontrolling interests. Do not add them again. |
| Redeemable noncontrolling equity | `RedeemableNoncontrollingInterestEquityCommonCarryingAmount + RedeemableNoncontrollingInterestEquityPreferredCarryingAmount + RedeemableNoncontrollingInterestEquityOtherCarryingAmount` | All three carrying amounts required; this feeds temporary equity. |
| Operating government-assistance income | `GovernmentAssistanceAmount − GovernmentAssistanceNonoperatingIncome` | The operating-income fallback still requires the result to equal zero. |
| Operating expenses | `OperatingCostsAndExpenses + SellingGeneralAndAdministrativeExpense` | The first explicitly excludes SG&A; the target explicitly includes it. Both inputs required. |
| Operating revenue | `RegulatedAndUnregulatedOperatingRevenue`, otherwise `RegulatedOperatingRevenue + UnregulatedOperatingRevenue` | The aggregate definition says total operating revenue. Both portions required for the sum. |
| Inclusive LLC members' equity | `MembersEquity + MembersEquityAttributableToNoncontrollingInterest` | Direct inclusive LLC equity takes precedence. Temporary equity remains separate. |

The equity concepts above have unchanged definitions in the archived 2021–2026
releases. `GovernmentAssistanceAmount` had broader recognition wording in 2022;
its 2024 definition describes income. The nonoperating-income component first
appears in 2024, so the new identity requires that newer concept as well. No
runtime taxonomy download or version-selection framework was added.

Several promising-looking candidates were **not** added:

- Contract revenue plus noncontract revenue requires the assessed-tax basis to
  match the company's reporting policy. The reference archive also contains a
  bank revenue presentation with net interest, whereas the generic `Revenues`
  definition includes interest before deduction of interest expense. A template
  relationship alone cannot settle that scope difference.
- The noncurrent-liability reference group combines debt-and-lease obligations
  with liabilities other than long-term debt. The latter definition does not
  explicitly exclude finance leases. Blind addition is not justified without
  establishing a disjoint partition.
- Security-only interest income, debt-category expense totals, share-class equity
  sums and detailed balance-sheet lists still need matching scope and completeness.
  Finding additional component tags does not establish an exhaustive partition.

The three latest identities above have unchanged definitions across 2021–2026.
Their supporting definitions are in the official
[2026 documentation](https://xbrl.fasb.org/us-gaap/2026/elts/us-gaap-doc-2026.xml);
the reviewed earlier definitions and source references are retained with the research.
The full earlier taxonomy downloads were removed during cleanup. The LLC presentation
in `stm/us-gaap-stm-sfp-cls2-cal-2026.xml` separately places temporary equity and
inclusive members' equity beneath liabilities and equity. That supports keeping
temporary equity separate; it does not authorize treating absent temporary equity
as zero or summing every template child indiscriminately.

The archived [candidate comparison](scratch/research/research_evidence.json)
tested 20 explicit equations against the 22 archived filings, recording exact
inputs, accessions, source URLs and definition histories in
[its results](scratch/research/research_evidence.json).
These comparisons exposed useful boundaries:

- Total long-term debt less current debt matched 13 reported noncurrent amounts.
  However, the **2022** total/noncurrent definitions exclude unamortized carrying
  adjustments while the current definition retains the earlier wording. This is
  not an unconditional cross-version identity. It also does not solve the missing
  complete partition of noncurrent liabilities.
- Domestic plus foreign pretax income matched 17 inclusive reported totals. The
  official income-tax reference places those components under the subtotal
  **before equity-method income**. The matches do not establish universal
  inclusive scope. Other after-tax/OCI/pretax component identities do not solve
  the unresolved bridge from pretax income to operating income or total interest.
  Unused intermediate modules were therefore not added.
- Current plus deferred tax had 17 complete comparisons, two unequal: AMD 2022
  and 2023. The archived inputs contain positive deferred-tax amounts of
  $1.505 billion and $1.019 billion, respectively, whereas subtracting them from
  current tax reproduces the reported tax benefits. The raw 2022 XML confirms
  the positive amount. This is a conflict to investigate, not permission to
  change signs or proof that the accounting identity is invalid.
- JPMorgan 2025 reports both gross and net revenue concepts as $182.447 billion
  and operating interest expense as $97.898 billion in the matched context.
  Subtracting those revenue facts yields zero. The cause is not established;
  this sample does not validate a universal gross/net reversal.
- EPS, tax-rate, borrowing-rate and regulatory-ratio inversions were not added.
  Their denominators, ownership scope, time basis or rounding can differ from
  the requested monetary total. Period-end debt times a rate is not annual
  accrued interest; regulatory/risk-weighted/average assets are not period-end
  GAAP assets. This is an implementation boundary, not a claim that no particular
  filing could supply enough compatible information.

The newly added expense, regulated-revenue and members'-equity partitions had
**no complete input sets in the archived sample**. Their arithmetic, missing-input,
zero and priority checks are constructed evidence. Their real-filing coverage
remains unverified. No claim of improved S&P 500 recovery follows from these tests.

### Modules for intermediate values

An intermediate value with its own fallback now has its own module. `get_equity`
returns only inclusive **permanent** equity; `get_temporary_equity` returns temporary
equity. Assets and liabilities retrieve both separately when that identity is used.

The four main metric modules remain at the top level. Supporting modules live in
folders named for the metric they support, with deeper fallbacks nested beneath
their intermediate metric. Shared components live at their nearest common level
so there is only one implementation of each formula.

```text
value_retrieval/
├── get_value.py
├── get_assets.py
├── get_liabilities.py
├── assets_and_liabilities/
│   ├── get_equity.py
│   ├── equity/
│   │   ├── get_partners_equity.py
│   │   ├── get_members_equity.py
│   │   └── get_treasury_stock.py
│   ├── get_temporary_equity.py
│   └── temporary_equity/
│       └── get_redeemable_noncontrolling_equity.py
├── get_operating_income.py
├── operating_income/
│   ├── get_gross_profit.py
│   ├── get_operating_revenue.py
│   ├── get_operating_expenses.py
│   └── get_government_assistance_operating_income.py
├── get_interest_expense.py
└── interest_expense/
    ├── get_operating_interest_expense.py
    ├── get_nonoperating_interest_expense.py
    ├── get_operating_interest_income.py
    ├── get_operating_net_interest.py
    ├── get_net_interest.py
    └── get_capitalized_interest.py
```

Operating revenue is shared by gross-profit and operating-income retrieval.
Operating interest income and net interest also support multiple fallbacks, so
they remain directly inside `interest_expense/`. Current/noncurrent direct tag
lookups stay in the existing main modules; no empty folders or wrapper modules
are needed for concepts that have no implemented fallbacks of their own.

| Module(s) | Responsibility |
| --- | --- |
| `get_partners_equity`, `get_members_equity`, `get_treasury_stock` | Resolve their direct amounts or complete component identities for permanent equity. |
| `get_redeemable_noncontrolling_equity`, `get_temporary_equity` | Resolve redeemable NCI, then combine it with parent temporary equity. |
| `get_operating_interest_income`, `get_operating_net_interest` | Resolve operating income from interest/dividend amounts and operating net interest from total/nonoperating net amounts. |
| `get_operating_interest_expense`, `get_nonoperating_interest_expense` | Resolve each expense classification independently from its compatible income/net inputs. |
| `get_net_interest`, `get_capitalized_interest` | Resolve total net interest and the alternative capitalized-interest tags. |
| `get_operating_revenue`, `get_gross_profit`, `get_operating_expenses` | Resolve operating revenue, revenue-minus-cost, and the reviewed expense identities. |
| `get_government_assistance_operating_income` | Resolve direct operating assistance or total assistance income less nonoperating assistance income. |

These functions use literal concept searches and explicit arithmetic. They do not
call back into the main metric to manufacture a required component. Existing
identity order is preserved: some main modules therefore try a reported pair
before calling the intermediate modules for deeper fallbacks.

**Validation:** all 34 constructed/integration tests pass, and all 22 archived
filings retain their frozen baseline. The read-only comparison of 30 exact saved
S&P 500 filings preserves all existing ratios and recovers **no additional ratios**
in that sample. The sample did not supply complete inputs for the new nested
identities, so their arithmetic/missing-input tests are constructed evidence,
not independent real-filing confirmation. All 55 literal production concepts were
checked against the official definitions/schema and their 2021–2026 definition
history. The full pipeline was not run; production CSV hashes remained unchanged
and the live database was not accessed.

The exploratory inventory runner and full downloaded taxonomies were removed after review.
The retained evidence contains the counts, equation decisions, relevant relationships,
definition histories and source hashes; it does not reproduce the full inventory.

### Review of additional standard-concept equations

The initial follow-up review verified the **36 literal US GAAP concepts then used by
retrieval** against the official 2026 definitions and schema, and compared their
definitions across the archived 2021–2026 releases. The
[definition history and real-filing results](scratch/research/research_evidence.json)
are scratch evidence, not a runtime taxonomy dictionary or downloaded rules engine.

Additional equations and their limits:

- `Assets = Liabilities + AssetsNet`, and the inverse for liabilities. These use
  reported net assets, not inferred zero temporary equity or noncontrolling interest.
- `PartnersCapitalIncludingPortionAttributableToNoncontrollingInterest` is an
  explicit inclusive permanent-equity alternative; temporary equity is still required.
- Operating interest income can come from `InterestAndDividendIncomeOperating −
  DividendIncomeOperating`. Net operating interest can also come from
  `InterestRevenueExpenseNet − InterestIncomeExpenseNonoperatingNet`. These support
  the existing operating-interest-expense identity without treating dividends as interest.
- Total interest expense can come from `InterestIncomeOperatingAndNonoperating −
  InterestRevenueExpenseNet`, or by subtracting both operating and nonoperating net
  interest from that same total income. A directly reported operating expense can
  instead be combined with nonoperating expense derived as total interest income
  minus operating interest income minus nonoperating net interest.
- `InterestCostsIncurred − InterestCostsCapitalized` is another complete interest
  identity. `InterestCostsCapitalizedAdjustment` is an alternative capitalized input;
  its positive credit amount is subtracted. A missing capitalized amount is not zero.

**Operating-income qualification:** the official
[FASB statement calculation example](https://xbrl.fasb.org/us-gaap/2026/stm/us-gaap-stm-soi-cal-2026.xml)
contains `GrossProfit − OperatingExpenses + OtherOperatingIncomeExpenseNet +
GovernmentAssistanceOperatingIncome`. It therefore disproves the blanket claim
that the first two tags always suffice. This reference network illustrates a
permitted structure; it does not establish the actual calculation network of every
company. The simple fallbacks require established zero values for the two extra
income terms (reported directly or derived from complete compatible inputs). Nonzero or absent adjustments remain unsupported because this
pipeline does not determine whether they have already been included elsewhere.
This is a conservative implementation restriction, **not an SEC requirement to
report zero facts**, and not a complete solution for all permitted structures.

With those explicit zeros, the module tries `GrossProfit − OperatingExpenses`,
then `Revenues − CostsAndExpenses`. It can reconstruct gross profit as
`Revenues − CostOfRevenue`, or operating expenses as
`CostsAndExpenses − CostOfRevenue`, using complete inputs. These now live in separate intermediate-value modules, with direct retrieval
first and no recursion or comparison of competing fallback results.

**Reviewed exclusions:** customer-contract revenue alone need not be total revenue;
`CostOfGoodsAndServicesSold` explicitly excludes some financial-service and other
revenue-generating costs. Debt interest, lease interest and other selected borrowing
categories do not establish an exhaustive partition of total interest.
`InterestAndDebtExpense` includes debt-related costs beyond interest, cash interest
paid is not accrued expense, and `InvestmentIncomeInterest` does not establish all
nonoperating interest income. `InterestCostsIncurredCapitalized` includes construction
allowances, so it is not an unconditional substitute for pure capitalized interest.
Likewise, a pretax-income bridge needs the correct treatment of equity-method
income, interest/debt costs and other nonoperating items; it was not added merely
because a tag is named `NonoperatingIncomeExpense`. Detailed asset/liability
components and equity share-class balances are not presumed complete or disjoint.
These exclusions are scope limitations, not proof that the amounts can never be
recovered with additional filing-specific evidence.

The new total-interest-income concept and the operating/nonoperating expense
concepts first appear in the reviewed 2024 release. `InterestRevenueExpenseNet`
previously described a narrower investment/cash-interest scope; its 2024 definition
covers operating and nonoperating interest. The new formulas using that aggregate
also require a post-2023 income/expense concept, rather than treating the older
wording as equivalent. Asset/liability and equity wording changes are recorded in
the review JSON. No runtime standards download or taxonomy-version gate was added.

**Validation:** 24 constructed/integration tests pass, and 22 archived filings still
match their frozen baseline. The same 30-filing live sample preserved every
previously available ratio and recovered one previously missing coverage value:
Air Products FY2025. Its $615.8 million incurred interest minus $401.8 million
capitalized interest yields $214 million expense and coverage of approximately
−4.0981, using its reported operating loss. This also equals its separately
reported nonoperating interest expense; zero operating interest was not assumed.
For an independent check of the incurred/capitalized identity, ARE FY2025 supplies
$557.122 million incurred and $330.424 million capitalized, whose difference equals
its directly reported $226.698 million total interest expense. The new operating
income fallbacks recover none of the sampled missing numerators. All other sampled
missing ratios remain missing. Production CSVs and the database were not rewritten.

The definition audit and read-only sample results are retained as historical evidence;
the exploratory runner has been removed.

This is a bounded review of supported equations for the four current metrics,
not certification that every possible accounting derivation has been implemented.
Definitions do not enumerate every company's complete partition of amounts.
Remaining coverage gaps must not be hidden by calling missing inputs zero.

### Further interest-coverage candidate research

An additional screen examined 579 monetary duration concepts matching interest or
operating-income/cost terminology in the official 2026 definitions. This is a
historical keyword screen, not an exhaustive proof of every possible equation.
The selected candidate definitions were also compared across 2021–2026.

One further denominator candidate is:

```text
Total interest expense = before-interest continuing-operations subtotal
                      + total interest income − pretax continuing-operations income
```

The exact standard concepts are
`IncomeLossFromContinuingOperationsBeforeInterestExpenseInterestIncomeIncomeTaxesExtraordinaryItemsNoncontrollingInterestsNet`,
`InterestIncomeOperatingAndNonoperating`, and
`IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest`.
The first subtotal includes nonoperating and equity-method income: it is **not**
a replacement for the operating-income numerator. Its reviewed definition is
unchanged across 2021–2026; the total-interest-income concept first appears in 2024.

The later full-archive review found an additional restriction: the reference
income template builds this subtotal from operating income, nonoperating income
and equity-method income. It does not establish that all operating interest has
been removed from operating income. Therefore the displayed equation is still
an **unapproved candidate**, even if all three tags are present; matching
classification evidence would be required before using it for total interest.

Possible complete-input bridges to the pretax amount are continuing-operations
income including noncontrolling interests plus continuing-operations tax expense;
or consolidated `ProfitLoss` minus discontinued-operations income after tax,
plus that tax expense. Parent-only `NetIncomeLoss` additionally requires the
noncontrolling-interest income component. Missing discontinued operations or
noncontrolling interests are not assumed zero.

**Real evidence:** a purposive sample of 26 latest saved S&P 500 company filings
covered banks, brokers, utilities and previously problematic nonfinancial firms.
None supplied the required before-interest subtotal, so this candidate recovered
**zero additional interest-expense amounts or ratios**. Ten constructed checks
verified the arithmetic and missing-input handling; they do not validate the
identity against a real filing. The candidate remains research and was not added
to production. Production CSV hashes were unchanged and no database was accessed.

Other screened concepts do not establish an unconditional new fallback:

- `InterestExpenseBorrowings`, `InterestExpenseDeposits`,
  `InterestExpenseInterestBearingLiability`, `InterestExpenseDebt` and lease
  interest describe components. Their names do not establish a complete,
  nonoverlapping partition of total expense.
- `InterestAndDebtExpense` includes debt-related costs, so it is not a pure
  interest-expense substitute.
- `InvestmentIncomeInterest` concerns securities interest before certain
  amortization/accretion adjustments; it is not all nonoperating interest income.
- `InterestIncomeExpenseAfterProvisionForLoanLoss` includes loss provisions.
  Adding a provision back needs matching scope and does not by itself establish
  total operating and nonoperating interest expense.
- A cash-interest-paid bridge needs more than changes in interest payable:
  noncash adjustments and capitalized amounts can matter.

These conclusions use the [official FASB 2026 definitions](https://xbrl.fasb.org/us-gaap/2026/elts/us-gaap-doc-2026.xml)
and [technical schema](https://xbrl.fasb.org/us-gaap/2026/elts/us-gaap-2026.xsd),
within the [SEC accepted-taxonomy framework](https://www.sec.gov/data-research/structured-data/taxonomies-schemas/standard-taxonomies).
The equations are accounting interpretations of the definitions, not SEC mandates
to disclose those inputs. No new unconditional operating-income derivation was
established by this screen. Unexamined structures remain unverified coverage.

The consolidated evidence retains the selected definition histories, exact
accessions, filing URLs and observed inputs. The broad keyword inventory and its
exploratory runner were removed; they are not needed by the current tests.

The `get_assets_before_equity` and `get_liabilities_before_equity` helpers exclude
the final equity identity. The final formulas use those helpers so they cannot
call each other indefinitely. There is no recursive fallback framework.

Historical taxonomy definitions are not all identical. In the reviewed releases,
`InterestExpenseOperating` and `InterestExpenseNonoperating` first appear in 2024;
`InterestExpense` also changes wording. The pipeline does not enforce a taxonomy
version gate or prove cross-year semantic equivalence. Earlier version comparisons
remain in the archived review linked below.

</details>

<details>
<summary>Extraction performance</summary>

<a id="extraction-performance"></a>

Extraction is the main runtime cost, so `ThreadPoolExecutor` processes three
companies concurrently while each company's filings remain sequential. Results
retain company-CSV order and are written once after all workers succeed.
EdgarTools shares one request limiter across the threads (9 requests/second by
default), below the [SEC limit](https://www.sec.gov/about/developer-resources).

In user-reported runs, extraction took **2,023 seconds with one worker** and
**1,671 seconds with three**—about **17% faster**. Two workers were close at
1,689 seconds; four, five, six and ten were slower. Three is the chosen practical
setting, not a proven optimum. These were individual runs with potentially
different cache, network and machine conditions; the original roughly 2,200-second
sequential run is not a controlled baseline. Parsing still takes time even when
downloads are cached, so more workers do not guarantee a shorter run.

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
