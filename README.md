# S&P 500 financial risk pipeline

Retrieves financial values from SEC 10-K filings, calculates two risk ratios,
and stores results in CSVs and PostgreSQL sector-ranking views.

The code favors direct concept searches, explicit accounting formulas and small
modules with separate purposes. Current behavior and policies below reflect the
October 15, 2026 revision.

## Analytical framework

The project is organized around four questions:

1. **Likelihood of failure:** how vulnerable is a company to financial distress or default?
2. **Loss or recovery conditional on failure:** how protected is a stakeholder if failure occurs?
3. **Likelihood of growth or contraction:** which direction might the business move?
4. **Magnitude of growth or contraction:** how large might the upside or downside be?

The measures below provide accounting inputs for investigating these questions.
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

## Metrics

| Output | Formula | Meaning |
| --- | --- | --- |
| `debt_to_assets_ratio` | Total liabilities / total assets | Uses **all liabilities**, not only interest-bearing debt. |
| `interest_coverage_ratio` | Annual operating income / annual total interest expense | Total interest expense includes operating and nonoperating interest expense; the numerator is operating income, not a separately reconstructed EBIT. |

A missing required value or zero denominator produces `None`. Zero numerators and
negative reported amounts are not automatically rejected.

## Pipeline flow

1. Read current S&P 500 constituents, CIKs and sectors from Wikipedia.
2. Use each CIK to retrieve up to five distinct original 10-K reporting periods.
3. Let Edgar parse each filing; search its facts using explicit concept names.
4. Retrieve each metric, trying its accounting fallbacks only when needed.
5. Calculate ratios, save CSVs, load the database and refresh sector views.

Historical results cover **current constituents**, not historical index membership.
Amended filings are excluded. The full run performs all five steps.

| Location | Purpose |
| --- | --- |
| [src/main.py](src/main.py) | Run the pipeline stages. |
| [src/wiki_pull.py](src/wiki_pull.py) | Retrieve the constituent list. |
| [src/table_data/](src/table_data/) | Build company and ratio CSVs. |
| [src/value_retrieval/get_value.py](src/value_retrieval/get_value.py) | Search one exact concept and match dimensions and dates. |
| [src/value_retrieval/get_reporting_period.py](src/value_retrieval/get_reporting_period.py) | Establish the annual start from reported DEI facts. |
| [src/value_retrieval/](src/value_retrieval/) | Individual asset, liability, equity, interest and operating-income formulas. |
| [src/calculations/](src/calculations/) | Divide independently retrieved metrics. |
| [src/database/](src/database/) | Create tables, load CSVs and refresh views. |
| [scratch/unchecked_tests/](scratch/unchecked_tests/) | Tests, archived filings and review evidence. |

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
- Require every input to a formula. An absent component does not automatically
  mean zero; this includes noncontrolling interest and temporary equity.
- Trust compliant duplicate facts and accepted rounding differences. Use Edgar's
  dataframe duplicate handling, then the first matching row. No independent
  precision ranking or conflicting-value reconciliation is performed.
- Convert original numeric text to `Decimal` to avoid binary floating-point
  representation error. Arithmetic still has finite precision; ratios use 28
  significant digits with half-even rounding.

Annual starts come from the matching `DocumentType`, `DocumentFiscalPeriodFocus`
and `DocumentPeriodEndDate` contexts. Exactly one shared start must be found.
This avoids assuming that every annual reporting period is 350–380 days long.

These are retrieval policies under a defined scope, not a promise to validate
arbitrary filings. Missing or unusable selected data returns `None`; unexpected
parser, network or malformed-input errors are not all converted to `None`.

