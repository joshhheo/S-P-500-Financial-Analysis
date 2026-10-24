# S&P 500 Financial Analysis

Company-level analysis of current S&P 500 constituents using annual SEC 10-K
filings, with sector comparisons providing context for financial condition,
performance, and business trajectory.

The project collects up to five annual reporting periods for each current
constituent and calculates liabilities-to-assets and interest coverage ratios.
Results are available as CSVs and in PostgreSQL for company-level and sector
queries. My Tableau charts compare each company's latest two comparable annual
periods within its sector.

- [Analytical Framework](#analytical-framework)
- [Metrics](#metrics)
- [Data Analysis](#data-analysis)
- [Data Rules and Assumptions](#data-rules-and-assumptions)
- [Accounting Fallbacks](#accounting-fallbacks)
- [Limitations](#limitations)
- [Tests and Evidence](#tests-and-evidence)
- [How It Works](#how-it-works)
- [How It's Built](#how-its-built)
- [Setup and Execution](#setup-and-execution)
- [Roadmap](#roadmap)

## Analytical Framework

The long-term company overview addresses four questions:

1. **Likelihood of failure:** how vulnerable is a company to financial distress or default?
2. **Loss or recovery conditional on failure:** how protected is a stakeholder if failure occurs?
3. **Likelihood of growth or contraction:** which direction might the business move?
4. **Magnitude of growth or contraction:** how large might the upside or downside be?

Different measures help investigate different questions. Liabilities/assets,
interest coverage, and planned liquidity measures help assess financial
vulnerability. Revenue growth and profit margins help show whether a business is
expanding and how profitably it operates. Free cash flow shows how much cash
remains after capital expenditures. Growth, profitability, liquidity, and cash-flow
measures are planned additions, not current outputs.

These measures provide evidence, not definite answers. A few ratios cannot tell
us whether a company will fail, how much it will grow, or what stakeholders would
recover if it failed. Those judgments also require business context and assumptions
about the future. For example, assets reported on a balance sheet may sell for
different amounts, and recovery depends on which claims get paid first.

## Metrics

| Output | Formula |
| --- | --- |
| `liabilities_to_assets_ratio` | Total liabilities / total assets |
| `interest_coverage_ratio` | Annual operating income / annual total interest expense |

## Data Analysis

**Data snapshot: October 21, 2026.** Open the [interactive Tableau workbook][tableau]
and use its sheet tabs to switch between metrics and zoom levels. Each image below
also links to the workbook.

My Tableau charts are separate from the pipeline. I run the
[preparation queries](src/database/sql/tableau_prep/) against the database, export
the results as CSVs, and import them into Tableau. The exact steps depend on the
database and Tableau version.

### Reading the Charts

Each sector has two box plots: Previous and Latest. These refer to each company's
consecutive annual periods, so the actual fiscal dates can differ across companies.
The snapshot date describes when the data was collected, not the fiscal year being
measured. Each dot represents one ticker in one annual period.

The box contains the middle 50% of observations, with the median marked inside.
The interquartile range (IQR) is the distance between the lower and upper quartiles.
Whiskers extend to the most extreme observed values within 1.5 × IQR below the
lower quartile or above the upper quartile. Points beyond the whiskers are outliers.

Point colors show distance from that sector's median for the same comparison
period: green is closer and red is farther away. Color does not indicate financial
health.
The score is the absolute distance from the median divided by the IQR, calculated
separately for each sector and comparison period. A score of 1 means one IQR away;
a zero IQR leaves the score unavailable. The color ranges are 0–4 for
liabilities/assets and 0–5 for interest coverage; higher scores share the strongest
red. Distance alone does not determine whether a point is an outlier.

Zoomed charts use a narrower axis range. Points outside that range still contribute
to the box plots and statistics. An outlier is a point to investigate,
not proof of financial distress or an extraction error. Filtering companies can
change Tableau's statistics while the exported color scores stay fixed.

Hover in Tableau for company details, the ratio, and fiscal dates.

### Annual Percentage Change

The tooltip on each Latest point also shows the percentage change in that company's
ratio from its Previous annual period:

```text
Annual percentage change = 100 × (latest − previous) / previous
```

For example, a ratio rising from 0.60 to 0.66 has increased by 10%, equivalent to
6 percentage points. This compares the company's own ratios, not sector medians.

Change is shown only when the previous ratio is positive. A zero or negative
previous ratio leaves change blank, but the company remains in both box plots.
Previous points do not show percentage change.

### Coverage Definitions

“Latest available” counts tickers with a ratio in their latest stored period.
“Matched tickers” counts those with usable ratios in both adjacent annual periods;
only matched tickers appear in the charts. Percentages use all current tickers in
the relevant sector or overall sample, including those with no financial records.
See the [annual-matching rules](#annual-matching-for-the-charts) for eligibility.

### Liabilities-to-Assets Distribution

**Zoomed View (0–1.5)**

[![Previous and Latest liabilities-to-assets distributions by sector, zoomed to 0–1.5](<docs/images/Liabilties-to-Assets-Distribution (0-1.5).png>)][tableau]

**Full-Range View**

[![Previous and Latest liabilities-to-assets distributions by sector, full range](<docs/images/Liabilties-to-Assets-Distribution.png>)][tableau]

**Coverage:** 401 of 503 tickers have a latest ratio (79.72%); 102 are missing
(20.28%). The paired charts include 396 tickers (78.73% of all current tickers),
with two observations each: 792 rows. The remaining 107 tickers are excluded.
These counts use the October 21, 2026 repository CSV snapshot. The published
Tableau extract has not been independently checked against them.
[Source record](scratch/research/liabilities_to_assets_coverage.json).

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

### Interest Coverage Distribution

**Zoomed View (−10–65×)**

[![Previous and Latest interest-coverage distributions by sector, zoomed to −10–65 times](<docs/images/Interest Coverage Ratio Distribution (-10-65).png>)][tableau]

**Full-Range View**

[![Previous and Latest interest-coverage distributions by sector, full range](<docs/images/Interest Coverage Ratio Distribution.png>)][tableau]

**Coverage:** 96 of 503 tickers have a latest ratio (19.09%); 407 are missing
(80.91%). The paired charts include 94 tickers (18.69% of all current tickers),
with two observations each: 188 rows. The remaining 409 tickers are excluded.
These counts use the October 21, 2026 repository CSV snapshot. The published
Tableau extract has not been independently checked against them.
[Source record](scratch/research/interest_coverage_counts.json).

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

Interest coverage is expressed as a multiple (×). Some sectors have only two or
three usable observations, which is too few to describe the sector as a whole.
Always read the charts alongside their coverage counts.

[tableau]: https://public.tableau.com/views/SP500FinancialAnalysisOctober212026Data/Liabilties-to-Assets-Distribution?:language=en-US&:sid=&:redirect=auth&:display_count=n&:origin=viz_share_link

## Data Rules and Assumptions

These rules explain which financial facts the code accepts and how it handles
calculations, missing values, and errors.

### Company Coverage

The project retrieves data for current S&P 500 constituents, including their
earlier reporting periods. It does not reconstruct past index membership. The
[S&P U.S. Indices Methodology](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-indices.pdf)
explains index eligibility and domestic reporting criteria.

Separate share classes count as separate tickers.

### Company Identifiers

A CIK is the SEC identifier used to select a company's filing. The code does not
separately require every fact's internal company identifier to equal that CIK.
The [SEC XBRL Guide §6.2.7](https://www.sec.gov/files/edgar/xbrl-guide.pdf) allows
one co-registrant's CIK to represent the consolidated entity in a filing covering
multiple registrants.

### Fact Selection

- **Tag names:** the code searches for exact standard tag names, such as
  `us-gaap:InterestExpense`. It does not interpret company-specific custom tags
  or substitute tags with similar names.
- **Taxonomy validation:** the code relies on Edgar's parsing. Finding an exact
  tag name does not independently verify the filing's taxonomy setup or whether
  the amount was tagged correctly. The [SEC accepted-taxonomy list](https://www.sec.gov/data-research/structured-data/taxonomies-schemas/standard-taxonomies)
  identifies supported taxonomies, and the [SEC interactive-data FAQs](https://www.sec.gov/data-research/structured-data/office-structured-disclosure-staff-observations-guidance-trends/staff-interpretations-faqs-related-interactive-data-disclosure)
  explain reporting and tagging guidance.
- **Company-wide amounts:** the code selects non-dimensioned facts: values without
  an extra category such as a business segment or geographic region. This is the
  project's policy for selecting company-wide amounts from a filing.
- **Duplicate facts:** after Edgar's dataframe handling and the filters for
  reporting dates and company-wide amounts, the code uses the first nonmissing
  matching value. It assumes duplicate facts are consistent within accepted
  rounding differences. It does not rank competing facts by reported precision
  or reconcile conflicting values.

### Reporting Dates

A filing can contain several years of figures. The code matches dates so that
comparative periods are not mixed together:

- **Assets and liabilities:** match the requested balance-sheet date.
- **Operating income and interest expense:** match both the start and end of the
  requested reporting period.

### Annual Start Date

The code uses the filing's document metadata to identify the annual start:

1. `DocumentType` must identify a `10-K`.
2. `DocumentFiscalPeriodFocus` must identify a full fiscal year (`FY`).
3. `DocumentPeriodEndDate` must match the requested period end.

The matching facts must share exactly one possible start date. If they do not,
the annual start is unavailable. The code does not identify an annual period
simply by checking whether it lasts 350–380 days.

### Annual Matching for the Charts

For a match, the previous period must end the day before the latest starts, and
both periods must last 364–371 days. This accepts calendar years and 52/53-week
fiscal years. Both annual values for the metric must be available. Gaps, missing
dates, shorter transition periods, or a missing ratio exclude the ticker from
both plots. Each matched ticker contributes two rows, one per period.

Previous and Latest use the same tickers within each metric, but the two metrics
can have different samples. A missing latest ratio is not replaced with an older
value.

### Currency

The project assumes USD for the selected company-wide amounts.
[Regulation S-X 3-20(a)(2)](https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol3/pdf/CFR-2025-title17-vol3-sec210-3-20.pdf)
generally requires issuers that are not foreign private issuers to report in
U.S. dollars. [SEC Financial Reporting Manual §6640](https://www.sec.gov/about/divisions-offices/division-corporation-finance/financial-reporting-manual/frm-topic-6)
describes limited exceptions.

The code does not check units or convert currencies, so it does not detect or
support those exceptions.

### Calculation Rules

- **Fallback order:** use a reported amount first, then try the accounting
  identities below. The first successful result is retained, including zero.
  Alternative results are not reconciled.
- **Required inputs:** every component used by a formula must be available. This
  includes noncontrolling interest and temporary equity where a formula uses them.
  [Regulation S-X §4-02](https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol3/pdf/CFR-2025-title17-vol3-sec210-4-04.pdf)
  permits immaterial amounts to be combined, so an absent tag does not establish zero.
- **Missing inputs:** a ratio cannot be calculated when a required input is missing;
  the result is `None`.
- **Zero denominators:** a ratio with a zero denominator returns `None`.
- **Zero numerators:** zero is a valid numerator and is not automatically rejected.
- **Negative amounts:** negative reported values are not automatically rejected.

### Missing Data

- **Storage:** missing values remain blank in CSVs and become SQL `NULL`, never
  zero. The loader uses pandas' inferred numeric types and converts missing cells
  to Python `None`.
- **Meaning:** a missing result does not explain whether the amount was undisclosed
  or the filing used an unsupported structure.

### Numeric Precision

Reported values are converted to Python `float`, and calculations use ordinary
floating-point arithmetic. The project does not use Decimal arithmetic to preserve
exact decimal values.

### Execution Errors

Unavailable selected data returns `None`. Unexpected parser, network, or malformed
input errors can still stop execution; they are not all treated as missing data.

## Accounting Fallbacks

A fallback calculates an amount from other reported values when the preferred
tag is unavailable. For example, total liabilities can be calculated by adding
current and noncurrent liabilities, but only when both values are present.

The lists below show the attempts in order after the direct concept is unavailable.
Exact tag names are in the retrieval modules.
Their accounting meanings were reviewed against the
[FASB US GAAP 2026 definitions](https://xbrl.fasb.org/us-gaap/2026/elts/us-gaap-doc-2026.xml)
and [technical schema](https://xbrl.fasb.org/us-gaap/2026/elts/us-gaap-2026.xsd).
That research is done before runtime; the code does not download taxonomy rules.
The formulas are project interpretations of compatible accounting components,
not substitutions mandated by the SEC.

### Assets

1. Current assets + noncurrent assets.
2. Reported liabilities-and-equity total.
3. Liabilities + net assets.
4. Liabilities + inclusive permanent equity + temporary equity.

### Liabilities

1. Current liabilities + noncurrent liabilities.
2. Assets − net assets.
3. Assets − inclusive permanent equity − temporary equity.

### Inclusive Permanent Equity

1. Inclusive partners’ capital.
2. Inclusive LLC members’ equity.
3. Parent equity + noncontrolling interest.
4. Derived partners’ capital.
5. Equity before treasury stock − treasury stock.
6. Derived LLC members’ equity.

### Inclusive Temporary Equity

Parent temporary equity + redeemable noncontrolling equity.

### Total Interest Expense

Every term in the chosen formula must be available.

1. Operating interest expense + nonoperating interest expense.
2. Total interest income − total net interest.
3. Incurred interest − capitalized interest.
4. Total interest income − operating net interest − nonoperating net interest.
5. Operating interest expense + derived nonoperating interest expense.

### Operating Income

All attempts below are subject to the [operating-income restriction](#operating-income-restriction).

1. Gross profit − operating expenses.
2. Revenues − costs and expenses.
3. The same identities with gross profit or operating expenses reconstructed
   using cost of revenue.

### Equity Definitions

Inclusive equity includes noncontrolling interests. Derived partners’
capital and LLC members’ equity combine the parent amount with the corresponding
noncontrolling-interest amount. Permanent equity and temporary equity are retrieved
separately; one is not assumed to include the other.

### Operating-Income Restriction

The operating-income formulas have an additional restriction: other operating
income/expense and operating government-assistance income must both be established
as zero, either directly or from complete inputs. If either is missing or nonzero,
these fallbacks are not used. This is a conservative project rule, not an SEC
requirement to report zero amounts explicitly.

[Research evidence](scratch/research/research_evidence.json) records the reviewed
definitions, component boundaries, and rejected alternatives.

## Limitations

- **Ticker changes can split company history.** The database uses tickers as keys
  and does not automatically connect an old ticker to a new one. Later loads can
  leave records under both. CIKs in `companies` help identify the relationship.
- **Missing data is not necessarily unobtainable.** The code does not support every
  valid filing structure or possible accounting derivation. The SG&A expense,
  regulated/unregulated revenue, and LLC equity fallbacks have constructed tests,
  but their recovery of missing S&P 500 values has not been demonstrated by the samples.
- **Validation is incomplete.** Tests do not cover every issuer, period, historical
  taxonomy change, or deployed PostgreSQL behavior.
- **Some cases are outside scope.** These include interpreting custom tags,
  malformed or incorrectly bound data, non-USD reporting exceptions, amended
  filings, and retrieval through filing calculation relationships.
- **Some inputs cannot be uniquely recovered.** Filings do not need to disclose every
  component required by a formula. A net amount may not reveal its gross components,
  and rounded amounts may not determine an exact underlying value.

## Tests and Evidence

### AI Assistance

I used AI assistance for parts of development and test
generation. For some checks, I rely entirely on AI-generated tests without
independent manual verification. Tests can share assumptions or mistakes with
the implementation, so passing results are not an independent accounting audit.

### What the Checks Cover

- **41 offline tests** check retrieval, accounting fallbacks, extraction order,
  failure handling, and loading missing values into the database. Seven of these
  test the Tableau queries: latest-period selection, current membership, annual
  matching, missing data and gaps, nonpositive baselines, separate period statistics,
  and zero IQR.
- **22 archived filings from six companies** are compared with saved expected
  results for four financial inputs and both ratios, including missing values.
  This checks whether behavior has changed; it does not prove every expected result
  is independently correct.
- **The SQL tests use SQLite substitutes** for PostgreSQL percentiles and date
  subtraction. They check the comparison rules, not live PostgreSQL execution
  or numerical precision.

### Running the Checks

Run both checks offline. Neither replaces production CSVs nor writes the database:

```sh
PYTHONPATH=src .venv/bin/python -B -m unittest discover -s scratch/tests -p 'test_*.py'
.venv/bin/python -B scratch/tests/verify_archived_filings.py
```

### Retained Evidence

The [tests folder](scratch/tests/) includes the saved filing ZIP and instance
manifest needed for archived verification. The [research folder](scratch/research/)
contains coverage records, [accounting evidence](scratch/research/research_evidence.json),
and a [source manifest](scratch/research/source_manifest.json). Some historical
scripts and downloads were removed, so not all research can be rerun from these
files. I have not independently reviewed all retained research.

## How It Works

### Pipeline

1. Retrieve current S&P 500 tickers, company names, sectors, and CIKs from Wikipedia.
2. Use each CIK to retrieve up to five distinct original 10-K reporting periods.
   Amended filings are excluded.
3. Use EdgarTools to parse the filings, then select financial facts using the
   reporting dates and accounting rules described above.
4. Calculate ratios, write the CSVs, load PostgreSQL, and refresh the sector views.

### Concurrent Extraction

Three companies are processed at the same time using `ThreadPoolExecutor`.
Filings for an individual company are processed sequentially.

<a id="extraction-performance"></a>

I chose three workers based on my extraction runs: one took 2,023 seconds, three
took 1,671 seconds (about 17% faster), and two took 1,689 seconds. Higher worker
counts were slower. These were individual runs with different possible cache
and network conditions, not a controlled benchmark.

EdgarTools shares one 9-request-per-second limiter across the threads, below the
[SEC request limit](https://www.sec.gov/about/developer-resources).

### Output Order

Results retain the company CSV's order and are written after all workers finish
successfully.

### Failure Handling

There is no checkpoint or resume mechanism if extraction fails.

### Storage and Outputs

| CSV | Database key and contents |
| --- | --- |
| `data/company_status.csv` | Loads ticker, CIK, company name, and sector into `companies`, keyed by ticker. |
| `data/financial_ratios.csv` | `financials`, keyed by ticker and fiscal-period end: reporting dates and both ratios. |

| Output | Purpose |
| --- | --- |
| `companies` | Company identity, current sector and constituent status. |
| `financials` | Stored financial ratios and fiscal periods for each ticker. |
| `sector_leverage_rankings` | Latest liabilities/assets ratios and within-sector ranks for current constituents. |
| `sector_interest_coverage_rankings` | Latest interest-coverage ratios and within-sector ranks for current constituents. |

The company loader marks tickers in the current CSV as current constituents and
marks other stored tickers as no longer current.

CIK is stored only in `companies`.

The sector views join company details to financial history by ticker. They select
each current ticker's latest stored period and rank its available ratio within
the sector. A missing latest ratio stays missing; an older value is not substituted.

The tables, views, and CSVs are reusable outputs. My Tableau preparation queries
and chart publishing are separate research steps and are not run by `main`.

## How It's Built

### Tools and Rationale

| Tool or format | Role and rationale |
| --- | --- |
| Python | Organizes collection and calculations into small, testable modules. Formulas and fallback order are written explicitly so they can be inspected. |
| EdgarTools | Retrieves filings and parses XBRL, the structured financial facts in SEC filings. This avoids writing a custom parser while leaving concept selection and calculations in this project. |
| PostgreSQL | Stores company details and reporting history in related tables. SQL supports period matching, consistent company samples, sector views, and queries independent of Tableau. |
| Neon | Hosts PostgreSQL so the database does not depend on running a local server or keeping the extraction process open. |
| Tableau Public | Publishes interactive sector comparisons with company tooltips. Importing dated CSVs keeps chart updates separate from extraction. |
| CSV | Makes the results easy to inspect and use in other tools without access to the database or Tableau. |

Pandas handles tabular data, SQLAlchemy manages database connections and SQL
execution, and psycopg2 connects to PostgreSQL. Versions are pinned in
[requirements.txt](requirements.txt).

### Code Structure

| Location | Purpose |
| --- | --- |
| [src/main.py](src/main.py) | Run the pipeline stages. |
| [src/wiki_pull.py](src/wiki_pull.py) | Retrieve the constituent list. |
| [src/table_data/](src/table_data/) | Build company and ratio CSVs. |
| [src/value_retrieval/get_value.py](src/value_retrieval/get_value.py) | Identify the annual start from document metadata and retrieve exact concepts for the requested dates. |
| [src/value_retrieval/](src/value_retrieval/) | Individual asset, liability, equity, interest and operating-income formulas. |
| [src/calculations/](src/calculations/) | Divide independently retrieved metrics. |
| [src/database/](src/database/) | Create tables, load CSVs and refresh views. |
| [scratch/tests/](scratch/tests/) | Repeatable behavior checks and archived filing fixtures. |
| [scratch/research/](scratch/research/) | Historical investigations and source evidence behind accounting decisions. |

### Design Decisions

- **Module responsibilities:** each main financial amount has its own retrieval
  module. Supporting calculations have separate modules when they have their own
  fallbacks, and shared calculations have one implementation.
- **Preventing circular calls:** assets and liabilities use helpers that exclude
  the final equity identity so the two retrieval functions cannot call each other
  indefinitely.

- **Equity scope:** parent-only equity is not automatically treated as total equity
  including noncontrolling interests.
- **Interest-expense scope:** cash interest paid is not substituted for accrued
  interest expense, and a net interest amount alone does not establish total expense.
  Unsupported equations stay out of production.
- **Research definitions before runtime.** Definitions were reviewed against 2026
  and selected 2021–2026 releases. Some interest concepts first appear in 2024.
  The code does not check taxonomy versions at runtime or guarantee equivalent
  meanings across every year.
- **Defer calculation-linkbase retrieval.** A filing's calculation linkbase records
  relationships between reported facts. Reading it could recover some missing
  amounts, but adds parsing and relationship-handling code. I deferred that work
  to keep the implementation small. An earlier comparison lost liabilities/assets
  for ten AMD and Walmart filings when linkbase retrieval was disabled, so this
  choice has a known coverage cost.

The [research evidence](scratch/research/research_evidence.json) retains definition
histories, candidate equations, filing observations, and rejected substitutions.

### Why Caching Does Not Eliminate Extraction Time

EdgarTools 5.58.0 uses a local HTTP response cache. The 30-second setting is a
freshness period for submission metadata and company facts, not a server-side
expiry applied to every call. Archived filing responses are cached indefinitely
under the default rules; index responses use a 30-minute freshness period.
[Cache rules](https://github.com/dgunning/edgartools/blob/v5.58.0/edgar/httpclient.py).

Caching helps when the same URL is requested again. A first extraction still needs
to download uncached filings, and metadata may require a network freshness check
after 30 seconds. Cached filing responses can reduce later downloads, but a new
pipeline run still parses filings, selects facts, and calculates ratios. The
pipeline does not persist those parsed results or resume completed companies.
Caching therefore does not remove the full extraction cost.

### Why I Do Not Use EdgarTools' Total-Value Getters

I use EdgarTools to retrieve and parse filings, but calculate financial totals
through this project's exact-concept searches and reviewed accounting fallbacks.
Convenience methods such as `get_total_assets()` can use broader label matching
than the metric requires.

In the pinned 5.58.0 implementation, `get_total_assets()` includes the pattern
`Assets$`, which also matches a label ending in “Current Assets.” If no earlier
pattern finds a usable total, the method can therefore return current assets as
total assets. An isolated check with only “Current Assets = 100” reproduced that
result. Current assets alone are not total assets.
[Getter implementation](https://github.com/dgunning/edgartools/blob/v5.58.0/edgar/financials.py).

This is a specific reason to keep metric selection explicit, not a claim that
every convenience method is incorrect. My retrieval requires the exact reported
total or a complete supported identity, such as current assets plus noncurrent
assets. Otherwise, the amount remains missing.

## Setup and Execution

Run these commands from the repository root. The development environment uses
Python 3.13; the dependency file pins the libraries, including EdgarTools 5.58.0.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Create a `.env` file with your SEC contact identity and database connection string.
Do not commit this file:

```dotenv
SEC_user_agent="Your name your-email@example.com"
db_connection_string="postgresql+psycopg2://USER:PASSWORD@HOST/DATABASE?sslmode=require"
```

Run the full pipeline (**network access, CSV replacement and database writes**):

```sh
.venv/bin/python src/main.py
```

To run only a collection stage, use one of these commands. Both access the network
and replace their corresponding CSV. They do not load the database or refresh views.

```sh
# Refresh data/company_status.csv
PYTHONPATH=src .venv/bin/python -m table_data.company_status

# Read that company list and write data/financial_ratios.csv
PYTHONPATH=src .venv/bin/python -m table_data.generate_ratios
```

`PYTHONPATH=src` lets Python find the project modules. `.venv/bin/python` uses the
project's virtual environment, and `-m` runs the named module.

Schema setup creates tables that do not exist; the view-refresh stage creates
the sector views. It does not update an older table structure or delete existing
tables automatically. When the structure changes, I manually recreate the affected
tables and dependent views in Neon, then rerun the pipeline to load them.

## Roadmap

The next analysis step is to check the published Tableau extracts against the
coverage records, then interpret the paired box plots. Automatic chart updates
are not planned as part of the tool.

### Improving Interest-Coverage Data

I plan to verify existing interest-coverage values more thoroughly and investigate
why so many companies have missing results. The work will focus on:

- **Checking reported inputs:** compare operating income and total interest expense
  with the original financial statements and notes. Review both ordinary and
  extreme ratios, confirming the reporting period, units, and accounting scope.
- **Understanding missing results:** identify whether operating income, interest
  expense, or a component needed for a fallback is unavailable. Distinguish missing
  disclosures from values the current retrieval rules do not support.
- **Reviewing additional retrieval methods:** investigate standard concepts,
  complete accounting identities, and filing calculation relationships that could
  recover missing inputs. Add methods only when their definitions and filing
  evidence support the intended metric; do not assume missing components are zero.
- **Verifying changes independently:** manually check selected filing examples and
  compare results before and after retrieval changes. Use those checked examples
  to support tests, rather than relying only on AI-generated expectations.
- **Reporting progress:** update the coverage counts and explain remaining gaps
  so readers can see which companies and sectors the analysis represents.

### Planned Measures and Features

| Measure or feature | Planned definition and scope |
| --- | --- |
| Current ratio | Current assets / current liabilities. |
| Revenue growth | Change in annual revenue relative to the preceding comparable annual period. Establish the revenue concepts, comparison basis and zero/missing prior-period treatment before implementation. |
| Operating margin | Annual operating income / annual revenue, using the same reporting period and scope. |
| Free cash flow (FCF) | Operating cash flow minus a clearly defined capital-expenditure measure. Establish which expenditures are included and normalize the cash-outflow sign before implementing the subtraction. |
| FCF margin | Potential extension: defined free cash flow / revenue for the same period. |
| Calculation-linkbase retrieval | Revisit recovery of missing values if the coverage benefit warrants the additional code; preserve the applicable relationship semantics. |

These additions still need reviewed tag definitions, component boundaries, and
fallback rules. Revenue retrieval is needed for revenue growth, operating margin,
and FCF margin. The existing liabilities/assets metric will continue to use total
liabilities.

### Further Analysis

| Analysis | Question and scope |
| --- | --- |
| Annual company changes | Which companies' liabilities/assets ratios changed most? Calculate percentage-point differences between comparable consecutive annual periods; preserve missing observations and flag gaps. |
| Matched-company sector trends | Are changes widespread within sectors? Compare the same companies across periods, reporting median company change and the share with an increase. |
| Company position within its sector | How does each company's latest ratio compare with its sector median and percentile? Keep the reporting period visible. |
| Interest-coverage histories | How does available coverage change within each company? Preserve gaps and avoid inferring the cause of negative ratios without the underlying amounts. |
| Correlation exploration | Potential future analysis of liabilities/assets versus interest coverage within sectors, using company-level scatter plots and correlation summaries. Inspect the patterns and validate inputs before deciding whether Pearson, Spearman or another approach is appropriate. |