## Why the pipeline is built this way

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
is supporting evidence, not an exhaustive proof. [Recorded facts and contexts](scratch/unchecked_tests/implementation/foreign_currency_evidence.json)

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
[historical comparison](scratch/unchecked_tests/full_review/taxonomy_comparison.json)
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
We accepted Edgar's duplicate handling and first-row selection, rather than
preserving precision intervals and dependency graphs. That is an implementation
choice with accepted rounding differences, not an SEC mandate to select the first
row. The [SEC XBRL Guide](https://www.sec.gov/files/edgar/xbrl-guide.pdf) discusses
numeric duplicate consistency and accuracy; the project does not independently
revalidate those conditions.

Similarly, direct values take precedence and later fallback results are not
compared after one succeeds. A returned zero is a result, not a reason to continue.
`Decimal` remains as a small way to avoid introducing binary representation error;
it does not recover undisclosed precision. Detailed missing-reason objects and
provenance classes were removed in favor of values/`None` and available/missing
statuses, while filing identifiers remain in the output.

### Why calculation-linkbase support was deferred

We implemented and tested filed calculation relationships, then measured what
happens without them. Disabling the linkbase while keeping the same direct facts
and accounting fallbacks removed liabilities and debt-to-assets for AMD and Walmart
in five filings each. Other outputs did not change in the sample.
[Measured comparison](scratch/unchecked_tests/implementation/linkbase_dependency_results.json)

Simple candidate formulas reproduced all ten liabilities numerically. However,
missing equity categories prevented us from proving those candidates complete as
general accounting fallbacks. The test therefore demonstrated dependence on the
then-current implementation, not that the values were mathematically impossible
to derive another way. [Candidate identity comparison](scratch/unchecked_tests/implementation/liability_identity_comparison.json)

The owner chose simpler code and reduced coverage over calculation-network
parsing, priority/prohibition handling and traversal. Those features were removed,
including their supporting architecture. The affected values currently remain
missing. This is a known recoverable coverage gap and a future feature—not proof
that linkbases have negligible value or that `None` resolves the gap.

## Accounting fallbacks

Exact concept names are written in the respective metric modules. Definitions
were reviewed against the US GAAP 2026 baseline; standards research is done
beforehand, not downloaded at runtime.

| Metric | Order after its direct concept is unavailable |
| --- | --- |
| Assets | Current + noncurrent assets; liabilities-and-equity total; liabilities + inclusive permanent equity + temporary equity. |
| Liabilities | Current + noncurrent liabilities; assets − inclusive permanent equity − temporary equity. |
| Inclusive permanent equity | Parent equity + noncontrolling interest. |
| Inclusive temporary equity | Parent temporary equity + redeemable noncontrolling equity. |
| Total interest expense | Operating + nonoperating interest expense. If operating expense is missing, operating interest income − net operating interest income. |
| Operating income | No accounting fallback currently implemented. |

The `get_assets_before_equity` and `get_liabilities_before_equity` helpers exclude
the final equity identity. The final formulas use those helpers so they cannot
call each other indefinitely. There is no recursive fallback framework.

Historical taxonomy definitions are not all identical. In the reviewed releases,
`InterestExpenseOperating` and `InterestExpenseNonoperating` first appear in 2024;
`InterestExpense` also changes wording. The pipeline does not enforce a taxonomy
version gate or prove cross-year semantic equivalence. Earlier version comparisons
remain in the archived review linked below.

## Results and storage

- `data/company_status.csv`: current constituent identity and sector data.
- `data/financial_ratios.partial.csv`: checkpoint rewritten after each company.
  A new extraction starts fresh; this is not a resume mechanism.
- `data/financial_ratios.csv`: completed extraction, including CIK, accession,
  reporting dates, ratios and `available`/`missing` statuses.
- `companies` and `financials`: PostgreSQL tables. Financial rows are keyed by
  ticker and fiscal-period end. The loader preserves decimal strings and turns
  blank cells into SQL `NULL`; it refuses updates with a conflicting stored CIK.
- Sector views select the latest stored period for current constituents and rank
  only available ratios. They do not substitute an older available period when
  the latest value is missing. Legacy unverified values are excluded from ranking.

The existing `extraction_evidence` database column is retained for compatibility;
current loads leave it null. Missing statuses do not distinguish undisclosed
amounts, unsupported standard structures or custom-tag coverage gaps.

## Setup and execution

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

Run just constituent collection or ratio extraction **with network access and CSV writes**:

```sh
PYTHONPATH=src .venv/bin/python -m table_data.company_status
PYTHONPATH=src .venv/bin/python -m table_data.generate_ratios
```

## Offline verification

These are the active checks for the current architecture. They use constructed
cases, mocked integration and archived filings; they do not run live extraction
or write to the live database or production CSVs.

```sh
PYTHONPATH=src:scratch/unchecked_tests .venv/bin/python -B -m unittest discover -s scratch/unchecked_tests
.venv/bin/python -B scratch/unchecked_tests/implementation/verify_simple_retrieval.py
```

The consolidated suite passed **16 tests**: 14 retrieval/calculation checks and
two storage/checkpoint checks. Across
**22 archived filings from six companies**—Apple, AMD, Microsoft, Walmart,
Berkshire Hathaway and JPMorgan—all four metric slots and both ratios matched
the frozen linkbase-disabled baseline, including missing values.

Evidence:

- [Focused test log](scratch/unchecked_tests/implementation/current_tests.txt)
- [Archived-filing comparison log](scratch/unchecked_tests/implementation/archived_filings.txt)
- [Per-filing results](scratch/unchecked_tests/implementation/simple_retrieval_results.json)
- [Original filing manifest](scratch/unchecked_tests/implementation/instance_manifest.json)
- [Linkbase dependency experiment](scratch/unchecked_tests/implementation/linkbase_dependency_results.json)

Obsolete suites and repeated run outputs have been removed. The remaining tests
run through standard unittest discovery. The mocked filing-loop test verifies
wiring, not live transport. SQLite checks transaction and missing-value behavior;
it does not establish deployed PostgreSQL behavior or numeric precision.
Original filing and official-source documents are compressed, and distinct
research conclusions are retained alongside the active tests; see the
[archive guide](scratch/unchecked_tests/README.md). Historical comparisons are
evidence from earlier experiments, not current executable regression tests.
Passing a sample does not prove universal correctness or complete S&P 500 coverage.

## Upcoming features

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

The existing liabilities/assets measure retains **total liabilities** as its
numerator, despite the historical `debt_to_assets_ratio` name. Interest-bearing
debt must not silently replace it when extending the project.

Tableau visualizations are upcoming after the next SQL analysis work.

## Remaining limitations

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

## Official references and review history

- [SEC accepted standard taxonomies](https://www.sec.gov/data-research/structured-data/taxonomies-schemas/standard-taxonomies)
- [US GAAP 2026 definitions](https://xbrl.fasb.org/us-gaap/2026/elts/us-gaap-doc-2026.xml)
- [US GAAP 2026 schema](https://xbrl.fasb.org/us-gaap/2026/elts/us-gaap-2026.xsd)
- [SEC XBRL Guide](https://www.sec.gov/files/edgar/xbrl-guide.pdf)
- [SEC interactive-data interpretations and FAQs](https://www.sec.gov/data-research/structured-data/office-structured-disclosure-staff-observations-guidance-trends/staff-interpretations-faqs-related-interactive-data-disclosure)
- [S&P U.S. Indices Methodology](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-indices.pdf): index eligibility and domestic reporting criteria.
- [Regulation S-X 3-20(a)(2)](https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol3/pdf/CFR-2025-title17-vol3-sec210-3-20.pdf): general USD reporting requirement for non-foreign-private issuers.
- [SEC Financial Reporting Manual §6640](https://www.sec.gov/about/divisions-offices/division-corporation-finance/financial-reporting-manual/frm-topic-6): limited staff exceptions to USD reporting.
- [Regulation S-X §4-02](https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol3/pdf/CFR-2025-title17-vol3-sec210-4-04.pdf): immaterial amounts need not be separately presented; omission alone does not establish zero.
