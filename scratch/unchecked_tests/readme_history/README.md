# Historical README archive — October 15, 2026

This is a snapshot before documentation cleanup. It contains superseded policies,
implementation descriptions and test commands. Repository paths in the original
text are relative to the project root. Use the [current README](../../../README.md)
for current behavior.

---

# S&P 500 financial risk pipeline

> **Current implementation:** see [Simple Edgar-based retrieval](#simple-edgar-based-retrieval).
> Production logic has now been updated after the review; production CSVs and the
> live database remain unchanged. Earlier review sections below are historical.

A Python pipeline that extracts financial amounts from SEC 10-K filings, calculates
risk ratios, saves inspectable CSVs, and loads Neon PostgreSQL tables and sector
ranking views. The intended audience is equity investors and creditors.

### USD scope assumption — current policy (October 15, 2026)

At the user's request, retrieval no longer checks monetary units. USD is an
explicit assumption for the selected S&P 500 companies and consolidated main/
fallback concepts under ordinary domestic reporting requirements. The limited
non-USD reporting exceptions described in the external research remain outside
supported scope. They are not detected or rejected at runtime. No conversion or
unit compatibility validation is performed; a non-USD fact reaching retrieval
would be processed numerically. This supersedes earlier USD-filter descriptions.
Company/filing selection, exact concept matching, dimensions, requested dates,
missing inputs and accounting formulas are unchanged.

The active constructed tests no longer promise rejection of non-USD inputs. One
explicit out-of-scope case records the removed enforcement. The offline archived
comparison and logs for this change are `implementation/usd_assumption_tests.txt`
and `implementation/usd_assumption_real_log.txt` under `scratch/unchecked_tests`.

### Simple Edgar-based retrieval

Rebuilt October 15, 2026 around the earlier procedural architecture. This section
supersedes the historical source-adapter and recursive retrieval descriptions below.

The filing loop gets `filing.obj().financials.xb` through Edgar. `get_value.py`
performs an exact concept search, excludes dimensioned facts, accepts only USD,
and matches the requested instant or duration dates. It returns the original
numeric text converted to Decimal, or `None`. It does not choose metric fallbacks.
Each metric file explicitly retrieves its reviewed concepts and applies its own
accounting equations. Ratios only call the metric functions and divide.

The two `get_*_before_equity` helpers in assets/liabilities intentionally do not
call each other. The final equity identities use those helpers, preventing cycles
without a recursive dispatcher, a trail parameter or a registry. Equity components
are all required: absent NCI or temporary equity is not automatically zero.
Operating income remains direct-only; the unverified gross-profit-minus-operating-
expenses formula has not been restored. Linkbase-derived amounts remain outside
coverage, including the ten AMD/WMT liabilities previously documented as missing.

`get_reporting_period.py` intersects the starts associated with the matching
DocumentType, DocumentFiscalPeriodFocus and DocumentPeriodEndDate facts. Exactly
one annual start is required. This handles a shortened reported annual duration
without relying on Edgar's 350–380-day Annual label.

Removed `source.py`, Source/FilingInstance classes, manual XML hooks, copied fact
records, centralized concept lists, runtime namespace-year gating, recursive
fallback routing, and the 2200-digit arithmetic context. Metric formulas use normal
Decimal arithmetic; ratio rounding is unchanged. Retrieval totals 148 source lines
versus 393 immediately before this rebuild (including comments and blank lines).

**Explicit scope and implementation assumptions:**

- The selected filing is the intended company's compliant annual instance. No
  redundant context-CIK equality gate is applied. Non-dimensioned facts identify
  the default reporting scope; subsidiary-specific dimensional facts are excluded.
- Exact concept strings are in the metric functions, based on the previously
  reviewed definitions. Edgar's exact search matches concept spellings; it does
  not independently validate namespace bindings. Correct standard bindings are
  trusted under the user's compliant-structure assumption. The custom literal-
  prefix hook and taxonomy-year acceptance list are no longer enforced. This is
  not new research proving historical/future definition equivalence.
- USD is fixed supported coverage. The small unit filter resolves Edgar's parsed
  simple units by their currency name, assuming standard monetary units. Edgar's
  convenience `currency` field failed the constructed `iso:USD` prefix test, so
  that shortcut is not used. No custom XML unit parser or conversion is added.
- Edgar's dataframe duplicate handling is used, followed by first matching row
  selection. Consistent duplicates/rounding are trusted as previously agreed;
  this is not an independent conflict-reconciliation system.
- Missing required inputs remain missing. The code does not infer unavailable
  components from absence, nor interpret custom concepts.

**Current reproducible verification** (offline):

```sh
PYTHONPATH=src:scratch/unchecked_tests .venv/bin/python -m unittest test_simple_retrieval
.venv/bin/python scratch/unchecked_tests/implementation/verify_simple_retrieval.py
```

Seventeen constructed tests passed: source queries with alternate ISO prefixes,
USD/non-USD and nil selection, explicit formulas and zero precedence, incomplete
equity, dimension and period exclusions, short/ambiguous annual starts, denominator
zero, and a fully mocked filing-loop integration with no network or CSV writes.
Separately, 22 original archived filings match all four metric slots and both ratios
from the frozen pre-removal linkbase-disabled baseline. Evidence resides under
`scratch/unchecked_tests/implementation`: `simple_retrieval_tests.txt`,
`simple_retrieval_real_log.txt`, `simple_retrieval_results.json` and
`simple_retrieval_csv_check.json`. The real test uses Edgar's `XBRL.from_files` on
instance files; it does not run the live pipeline or exercise live downloading.
The mocked integration verifies the filing-object wiring, not live Edgar transport.
Older scratch suites targeting removed APIs remain historical and are not claimed
to pass. All production CSV hashes match; no live database access occurred.
Passing this sample is not proof of universal correctness or complete coverage.

### Current source boundary and retrieval entry (October 15, 2026)

USD financial facts are now selected once during source preparation. Unit IDs
are resolved using Edgar's parsed unit definitions, then non-USD financial facts
are excluded. Unitless DEI metadata remains available for annual-period selection.
`Source.units` and stored `unit_ref` fields are removed; the prepared records are
already USD-only. Code constructing Source directly must honor that same contract.
The duplicate retrieval entry `get_amount` was merged into `get_value`, which
retains direct-first accounting fallback order and the accounting cycle guard.
Company, period, dimensions, reviewed concepts, nil handling and required formula
inputs retain their previous selection behavior.

The existing USD-only verification commands below remain current. Fifteen focused
constructed tests passed, including source-boundary tests using actual XML rather
than altering unit fields after preparation. All 22 archived filings still match
the frozen linkbase-disabled baseline. Evidence is in
`scratch/unchecked_tests/implementation/source_filter_tests.txt`,
`source_filter_real_log.txt` and `source_filter_results.json`. No production CSVs
or live database were written. Historical scratch tests that construct older
Source layouts or call `get_amount` are superseded, not claimed to pass.

### Current policy: USD-only retrieval (October 15, 2026)

All main and fallback concepts now accept only facts whose resolved unit is USD.
Non-USD facts are ignored; a value becomes `None` unless an eligible USD direct
fact or complete USD accounting formula supplies it. This explicitly excludes
non-USD reporting exceptions from supported coverage; it does not label them
invalid filings. Company, period, dimension, concept and missing-input selection
remain unchanged. No currency conversion is performed.

Removed currency discovery, DEI reporting-currency selection, currency arguments
through retrieval and ratio functions, and iteration across candidate currencies.
`filing_ratio` now calls its ratio function once and preserves available/missing
status. Unit references remain solely to enforce the USD filter.

Current offline verification commands:

```sh
PYTHONPATH=src:scratch/unchecked_tests .venv/bin/python -m unittest test_without_linkbase test_usd_only
.venv/bin/python scratch/unchecked_tests/implementation/verify_usd_only.py
```

All 13 constructed checks passed, including foreign-only facts, foreign facts
before USD duplicates, foreign nil facts, USD accounting fallbacks, mixed-currency
components and missing-ratio propagation. All four metric slots and both ratios
in 22 archived filings match the frozen linkbase-disabled baseline. Evidence is
in `implementation/usd_only_tests.txt`, `usd_only_real_log.txt` and
`usd_only_results.json` under `scratch/unchecked_tests`. Historical multicurrency
scripts below are superseded. Production CSVs and the live database were untouched.

### Follow-up structural cleanup (October 14, 2026)

Removed the unused full-fact return/conversion layers, retained fact IDs/context
IDs/decimals, stored Source taxonomy year and accession, and the calculation-only
CommitmentsAndContingencies special case. Context IDs are still used transiently
to associate Edgar facts with their contexts. The reviewed namespace allowlist
remains an acceptance check; it no longer stores a year in the prepared Source.
Accession provenance in production ratio rows still comes from the filing object.
Equity and interest accounting helpers no longer carry recursion-trail parameters.
The assets/liabilities cycle guard remains necessary for their mutual identities.
Edgar's constructor still requires a `calculation_trees` container; supplying that
empty container does not restore calculation-linkbase retrieval.

Eight constructed checks and all 22 archived filing comparisons passed after this
cleanup (`implementation/structure_cleanup_tests.txt` and
`implementation/structure_cleanup_real_log.txt` under `scratch/unchecked_tests`).
The latter compares against the frozen pre-removal, linkbase-disabled baseline;
it does not claim recovery of the ten deliberately missing liabilities results.

### Current retrieval: direct tags and accounting formulas (October 14, 2026)

Calculation-linkbase retrieval has been removed by user choice. The current
fallback order is **reported standard concept, then explicit metric-specific
accounting formulas**. The pipeline no longer downloads calculation/schema
attachments, parses calculation arcs, resolves weights/priorities/prohibitions,
or traverses calculation networks. `calculation_linkbase.py` and its associated
partition, applicability and rounding-comparison helpers were removed. Accounting
cycle prevention remains because assets and liabilities can refer to each other.
Source concept coverage was reduced to the concepts used by the remaining formulas.
The namespace-year allowlist and literal-prefix policy remain unchanged.

This is a coverage tradeoff, not evidence that calculation links only provide a
small accuracy improvement. No unverified zero assumptions were added. AMD/WMT
liabilities and debt-to-assets become missing in ten archived filings, as predicted
by the prior ablation; the candidate simplified identities below have not been
approved as generally complete fallbacks.

**Future features and known limitations:** alongside additional financial metrics,
consider restoring calculation-linkbase support if its demonstrated recovery
benefit warrants the complexity. Also investigate definition-backed accounting
alternatives and evidence for genuinely absent equity categories. Missing tags
alone do not establish zero. This change does not resolve those coverage limits.

Reproducible current checks (offline; scratch outputs only):

```sh
PYTHONPATH=src:scratch/unchecked_tests .venv/bin/python -m unittest test_without_linkbase
.venv/bin/python scratch/unchecked_tests/implementation/verify_without_linkbase.py
```

The eight constructed tests cover direct precedence/zero, complete partitions,
required equity inputs, cycles, nested interest, scope/currency selection and
instance-only fetching. The separate real-data check compares all four metric
slots and both ratios in all 22 filings to the frozen pre-removal **disabled**
linkbase results. Results are in `implementation/without_linkbase_results.json`
and the corresponding test/log files under `scratch/unchecked_tests`.
Older scratch suites and ablation scripts exercise the retired linkbase API and
are historical evidence, not the current regression command. A pre-removal source
snapshot is retained at `implementation/before_linkbase_removal`. Prior README
implementation sections below describe historical states where they conflict
with this section. No production CSV or live database operations are performed.

### Measured dependence on calculation links (October 14, 2026)

Offline ablation of the 22 archived filings from six companies (AAPL, AMD,
BRK-B, JPM, MSFT, WMT) compared unchanged retrieval against the same prepared
facts with `Source.equations` empty. This disables linkbase retrieval everywhere,
including within explicit accounting fallbacks; direct retrieval and those
accounting formulas remain enabled. No production code was changed for this test.

Two companies, AMD and WMT, lost liabilities and consequently debt-to-assets in
all five sampled filings each: 10 of 22 liabilities values and debt-to-assets
ratios. No other returned metric or ratio changed. Existing missing results did
not become available. This is dependence on the **currently implemented** formulas,
not proof that no additional justified accounting formula could recover a value.
The six issuers are not a representative sample of all S&P 500 companies, and
multiple years from one issuer are not independent company observations. The
observed 2/6 rate must not be extrapolated to an index-wide count.

Reproduce with `.venv/bin/python scratch/unchecked_tests/implementation/measure_linkbase_dependency.py`.
Per-filing enabled/disabled values are in
`scratch/unchecked_tests/implementation/linkbase_dependency_results.json`.
This uses original archived filing documents, not constructed examples, and
performs no network requests, production CSV writes or database operations.

### Compliant-input parsing simplification (October 14, 2026)

Parsing now assumes valid numeric syntax, valid context references, and the SEC
CIK entity scheme. Removed repeated validation of that scheme, the missing-context
recovery path, numeric syntax/nonfinite checks and arbitrary numeric-size limits,
and invalid-decimals validation. Annual-context selection no longer has a separate
contradiction scan; it still requires the matching annual DEI values and one start.
These are source-validity assumptions, not new SEC requirements. Malformed input
is outside this contract and may raise a native/library exception or propagate an
invalid number; it is no longer guaranteed to become `None`.

Missing values still return `None`. Selection by company, period, dimensions and
currency remains. The literal-prefix policy, reviewed concept/version coverage,
complete calculation inputs, priority/prohibition resolution and equity scope
checks remain because they determine which value a calculation can use. Numeric
conversion still uses the original fact text, not Edgar's floating-point field.
The applicable official references remain the [SEC XBRL Guide](https://www.sec.gov/files/edgar/xbrl-guide.pdf)
and its referenced XBRL specification; this change adds no runtime standards fetch.

Offline verification is recorded in
`scratch/unchecked_tests/implementation/compliant_parsing_tests.txt`,
`real_compliant_parsing_results.json` and `compliant_parsing_comparison.json`.
The constructed tests now test valid numeric conversion and missing states rather
than promising rejection of malformed numeric syntax. Archived filing tests are
real evidence; constructed cases are separate and neither proves universal coverage.

### Reduced source adapter — current implementation (October 14, 2026)

Under the user's compliant-formatting assumption, `source.py` no longer retains
a general namespace map or overrides Edgar's `_resolve_prefix`. It stores only
the US GAAP namespace declaration needed to select a supported taxonomy year.
It no longer checks for multiple taxonomy versions or resolves every returned
fact against a stored namespace map. Mixed standard taxonomy years and misleading
namespace declarations are not supported recovery cases.

The single `_extract_facts` hook still enforces the explicitly requested literal
fact-prefix policy before Edgar normalizes names. It excludes unsupported
prefixes and incorrect US GAAP/DEI namespace families; this protects the admission
boundary used by `read_facts`. After that boundary, the small, disjoint reviewed
concept lists assign admitted names to US GAAP or DEI. This also preserves correct
results when Edgar chooses another internally declared alias. There is no new
runtime taxonomy lookup, general alias-recovery mechanism or manual value parser.
Locally declared correct prefixes continue to work. Calculation locator matching
still uses the correct versioned official schema.

This is a modest reduction: `source.py` went from 278 to 264 lines, including
comments and blanks. The bulk remains the explicit concept lists, filing metadata,
Edgar adaptation and attachment acquisition. `Source` remains a filing container;
`FilingInstance` now has one hook rather than two. We have not claimed that merely
assuming compliant formatting makes entity/period/currency selection unnecessary.

Reproduction and evidence live in `scratch/unchecked_tests/implementation`:

```sh
PYTHONPATH=src:scratch/unchecked_tests .venv/bin/python -m unittest discover -s scratch/unchecked_tests
.venv/bin/python scratch/unchecked_tests/implementation/exercise_real.py real_source_simplified_results.json
.venv/bin/python scratch/unchecked_tests/implementation/compare_source_simplified_results.py
```

The final test log is `source_simplification_final_tests.txt`; archived-filing
comparison is `source_simplified_comparison.json`. The prefix-normalization
constructed test now checks both declaration orders. These cases remain separate
from the 22 real archived filings and are not evidence of universal coverage.

### Established fact prefixes — current acceptance policy (October 14, 2026)

Per the user's explicit scope restriction, financial facts must use the literal
`us-gaap:` prefix and the supported US GAAP namespace. Filing metadata must use
`dei:` and a supported DEI namespace. An arbitrary alias or an unprefixed fact is
not accepted merely because its namespace resolves to the same concept. No
alternative spellings have been established for this scope, so none are enabled.
New alternatives require an offline review of explicit official documentation.
No runtime standards research or downloads were added.

Official basis for the established spellings: the
[SEC glossary](https://www.sec.gov/page/osd_xbrlglossary) identifies `us-gaap` as
US GAAP shorthand; the [SEC XBRL Guide](https://www.sec.gov/files/edgar/xbrl-guide.pdf)
uses `us-gaap:` for its financial concept examples (§6.8) and `dei:` for filing
metadata (§3). The [SEC SRO guide, Figure 3](https://xbrl.sec.gov/sro/2024/sro-taxonomy-guide-2024-03-18.pdf)
explicitly lists `dei` with its namespace. Accepted taxonomies themselves remain
those reviewed from the [SEC operating-company listing](https://www.sec.gov/data-research/structured-data/taxonomies-schemas/standard-taxonomies/operating-companies).
The examples establish the spellings; they do not prove every possible alternative
violates SEC requirements. Excluding undocumented alternatives is our acceptance
policy, not a blanket finding of misfiling.

The original fact prefix is checked in `FilingInstance._extract_facts` before
Edgar can normalize multiple prefixes for one namespace. Namespace checks remain:
a familiar prefix attached to a custom namespace does not become an official tag.
A correct prefix declared locally on the fact remains accepted. This restriction
concerns the financial/DEI fact names; calculation locators still identify concepts
by their official schema and fragment, not by an XML fact prefix.

All 110 tests passed. All 44 ratio slots across 22 archived filings stayed unchanged;
production CSV hashes still match the original baseline, and no live database was used.
The former tests accepting arbitrary/default prefixes now expect missing values.
Additional constructed cases cover local declarations of accepted prefixes,
multiple root aliases, and mismatched prefix/namespace families. Real evidence is
separate in `implementation/real_established_prefix_results.json` and
`established_prefix_comparison.json`; tests are not proof of universal correctness.

```sh
PYTHONPATH=src:scratch/unchecked_tests .venv/bin/python -m unittest discover -s scratch/unchecked_tests
.venv/bin/python scratch/unchecked_tests/implementation/exercise_real.py real_established_prefix_results.json
.venv/bin/python scratch/unchecked_tests/implementation/compare_established_prefix_results.py
```

### Simplified retrieval — current implementation (October 14, 2026)

This section supersedes older architecture descriptions below. Five simplification
passes retained the reviewed metric definitions and supported fallback order:
reported concept, complete applicable filed calculation, then explicit metric
accounting formulas. No new metric aliases, estimates or custom-tag interpretations
were added.

1. Shared retrieval now owns direct/linkbase precedence once. Metric `derive_*`
   functions contain only their additional derivations. Nested metric derivations
   remain available; their cycle and calculation-network controls remain.
2. Removed `Amount`, its overloaded operators and propagation of rounding bounds
   through calculations. Every numeric getter returns `Decimal` or `None`.
   Explicit date/currency arguments filter each component before arithmetic;
   an amount no longer carries duplicate copies of those arguments.
3. Combined forward/inverse linkbase evaluation into one component loop. The
   inverse still requires an independently reported total and all other children.
   Removed the arbitrary 30-concept depth cap; revisiting a concept still stops
   the path. Removed the unused operating-income wrapper.
4. Rounding intervals now live in `get_equity.py`, only for the existing comparison
   between reported parent and inclusive equity. Ordinary numeric retrieval no
   longer computes intervals or rejects a usable number solely for missing
   `decimals`. That metadata remains necessary when performing the equity check.
5. Removed our manual context-dimension scan. Installed EdgarTools 5.58.0 already
   records explicit and typed segment dimensions, including nil typed members.
   We now use `Context.dimensions`. Noncompliant `scenario` content is outside the
   source assumption: [SEC Guide §8.5](https://www.sec.gov/files/edgar/xbrl-guide.pdf)
   forbids it. The former constructed forbidden-scenario test was replaced with
   explicit, typed and nil-typed segment cases. Also removed unused helper
   arguments and the separate public `retrieve`/`get_value` wrapper layer.

| Retrieval source | Before | After |
| --- | ---: | ---: |
| `get_value.py` | 362 | 253 |
| `source.py` | 276 | 269 |
| All eight retrieval modules | 1,048 | 882 |

Counts include comments and blank lines. Some rounding code moved to equity;
these total counts include that file, so the reduction is not just a file split.
Metric formulas remain explicit calls followed by ordinary arithmetic.

What remains has these purposes:

- Reviewed standard identities and period types: prevents an arbitrary/custom
  concept from being used as a supported component. Most early `source.py` lines
  are readable declarations, not a runtime research or validation engine.
- Edgar adapter and attachment acquisition: obtains a complete filing source and
  preserves namespace identity that the ordinary fact records do not retain.
- Company, period, dimensions and currency filtering: prevents different reporting
  bases from entering the same calculation. None, nil and zero remain distinct.
- Effective calculation relationships, missing-component checks, network isolation
  and cycle controls: preserve the existing nested and inverse derivation coverage.
- Metric formulas and equity applicability: prevent incomplete partitions and
  overlapping branches from being treated as the requested total.

`Source` remains one small dataclass holding a filing's records, units and
relationships plus annual-period/currency methods. `FilingInstance` remains an
Edgar subclass with two namespace-preservation hooks. These are implementation
choices, not SEC requirements. Replacing their syntax with dictionaries/functions
would not itself eliminate the underlying responsibilities. No per-value class
remains. Numeric conversion and Decimal arithmetic retain the existing finite
numeric limits and arithmetic precision; these are implementation choices too.

The stopping point is the simplest implementation justified here while retaining
current supported derivations and readable formulas—not a proof that every line
is mathematically indispensable or that all compliant filings are covered.
Earlier limitations on unreviewed concepts, missing information and unknown
future taxonomy versions still apply. Parser failures may still come from Edgar;
this work does not introduce manual exception raising or new error objects.

Evidence and reproduction (offline; no live pipeline/database):

```sh
PYTHONPATH=src:scratch/unchecked_tests .venv/bin/python -m unittest discover -s scratch/unchecked_tests
.venv/bin/python scratch/unchecked_tests/implementation/exercise_real.py real_simplified_results.json
.venv/bin/python scratch/unchecked_tests/implementation/compare_simplified_results.py
```

Logs `implementation/simplify_pass1_tests.txt` through `simplify_pass5_tests.txt`
each record 103 passing tests. The final run passed all 107 tests, including the
additional constructed cases in `test_numeric_retrieval.py`. All 44 ratio slots
across the 22 archived filings stayed unchanged, including missing values.
Production CSV hashes still match the original baseline. `real_simplified_results.json`
and `simplified_comparison.json` contain the real archived-filing results and
comparison to the first-row-selection baseline. The existing suite also compares
88 metric values against the archived independent extraction baseline. Tests
are sample evidence, not proof of universal correctness. Constructed cases are
identified as such; no constructed fact is presented as a real filing disclosure.

### First matching reported value — earlier implementation (October 14, 2026)

Reported selection now takes the first numeric fact after concept identity,
company, exact period, nondimensional scope and currency selection. It no longer
compares duplicate values or selects the greatest `decimals`. Currency ambiguity
and nil handling remain separate from choosing between numeric duplicates.

This relies on the user's explicit assumption of compliant source filings:

- [SEC XBRL Guide](https://www.sec.gov/files/edgar/xbrl-guide.pdf), August 2026,
  §§9.6–9.10: equivalent contexts/units cannot provide different reporting bases;
  numeric duplicates must agree at equal accuracy or have consistent rounding.
- The same Guide §2 incorporates xBRL-XML/OIM. Its
  [§§2.1.1–2.1.4](https://www.xbrl.org/Specification/xbrl-xml/REC-2021-10-13/xbrl-xml-REC-2021-10-13.html)
  exclude non-dimensional segment/scenario content and tuples. Thus these cannot
  supply a hidden distinction between our otherwise matching compliant facts.
  Guide §8.5 also prohibits scenario elements. Older SEC rules likewise restricted
  segment content to dimensions (e.g. [EFM §6.5.5](https://www.sec.gov/files/edgar/filermanual/archive/efmvol2-v37.pdf)).

**Implementation choice, not SEC's consolidation algorithm:** Guide §9.10 uses
maximum decimals for validation/rendering. We deliberately retain the first
reported amount instead. It may be more coarsely rounded; neither negligible
numerical impact nor order-independent ratios is promised. Noncompliant conflicting
numeric duplicates are no longer detected. Metadata differences such as IDs,
labels and presentation placement do not create another monetary basis.

`reported_selection` shrank from 33 to 14 lines. It retains the chosen fact's
rounding bounds because existing accounting applicability checks use them.
This is a targeted simplification, not removal of all precision-related code.

Offline evidence is in `scratch/unchecked_tests/implementation/first_row_tests.txt`,
`real_first_row_results.json` and `first_row_comparison.json`. All 103 tests passed. The 22 archived
constituent filings produced unchanged results in all 44 ratio slots (including
missing slots). Production selection tests also exercise 56 archived duplicate
groups in both orders, original Apple differing-accuracy disclosures, and
constructed cases separating company, concept, period, dimensions and currency.
The Apple unrelated concept tests selection only, not expanded metric coverage.
Older precision experiments remain historical evidence. Tests do not prove
universal correctness; the general conclusion relies on the official rules and
on our filtering/parser preserving those aspects correctly.

Reproduce without network, production CSV writes or live database access:

```sh
PYTHONPATH=src:scratch/unchecked_tests .venv/bin/python -m unittest discover -s scratch/unchecked_tests
.venv/bin/python scratch/unchecked_tests/implementation/exercise_real.py real_first_row_results.json
.venv/bin/python scratch/unchecked_tests/implementation/compare_first_row_results.py
```

## Current code structure

Each metric owns its explicit standard concepts and financial fallbacks. Its public
getter returns a `Decimal` or `None`. Each ratio calls those getters and divides.
The pipeline selects a common currency and saves the value with an availability
status. Standards research stays offline; Edgar parses the filing.

```text
src/value_retrieval/
    get_assets.py             Assets and their ordered accounting fallbacks
    get_liabilities.py        Liabilities and their accounting fallbacks
    get_equity.py             Permanent/temporary equity and scope
    get_interest_expense.py   Total interest and approved component formulas
    get_operating_income.py   Operating income
    get_value.py              Fact selection and calculations
    source.py                 Edgar facts and reporting contexts
    calculation_linkbase.py   Effective calculation arcs, priorities and prohibitions

src/calculations/
    debt_to_asset_ratio.py     Get liabilities, get assets, divide
    interest_coverage_ratio.py Get operating income, get interest, divide

src/table_data/                Company data, filing iteration and CSV output
src/database/                  Schema, loads and views
```

The ratio modules are 18 lines each, including imports and blank lines. For example:

```python
liabilities = get_liabilities(financial_data, period_end, currency=currency)
assets = get_assets(financial_data, period_end, currency=currency)
```

After handling missing inputs and a zero denominator, the function returns
`liabilities / assets` under a fixed 28-significant-digit Decimal context.
The currency is selected by `generate_ratios.filing_ratio`, which accepts exactly
one complete currency basis. No paired metric getter is involved.

### Values or None, without issue tracking — current behavior

The `issues` parameters, shared issue sets and invalid-data code collection have
been removed from retrieval, source selection and ratio calculations. Each getter
returns its value or `None`; each ratio returns its quotient or `None`. There are
no manual validation exceptions or replacement diagnostic objects.

A fallback returning `None` permits the next fallback, whether the earlier attempt
was absent, unusable, or unsupported. This intentionally removes the former rule
that a rejected earlier fact could block an otherwise successful later derivation.
Tests cover missing/unusable inputs followed by calculation/accounting formulas.
Conflicting numeric duplicates are now outside runtime validation, as explained above. Successful values, including zero, still stop
fallback evaluation. Calculation applicability, matching basis, complete inputs,
standard-concept eligibility and duplicate fact selection remain in place.

At the CSV/database boundary the existing status columns now contain only
`available` or `missing` for newly generated rows, preserving compatibility with
views that display available values. The ratio is blank/NULL when missing. The
pipeline no longer distinguishes missing components, zero denominators, rejected
facts or unsupported structures in output. `None` does not establish a custom tag
or filing error: a compliant filing may simply lack the necessary information,
or the implementation may lack coverage. Historical rows are not rewritten.

Multiple currencies are still never combined. Without a reporting currency, only
one currency with a computable ratio is accepted. A currency whose ratio returns
None no longer contributes a separate zero-denominator or invalid-data state.
Source calculation completeness remains necessary to avoid using partial linkbases;
that applicability check does not produce a per-value issue collection.

Verification: 102 tests pass (`implementation/no_issues_tests.txt`). All 44 ratio
values across 22 archived filings remain unchanged. Eleven unavailable interest
ratios now have the generic `missing` status. The changes are recorded in
`implementation/no_issues_results_comparison.json`. Production CSV hashes are
unchanged; no live pipeline or database ran. Reproduce with:

```bash
PYTHONPATH=src:scratch/unchecked_tests .venv/bin/python -m unittest discover -s scratch/unchecked_tests
.venv/bin/python scratch/unchecked_tests/implementation/exercise_real.py real_no_issues_results.json
.venv/bin/python scratch/unchecked_tests/implementation/compare_no_issues_results.py
```

Earlier issue/status-code descriptions below are historical and superseded.

### Taxonomy baseline — October 14, 2026

**Concept names, definitions, period types and accounting formulas use the reviewed
US GAAP 2026 taxonomy as the fixed baseline.** The baseline was documented on
October 14, 2026; this is not a claim that every taxonomy accepted on that date
is implemented. Sources are the official [2026 definitions](https://xbrl.fasb.org/us-gaap/2026/elts/us-gaap-doc-2026.xml)
and [2026 schema](https://xbrl.fasb.org/us-gaap/2026/elts/us-gaap-2026.xsd).

Runtime concept selection no longer branches on filing year. The special 2024
availability gate for `InterestExpenseOperating` and `InterestExpenseNonoperating`
was removed. A tag that is absent still supplies no value; missing components are
not inferred as zero. Reviewed standard concepts remain distinct from custom tags.

The existing 2021–2026 namespace/schema identifiers remain solely to recognize the
filing's standard taxonomy references. They do not select a different definition
or formula. A future unrecognized taxonomy release is still unsupported until
its identifiers and relevant definitions are reviewed. Historical definition
changes are not handled through per-version rules under this policy; the older
release comparisons remain offline documentation, not runtime behavior. This
supersedes earlier requirements below for version-specific concept availability.

The offline concept check verifies all supported concepts against 2026 and records
differences from the other five archived official releases. Future baseline updates
are deliberate code/documentation changes, never runtime standards downloads.
Verification: 102 tests pass in `implementation/taxonomy_baseline_tests.txt`.
All 44 ratio values across 22 saved filings remain unchanged. Walmart's missing
interest ratios for 2022–2024 now have `missing_required_amount` instead of
`incomplete_standard_coverage`, because an absent 2026-baseline concept is no
longer rejected by a historical-availability gate. No missing amount was recovered.
Results: `implementation/baseline_results_comparison.json`. Reproduce with
`exercise_real.py real_baseline_results.json`, then `compare_baseline_results.py`
in `scratch/unchecked_tests/implementation`. No live pipeline or database ran.

### Invalid data returns None — current behavior

Explicit validation exceptions have been removed, including `SelectionError`.
Invalid or unsupported fact values, conflicting duplicates, incompatible units,
ambiguous dates/currencies, missing instances and unsupported taxonomy versions
return `None`. Missing annual dates and zero divisors also return `None` from
metric/ratio functions. Callers check the returned value instead of catching a
validation exception. Existing issue sets still supply CSV missing-state codes;
invalid attempted data cannot be hidden by a later numerical fallback.

An empty extraction returns without replacing the completed CSV. A database CIK
collision returns before any row is written: the loader checks existing ownership
for the whole batch first. No explicit `raise` statements remain under `src`.
This does not catch arbitrary programming, network, filesystem or database-library
exceptions and disguise them as missing financial data.

The old exception assertions were replaced with `None` assertions. Six constructed
tests additionally cover malformed numeric values/accuracy, invalid duplicates
with a valid fallback, invalid units, conflicting reporting currencies, unsupported
taxonomy/missing instance, and incompatible arithmetic. The database test now
checks that a collision on a later row leaves the earlier row unwritten.
`implementation/none_validation_tests.txt` records 102 passing tests.
`implementation/none_results_comparison.json` records unchanged values and statuses
for all 44 ratios in 22 archived filings. Source-level failures that now return only
`None` use the generic missing-source/period status rather than exception-specific
messages. No production CSV or live database was changed.

```bash
PYTHONPATH=src:scratch/unchecked_tests .venv/bin/python -m unittest discover -s scratch/unchecked_tests
.venv/bin/python scratch/unchecked_tests/implementation/exercise_real.py real_none_results.json
.venv/bin/python scratch/unchecked_tests/implementation/compare_none_results.py
```

Earlier references below to raised validation errors are historical and superseded.

### Explicit metric formulas — current layout

Metric files now name the concepts at their retrieval calls and express accounting
formulas with `+` and `-`, matching the style of revision `ab40cee`:

```python
current_assets = get_component('us-gaap:AssetsCurrent')
noncurrent_assets = get_component('us-gaap:AssetsNoncurrent')
if current_assets is not None and noncurrent_assets is not None:
    return current_assets + noncurrent_assets
```

`get_component` is a local call to shared retrieval with the same company, dates,
currency and recursion path. The internal `Amount` record implements addition and
subtraction through the existing compatible-basis arithmetic; the public metric
getter still returns Decimal or None. No new reader class or module was added.
The former `add_amounts` and `subtract_amounts` wrappers were removed.

The general reviewed-concept lists moved from metric files to `source.py`, which
uses them to restrict parser/calculation coverage. They do not dispatch formulas.
Liability/equity branch classifications remain beside the specialized linkbase
partition that uses them. Direct concept names and formulas are now visible in
assets, liabilities, equity, interest and operating-income retrieval.

The priority and financial selection rules below remain unchanged. Verification:
`implementation/explicit_formula_tests.txt` records 96 passing tests;
`implementation/explicit_results_comparison.json` records identical values and
statuses for all 44 ratios across 22 saved real filings. Reproduce the comparison
with `exercise_real.py real_explicit_results.json`, then `compare_explicit_results.py`
in `scratch/unchecked_tests/implementation`. No live pipeline or database ran.

### Current policy: first successful fallback — October 13, 2026

The priority is **direct reviewed concept → applicable filed linkbase → supported
accounting identity**. The liability branch partition is itself linkbase-based,
so it runs before the current/noncurrent accounting identity. All concept lookups
still use the hardcoded reviewed taxonomy concepts and applicable release definitions;
no custom concepts, unreviewed aliases or runtime standards research were added.
The order correction is covered by `implementation/priority_order_tests.txt` and
`implementation/priority_results_comparison.json`; all 44 archived ratio values
and statuses match the immediately preceding ordered-fallback implementation.
Reproduce that comparison with `exercise_real.py real_priority_results.json`, then
`compare_priority_results.py`, both in `scratch/unchecked_tests/implementation`.

At the user's instruction, a successful fallback now returns immediately. Later
alternatives are neither evaluated nor compared. Reported totals are returned
without independently reconciling them to calculation equations or other totals.
`select_consistent_amount`, `check_reported_amount`, `check_balance`, and
reported-concept dependency tracking have been removed. This is an intentional
policy change, not a claim that the earlier cross-checks were mathematically redundant.

The explicit order is:

| Metric | Order after its directly reported concept |
| --- | --- |
| Assets | Filed calculation; current + noncurrent assets; combined liabilities/equity total; liabilities + inclusive permanent equity + temporary equity |
| Liabilities | Filed calculation; complete reviewed balance-sheet branch partition; current + noncurrent liabilities; assets − inclusive permanent equity − temporary equity |
| Inclusive permanent equity | Filed calculation; parent equity + noncontrolling interest |
| Temporary equity | Filed calculation; parent temporary equity + redeemable noncontrolling equity |
| Total interest expense | Filed calculation; operating + nonoperating interest expense |
| Operating interest expense | Filed calculation; operating interest income − net operating interest income |
| Operating income and other reviewed components | Filed calculation only |

A filed calculation returns the first complete applicable equation in supplied
network/relationship insertion order. Both forward sums and inverse equations are
eligible; they are not separately ranked. Metric fallback priority is an explicit
implementation policy. Network order is **not an established reliability ranking**.
Different applicable equations can therefore produce a different selected result
when their order changes. There is no claim that this ordering is prescribed by
SEC or that the first complete result must be the most accurate result.

Each attempted fallback still requires the reviewed concepts, applicable scope,
matching dates and currency, valid weights, and complete components. The existing
parent/inclusive/temporary-equity applicability rules remain: these decide whether
a formula measures the requested quantity, rather than comparing completed fallback
results. Recursion paths still prevent cycles. Missing components are never presumed
zero. A returned zero is successful and stops fallback evaluation.

Duplicate occurrences of the same reported concept are still selected using their
declared precision and checked for consistency. They are not different fallbacks.
Currency ambiguity, zero divisors, exact CSV handoff and missing-state storage are
unchanged. Missing-state coverage notes now describe only attempted retrieval paths,
not unused equations that independent reconciliation previously inspected.

**Verification:** 96 offline tests pass. Constructed conflict/rounding tests were
explicitly updated to assert the new precedence policy; they no longer assert
rejection of alternative totals. Four additional tests prove that reported values
skip fallbacks, successful equations skip later duplicate conflicts, derived zero
stops evaluation, and an incomplete equation permits the next complete equation.
The original tests' failures under the new policy are retained in
`implementation/ordered_fallback_tests_initial.txt`.

Across 22 archived real filings, all 44 ratio values (including missing values)
remain unchanged. Four missing interest-coverage statuses change from
`incomplete_standard_coverage` to `missing_required_amount`: AAPL 2025, BRK-B 2025,
and WMT 2025/2026. These are not newly recovered values or resolved coverage gaps.
Results are in `implementation/real_ordered_results.json` and
`implementation/ordered_results_comparison.json`. Production CSV hashes are
unchanged; no live pipeline or database was used. Sample results do not establish
universal correctness, especially for conflicting untested alternatives.

```bash
PYTHONPATH=src:scratch/unchecked_tests .venv/bin/python -m unittest discover -s scratch/unchecked_tests
.venv/bin/python scratch/unchecked_tests/implementation/exercise_real.py real_ordered_results.json
.venv/bin/python scratch/unchecked_tests/implementation/compare_ordered_results.py
```

The revisions below are historical. Their references to reconciliation,
dependency tracking, unchanged status codes and comparison scripts describe the
previous policy and are superseded by this section. The historical dependency
comparison script requires the earlier implementation; it is not a current check.

### Earlier minimal-code revision — October 13, 2026

Removed `checks.py`, `RatioResult`, the `evaluate_*` wrappers, per-getter audit
dictionaries, nested serialized derivation trees, runtime document hashing,
repeated CSV/evidence validation, and unused scalar helper APIs. Historical audit
helpers needed only by scratch scripts now live in `legacy_api.py` under scratch.
Production has no runtime taxonomy downloads or concept-metadata JSON.

`amount.py` has now been removed. Its shared retrieval helpers live in
`get_value.py`; there is no replacement module. The numerical behavior is unchanged,
including the filing-rounding checks used to compare disclosed totals.
`implementation/remove_amount_tests.txt` records the verification of this relocation.

The internal `Amount` record in `get_value.py` retains only the number, currency, company/period, rounding bounds,
reported-concept dependencies, and whether it is directly reported. Dependency
sets replace nested evidence trees: without them, a derivation could be used to
validate the very reported number on which it depends. Public getters validate
independently; recursive component lookups do not repeat that validation.

Checks retained in retrieval affect financial interpretation: consolidated scope,
period/currency compatibility, duplicate precision, complete applicable equations,
effective calculation relationships, conflicting alternatives and independent
reconciliation. Missing components remain missing. Missing does not establish zero.
The optional `issues` set records encountered coverage limitations for the pipeline's
missing-state code; it does not change the value returned by a getter.

CSV output retains company/accession/dates and one status per ratio, but no nested
`extraction_evidence` JSON. The existing database/view column of that name remains
nullable for schema compatibility; new inserts leave it NULL, and updates clear
old evidence. No database migration was executed. The loader preserves decimal
strings and NULLs, and prevents a ticker/period update from replacing another CIK.
Views still exclude unverified values from ranking. Offline scratch results retain
the source documents and historical detailed evidence.

Verification is recorded in `scratch/unchecked_tests/implementation/`:

- `minimal_tests.txt`: 92 passing offline tests, including constructed
  financial boundaries, CSV round trips and isolated SQLite handoff tests.
- `minimal_results_comparison.json`: all 44 ratio values and statuses unchanged
  across 22 saved real filings (AAPL, AMD, MSFT, WMT, BRK-B and JPM).
- `minimal_dependencies_comparison.json`: 176 amount comparisons preserve value,
  currency, period, rounding bounds, reported/derived state and dependencies.
  Half use the saved filings unchanged; half deliberately hide four target totals
  to exercise derivations and are constructed experiments.
- Production CSV SHA-256 hashes are unchanged. No live pipeline or database ran.
  SQLite tests verify handoff/NULL behavior, not PostgreSQL numeric precision.

Reproduce from the repository root:

```bash
PYTHONPATH=src:scratch/unchecked_tests .venv/bin/python -m unittest discover -s scratch/unchecked_tests
.venv/bin/python scratch/unchecked_tests/implementation/exercise_real.py
.venv/bin/python scratch/unchecked_tests/implementation/compare_minimal_results.py
.venv/bin/python scratch/unchecked_tests/implementation/compare_minimal_dependencies.py
```

Three obsolete tests policing generated evidence, duplicate output rows, and
nonfinite CSV inputs were removed with the duplicate validator. New tests verify
exact CSV values/missing states, distinct filing periods at generation, and CIK
collision protection. Existing financial conflict tests now assert returned status
codes instead of retired console messages. Financial selection tests remain.

This revision simplifies implementation; it does not expand coverage. Official
concept definitions and source references remain in the review below. Unreviewed
standard components and structures are still coverage gaps; custom concepts remain
excluded. Missing disclosures and non-unique rounded derivations remain information
limits. The saved sample and constructed tests do not prove universal correctness.

**The implementation sections below describe earlier revisions. Where they discuss
`RatioResult`, audit dictionaries, detailed runtime evidence or retired helper
functions, this current-code section supersedes them.**

## Use edgar shortcuts for reading, not unreviewed metric decisions

Prefer the installed library's existing operations when they preserve our inputs
and do not introduce metric interpretation. This review used `edgartools` 5.58.0,
which is pinned in `requirements.txt`.

| Shortcut | Use in this pipeline |
| --- | --- |
| `Company(cik).get_filings(form='10-K', amendments=False)` | Find original annual filings. Already used. |
| `XBRLAttachments(...).get('instance')` | Locate the extracted instance. Already used, with the existing homepage fallback. |
| `attachments.query("document_type in ['EX-101.CAL', 'EX-101.SCH']")` | Now selects all matching schema/calculation attachments from both attachment lists; repeated URLs are read once. It replaces our manual type filter. |
| `attachment.content` | Let edgar handle local/SGML contents or SEC transport. Already used. |
| `get_total_assets()` and other high-level metric helpers | Not used. The inspected assets helper selects through standardized-label patterns, rather than our explicit concept/period/currency/fallback rules. |
| `XBRL.from_filing()` as the entire replacement reader | Not used. It selects one attachment per linkbase type and its parsed calculation representation omits details needed by our policies. |
| `InstanceParser.parse_instance_content`, `Context`, `Fact.value`, `Fact.decimals`, `units` | Primary input for all selected facts, including ID-less duplicates. Exact strings feed Decimal arithmetic; a small subclass preserves namespace identity. |

The attachment shortcut selects documents, not financial values. The standard
concept list, metric definitions, fallback formulas and precision rules remain
our own explicit code. No runtime standards research or new source-value checks
were introduced. The XML parser still cannot download referenced schemas.

Earlier attachment-shortcut validation: 78 offline tests passed. A constructed test checks that multiple
calculation documents, including one in the document list, are retained and a
repeated URL is not counted twice. Separately, the adapter produces exactly the
same parsed data/equations/provenance as direct parsing for all 22 archived
original SEC filings. Reproduce that real-document comparison with:

```bash
.venv/bin/python scratch/unchecked_tests/implementation/exercise_edgar_attachments.py
```

Results are in `implementation/edgar_shortcuts_comparison.json` and
`implementation/edgar_shortcuts_tests.txt` under `scratch/unchecked_tests`.
The adapter harness supplies saved attachment contents; it does not test live
SEC networking. Production CSVs and the live database were untouched.

## Independent metric retrieval — earlier October 13 revision

The paired getters `get_liabilities_and_assets`, `get_income_and_interest`,
and `get_compatible_values` have been removed. No replacement paired module,
wrapper class, or callback was introduced.

Each ratio now calls the individual metric modules and contains the arithmetic:

```python
liabilities = get_liabilities(financial_data, period_end, currency=currency, audit=audit)
assets = get_assets(financial_data, period_end, currency=currency, audit=audit)
ratio = liabilities / assets
```

```python
operating_income = get_operating_income(
    financial_data, period_start, period_end, currency=currency, audit=audit)
interest_expense = get_interest_expense(
    financial_data, period_start, period_end, currency=currency, audit=audit)
ratio = operating_income / interest_expense
```

Standalone calls such as `get_assets(source, end)` still return Decimal or None.
The optional `currency` restricts the requested basis; the optional `audit`
dictionary records the returned amount, checks and coverage notes for CSV/DB
evidence. It does not affect the returned value or depend on another getter.

The shared `get_value` retrieval path independently performs scope/period/unit,
precision, duplicate, fallback and available filed-equation validation before a
public metric getter returns. Asset retrieval also performs balance-sheet
reconciliation, looking up whatever supporting components are available. Those
components are evidence for the asset amount, not a paired return value.
Internal `get_amount` and `get_*_amount` functions remain recursive component
readers; the public getters establish independent reconciliation at their boundary
to avoid recursively revalidating the same equations.

The calculation layer brings independently obtained amounts together. It tries
the reporting currency, or each disclosed currency when no reporting currency
is established. Both individual getters receive the same requested currency and
dates. This preserves a valid single complete pair even if one metric alone is
available in several currencies; disjoint currencies are never combined and
multiple complete currencies remain ambiguous. The calculator then checks basis,
handles zero division, performs 28-digit HALF_EVEN arithmetic, and packages the
existing statuses/evidence. None of the tag selection, accounting fallbacks or
reconciliation occurs in calculation files.

`get_ratio_values.py`, `calculate_ratio.py` and `RatioValues` remain removed.
`RatioResult` stays in `amount.py` for the existing CSV/database output contract.

**Behavioral correction:** standalone public getters now perform reconciliation
that previously ran only when both ratio operands existed. One old constructed
test incorrectly expected reported assets of 0 or 99 to override an independently
filed sum of 30. It now uses consistent data for the reported-value/zero test,
with a separate test requiring rejection of the conflicting sum. Four individual
metric getters are separately tested against conflicting filed equations.

**Verification:** 92 offline tests pass. All numeric and missing values for the
22 archived real filings are unchanged, and all available results retain identical
evidence. Seven unavailable interest-coverage results gain coverage notes from
the independently validated operating-income amount. Four consequently change
status from `missing_required_amount` to `incomplete_standard_coverage`
(AAPL 2025, BRK-B 2025, WMT 2025/2026); WMT 2022–2024 retains that status with an
additional note. No new numeric ratio is inferred. The exact changes are recorded
in the comparison JSON.

The added tests use constructed inputs for individual reconciliation, nil/zero,
the annual-period failure, one common currency among several, disjoint currencies,
and an available operand whose partner is missing. These are separate from the
archived real filing evidence. Production CSV hashes are unchanged; no live
pipeline or database was used. Existing coverage and information limits remain.

```bash
.venv/bin/python -m unittest discover -s scratch/unchecked_tests
.venv/bin/python scratch/unchecked_tests/implementation/exercise_real.py
.venv/bin/python scratch/unchecked_tests/implementation/compare_independent_getters.py
```

Results: `scratch/unchecked_tests/implementation/independent_getter_tests.txt`,
`independent_getter_boundary_tests.txt` and `independent_getter_comparison.json`.
Earlier `direct_ratio_*` and `ratio_boundary_*` artifacts describe the
intermediate architectures that have now been removed.

## Primary Edgar parser — October 13, 2026

`source.py` now has 222 lines and `calculation_linkbase.py` has 66. The change is
not just moving code: manual fact/unit extraction and the second instance parse
are gone. The remaining source code loads attachments, retains provenance,
adapts Edgar objects to selection fields, and selects annual periods/currencies.
Calculation documents are now parsed once each, including reference checks.

The standards and the trusted-source assumption allow these simplifications:

- All 63 reviewed US GAAP concepts have monetary type in their applicable
  official schemas. The offline `review_explicit_concepts.py` checks that fact
  against all six archived versions. Only those concepts and four required DEI
  concepts enter `Source.records`; other standard concepts remain a coverage
  limitation, not permission to substitute their values.
- For monetary concepts, a compliant unit has one ISO currency measure.
  Reading the local currency name from Edgar's measure is therefore sufficient;
  currency *compatibility* is still checked when combining values. This is the
  mandatory rule in [XBRL 2.1 §4.8.2](https://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31%2Bcorrected-errata-2013-02-20.html).
- An empty value on one of these compliant monetary facts means nil, not zero.
  This follows from its decimal type and XML nil semantics; see
  [XML Schema decimal](https://www.w3.org/TR/xmlschema-2/#decimal) and
  [XML Schema nil](https://www.w3.org/TR/xmlschema-0/#Nils).
  The rule is not applied to arbitrary text concepts. Absent facts, nil facts,
  and disclosed zero remain distinct; nil/numeric conflicts are still rejected.

These are consequences of mandatory type rules under the user's source-reliability
assumption, not guesses from filing conventions. The code is not a general
validator for malformed numeric facts or monetary facts with invalid units.
The four DEI values are used for period/currency selection; their empty strings
remain unavailable and their explicit nil attribute is not separately retained.

What still needs a supplement:

- Two small private Edgar hooks retain namespace mappings, including locally
  declared/default namespaces and shadowed prefixes. They call the library's
  implementations and do not replace fact parsing. This is a dependency on the
  pinned 5.58.0 interface; upgrades need these regression tests.
- A short scan of the already parsed context nodes preserves dimension exclusion,
  including arrangements its segment reader omits. The scenario test is a
  constructed boundary test, not evidence that SEC accepts every scenario.
- The calculation supplement preserves locator identity and resolves priority
  and prohibition. Existing tests demonstrate why simply using the library's
  calculation trees would change results. It reads only filing documents;
  no standards are researched or downloaded during extraction.

**Verification:** 84 offline tests pass. The 22 archived filings retain the same
multiset of relevant facts (including duplicates and nil), referenced monetary
units, equations, and provenance. Edgar changes some fact ordering and we omit
unused concepts; those are intentional internal differences. All 22 complete
ratio results, including statuses and evidence, are identical. The comparison
uses the frozen previous reader in scratch. Production CSV hashes are unchanged;
no live pipeline, database, or network was used in these tests.

Reproduce:

```bash
.venv/bin/python -m unittest discover -s scratch/unchecked_tests
.venv/bin/python scratch/unchecked_tests/review_explicit_concepts.py
.venv/bin/python scratch/unchecked_tests/implementation/exercise_real.py
.venv/bin/python scratch/unchecked_tests/implementation/compare_primary_edgar.py
```

Evidence is in `scratch/unchecked_tests/implementation/primary_edgar_tests.txt`,
`primary_edgar_boundary_tests.txt`, and `primary_edgar_comparison.json`.
The real documents cover AAPL, AMD, MSFT, WMT, JPM and BRK-B; added namespace,
nil/zero and local-currency cases are constructed. Existing finite-concept and
calculation-structure coverage limits remain. Live transport and PostgreSQL
integration were not tested; these samples do not prove universal correctness.

The earlier `edgar_instance_*` and `edgar_shortcuts_*` result files describe the
previous intermediate implementations, not the current architecture.

## Trusted-source assumption — October 13, 2026

The pipeline assumes its source values are reliable. Wikipedia tickers, CIKs,
company names and sectors are imported without separate missing/blank, duplicate,
or positive-integer checks. The former `check_companies` function and its calls
at CSV creation, extraction and company loading have been removed. Ordinary type
conversion remains where needed to call the SEC API or write database fields.
`check_ratios` no longer revalidates copied ticker/date fields for blank values
or date syntax.

The remaining handoff checks concern our outputs: duplicate ticker/period rows,
nonfinite computed ratios, and disagreement between values, availability statuses
and serialized evidence. Database provenance checks concern the audit fields our
pipeline must supply. These are separate from checking whether Wikipedia's
values are correct.

Financial fact selection still requires the appropriate company, reporting
period, currency, supported tag and usable calculation structure. Reliable source
facts can describe different scopes, and rounded facts can yield ambiguous
derivations. Those selection, arithmetic, reconciliation and missing-state rules
remain unchanged. Numeric parsing and supported-precision limits also remain.
Source reliability is an explicit assumption, not something this code verifies.

The obsolete empty-company rejection test has been removed, along with the
source-date rejection assertions. The database-boundary test now exercises
corrupted generated ratio evidence rather than a blank source date. The remaining 77 offline tests pass; no live
pipeline or database was run and production CSV hashes remain unchanged. See
`scratch/unchecked_tests/implementation/trusted_sources_tests.txt` and
`trusted_sources_preservation.json`.

## Explicit concepts: reviewed offline, selected at runtime

**No runtime standards research:** accepted tags, version limits and accounting
rules are established beforehand and hardcoded. Namespace and standard-schema
URLs in `source.py` are identifiers compared as strings; the program does not
open them or download FASB definitions. A namespace need not display a working
webpage. Runtime retrieval reads company filing documents (including their filed
calculation relationships), and the existing Wikipedia company-list pull remains.
The XML parser has network access disabled. Source-review scripts under scratch
are separate from the production pipeline.

`standard_concepts.json.gz` has been removed from production. Each metric file
now declares its `SUPPORTED_CONCEPTS`: **63 distinct tags**, verified against the
archived official US GAAP schemas and definitions for 2021–2026. `source.py`
contains six supported release identifiers and combines the explicit instant
and duration sets. There is no taxonomy file to open, decompress or parse at
runtime. This removes the broad registry; it does not eliminate the checks of
actual facts, periods, currencies or filed relationships. No runtime speedup has
been benchmarked.

The source basis is the [SEC accepted taxonomies listing](https://www.sec.gov/data-research/structured-data/taxonomies-schemas/standard-taxonomies),
the [official FASB 2026 definitions](https://xbrl.fasb.org/us-gaap/2026/elts/us-gaap-doc-2026.xml)
and [technical schema](https://xbrl.fasb.org/us-gaap/2026/elts/us-gaap-2026.xsd),
plus the corresponding official releases for older filings. Exact per-version
source URLs, hashes, definitions and differences are saved in
`scratch/unchecked_tests/implementation/explicit_concept_review.json`.
The verification script checks the archived files against their original source
manifest; it does not generate production code or choose accounting formulas.

| Metric file | Explicit scope |
| --- | --- |
| `get_assets.py` | Total/current/noncurrent assets and named cash, receivable, investment, tax, lease, tangible and intangible asset components. |
| `get_liabilities.py` | Total/current/noncurrent liabilities, the existing reviewed balance branches, and named noncurrent income-tax/customer-contract components for filed equations. |
| `get_equity.py` | Parent/noncontrolling permanent equity, temporary equity portions, combined balance total and the commitments caption. |
| `get_interest_expense.py` | Total/operating/nonoperating interest expense, operating interest income/net interest, finance-lease interest, incurred and capitalized interest costs. |
| `get_operating_income.py` | Operating result, revenue/cost/gross-profit/expense components and named pretax/nonoperating amounts used in filed equations. |

**A component list is not a sum or a list of interchangeable tags.** For example,
pretax income does not substitute for operating income, and finance-lease
interest does not substitute for total interest expense. The additional tags
can be used only through the actual complete filed equation and its weights.
They cannot become new fixed accounting fallbacks simply because they are in a
set. Existing fixed formulas remain in their metric files. No missing component
is treated as zero, and no unreviewed child is silently dropped from a sum.

The operating/nonoperating interest-expense concepts are enabled only from
2024, when they first appear in these official releases. Other reviewed tags
exist with the same period type throughout 2021–2026. Definitions nevertheless
change: examples include asset/liability wording, the 2022 debt carrying-amount
wording, goodwill's joint-venture scope, and 2026 intangible/software and
property/collection wording. All differences are preserved in the review data.
Component tags follow their filing-version meanings and filed relationships;
we do not reinterpret historical amounts as 2026 amounts.

**Coverage tradeoff:** this is a finite reviewed implementation list, not the
complete SEC-accepted taxonomy. A valid standard component outside the list
makes that equation unsupported. That is a pipeline coverage gap, not a filing
error or evidence of zero. A directly reported supported amount can still be
returned, with coverage notes when an independent equation cannot be checked.
Future taxonomy versions and additional standard structures need explicit
review. Custom tags remain intentionally excluded. Missing disclosures and
rounding that does not determine a unique amount remain information limits.

Reproduce the source check and filing comparison from the repository root:

```bash
.venv/bin/python scratch/unchecked_tests/review_explicit_concepts.py
.venv/bin/python -m unittest discover -s scratch/unchecked_tests
.venv/bin/python scratch/unchecked_tests/implementation/exercise_real.py
.venv/bin/python scratch/unchecked_tests/implementation/compare_explicit_tags.py
```

The tests include original SEC XML for 22 qualifying S&P 500 filings and
separate constructed cases for unreviewed components/parents, version limits,
precision and reconciliation. The current duplicate-selection retrieval test
covers 56 groups within the explicit list. The historical Apple tax-benefit
duplicates remain a test of the shared precision selector, but that unrelated
tag is no longer accepted by metric retrieval. Passing these tests does not
establish universal correctness. No production CSV or live database was changed.

## Audited extraction implementation — October 12, 2026

This section records the standards basis and corrections authorized after the
read-only review. The current file organization is described above. The older review below is retained as a record of the findings;
its old line numbers and “current behavior” descriptions refer to that earlier
snapshot. Production source is now changed. Production CSVs and the live database
have not been regenerated or updated.

### Earlier simplification after review (superseded registry layout)

This subsection records the previous simplification. The explicit-concept
implementation above replaces its runtime registry and registry-preservation test.

`selection.py` has been merged into `amount.py`; duplicate selection, rounding
and arithmetic now share one module. The old `taxonomy_metadata.json.gz` has
been removed. Its replacement, `standard_concepts.json.gz`, retains only the
standard monetary concept names, instant/duration properties and version/source
references that the code actually checks. Stored definition text and unused
balance attributes have been removed from production. The compressed file shrank
from 1,791,705 to 404,662 bytes (77% smaller).

The metric tags and accounting formulas are explicitly reviewed and coded in
the corresponding `get_*.py` metric files; the program does not interpret definition prose at runtime. Official
definitions remain in the scratch review sources for inspection. The compact
index supports additional standard concepts encountered in filed calculation
relationships. Reducing it to the four metric tags would lose existing fallback
coverage. Input parsing, shared retrieval and numeric/evidence handling remain separate
from metric-specific rules.

The simplification regression checks all 45,704 concept/version entries and all
source references against the previous index. This proves the removed fields do
not change those checks; the existing filing and accounting tests separately
check extraction behavior. All **75 tests passed**, and full results for all **22 real filings** were
identical before and after simplification. Production CSV hashes were unchanged.
Results are saved in
`scratch/unchecked_tests/implementation/simplification_tests.txt`.

### What a returned value means

The definitions remain **total liabilities / total assets** and **operating
income or loss / total interest expense**. These are project ratio definitions,
not SEC-prescribed ratios. “Debt” does not mean interest-bearing borrowings alone.
A returned ratio uses disclosed monetary point amounts, or an explicitly recorded
arithmetic derivation from them, for the same CIK, period and currency. It is
rounded to 28 significant decimal digits using round-half-even. It is not a claim
to recover undisclosed, unrounded economic amounts.

Every pipeline row records its identity and status. Available results carry
source document URLs and hashes, taxonomy version, operand values, currency,
dates, precision bounds, derivation and reconciliation checks. Missing results
retain the available source evidence and a reason. Reported operands and derived operands are
identified separately. The pipeline uses `evaluate_*` from the individual ratio modules and retains
the full result; scalar `calculate_*` functions are also available.

A missing noncurrent-liabilities fact **does not establish zero**. Reported total
liabilities can be used directly. A complete applicable standard equation can
also establish total liabilities or solve exactly one missing component from
other disclosed amounts. Neither operation assumes an omitted amount is zero.
A single arithmetic result based on rounded inputs retains its rounding bounds;
multiple rounding-compatible equations with different point results are marked
`rounding_ambiguity`, unless an independently reported equivalent total resolves
the choice. These bounds are conservative, not an exact solution of every
correlated rounding constraint in a filing.

### Corrections and current code locations

| Priority / reviewed defect | Current correction | Implementation |
|---|---|---|
| P1: units and exact values discarded | Parse SEC extracted instance text as Decimal; retain CIK, period, ISO currency and declared decimals before arithmetic. Do not convert currencies. | [src/value_retrieval/source.py:106](src/value_retrieval/source.py#L106) |
| P1: unsupported or incomplete calculations | Resolve effective filed ±1 relationships separately by role and calculation version; handle nested forward and one-unknown inverse equations; reject custom operands and missing required components. | [src/value_retrieval/get_value.py:86](src/value_retrieval/get_value.py#L86) |
| P1: liability/equity scope and reconciliation | Reconcile reviewed balance-sheet partitions with the combined total; support parent/redeemable temporary-equity split; reject known overlapping parts and contradicted parent-only equity scope. | [src/value_retrieval/get_liabilities.py:40](src/value_retrieval/get_liabilities.py#L40) |
| P1: conflicts and rounding | Same-accuracy duplicate conflicts fail; other duplicates require overlapping closed rounding intervals. Select the most precise reported amount. Conflicting equations fail instead of using the first role. | [src/value_retrieval/amount.py:129](src/value_retrieval/amount.py#L129) |
| P1: inferred values mistaken for independent checks | Record whether the checked total was used in the derivation. Reported ratio operands are checked against independently evaluable filed equations. A circular equality is not labeled independent evidence. | [src/calculations/calculate_ratio.py:20](src/calculations/calculate_ratio.py#L20) |
| P1: annual-period order heuristic | Use matching undimensioned DEI annual required-context facts and reject ambiguous starts, including conflicting DEI facts. No 350–380-day guess or first-row selection. | [src/value_retrieval/source.py:64](src/value_retrieval/source.py#L64) |
| P1: missing reasons and float conversion at storage boundaries | Persist status/evidence; validate finite Decimal values and value/status/evidence agreement; read CSV numerics as text and bind decimal strings with SQL NUMERIC casts. Reject invalid keys before opening a DB connection. | [src/database/financials_table_info.py:12](src/database/financials_table_info.py#L12) |
| P2: historical taxonomy semantics ignored | Check concept existence, monetary type and period against the filing's actual US GAAP version, using a compact monetary-concept index built from official schemas. | [src/value_retrieval/source.py:27](src/value_retrieval/source.py#L27) |

The most important additional real-structure fix was **Calculations 1.1**, used
by the saved Berkshire and Microsoft filings. The parser now accepts the 2003
and 2023 summation-item arcroles, equivalent decimal spellings of ±1 weights,
and embedded calculation links in extension schemas. Prior collection scripts
also missed some `-cal.xml` filenames; the scratch collector now captures both
hyphenated and underscored names. Real tests exercise these differences.

### Official basis and limits of each rule

| Basis | Classification and use |
|---|---|
| [SEC accepted taxonomies](https://www.sec.gov/data-research/structured-data/taxonomies-schemas/standard-taxonomies) | Official accepted taxonomy list. Acceptance does not make every concept interchangeable. The implemented registry covers US GAAP 2021–2026, not every SEC-accepted taxonomy. |
| [2026 FASB definitions](https://xbrl.fasb.org/us-gaap/2026/elts/us-gaap-doc-2026.xml) and [technical schema](https://xbrl.fasb.org/us-gaap/2026/elts/us-gaap-2026.xsd) | Official concept meaning, monetary type, instant/duration and balance attributes. Fixed partitions use the named definitions, not concept-name guesses or credit/debit classification alone. Each retrieved operand links to the version actually used. |
| [SEC XBRL Guide](https://www.sec.gov/files/edgar/xbrl-guide.pdf), §§3.1, 9.2 and required-context guidance | Required-context and entity/period rules support the DEI-based annual selection. Restricting this pipeline to original 10-Ks, one unambiguous annual start and undimensioned company facts is an implementation policy, not a claim that every permitted context has this form. |
| Same guide, §§9.8–9.10 | Unit and duplicate/accuracy requirements. Duplicate consistency is checked using declared precision. Currency cancellation is a mathematical requirement; no conversion or currency heuristic is introduced. |
| Same guide, §5.9 and §10.4 | Calculation relationships and structural validation. A filed relationship is evidence for a calculation, not proof that every possible component or every disclosure period is present. The engine requires all inputs for a forward equation, or exactly one unknown with an independently reported parent for an inverse equation. |
| Same guide, §6.8.1.10 | Permitted dash treatments include no numeric fact, nil or zero. This is **not** a general missing-equals-zero rule. Only an explicitly nil `CommitmentsAndContingencies` caption is skipped, based on its official caption definition; arbitrary nil numeric components are not zero. |
| [Calculations 1.1, corrected Recommendation](https://www.xbrl.org/Specification/calculation-1.1/REC-2023-02-22%2Bcorrected-errata-2024-02-14/calculation-1.1-REC-2023-02-22%2Bcorrected-errata-2024-02-14.html), §§4–5; [FASB 2025 technical guide](https://xbrl.fasb.org/resources/annualrelease/2025/GAAP_Financial_Reporting_Taxonomy_and_Data_Quality_Committee_Rules_Taxonomy_Technical_Guide.pdf) | Official technical basis for the newer arcrole and interval treatment. This application uses conservative rounding reconciliation for extraction; it is not a complete SEC or XBRL conformance validator. |
| [SEC staff interpretations and FAQs](https://www.sec.gov/data-research/structured-data/office-structured-disclosure-staff-observations-guidance-trends/staff-interpretations-faqs-related-interactive-data-disclosure) | Interpretations supplement the guide. Recommendations and examples are not converted into a mandatory disclosure of every amount this project's ratios need. |

The fixed fallback inventory is: assets = current + noncurrent assets; liabilities
= current + noncurrent liabilities; inclusive permanent equity = parent equity +
noncontrolling interest; inclusive temporary equity = parent temporary equity +
redeemable noncontrolling equity; interest expense = operating + nonoperating
interest expense; operating interest expense = operating interest income − net
interest income/expense; assets = the corresponding combined liabilities/equity
total; and the balance identity using both permanent and temporary equity.
**Every term is required** unless a complete filed equation supplies another
supported derivation. Temporary equity and noncontrolling interest are never
silently filled with zero. Filed equations can provide other standard-concept
routes, but custom tags remain excluded.

The former compact index has been replaced by explicit metric concept sets.
The official source material and per-version comparison are now retained only
under `scratch/unchecked_tests`; see the explicit-concept section above.
The historical `implementation/build_registry.py` writes a scratch artifact only.
The saved filings reference US GAAP 2021–2025, even where the report year is 2026.
The 2026 schema is checked and used in constructed tests, not misrepresented as
real 2026-taxonomy filing coverage. `InterestExpenseOperating` and
`InterestExpenseNonoperating` are absent from 2021–2023 and present from 2024.
Definitions for assets/liabilities, permanent equity, interest expense and debt
also differ across versions. The prior review's
`full_review/taxonomy_comparison.json` retains the per-version wording and
attributes. Historical concepts are not silently replaced with their 2026 text.

### Reproducible evidence

Run from the repository root with the project environment:

```bash
.venv/bin/python -m unittest discover -s scratch/unchecked_tests
.venv/bin/python scratch/unchecked_tests/implementation/exercise_real.py
```

The earlier implementation suite passed **74 tests**; its output is saved in
`implementation/tests_final.txt`. These commands run offline. The second writes
only scratch results. Do not run
`src/main.py` merely to reproduce this review: it is the live orchestration path.
The separate `implementation/collect_instances.py` is an optional SEC network
collector and also writes only to scratch.

* Real evidence: 22 original filings from AAPL, AMD, MSFT, WMT, BRK-B and JPM,
  checked against the saved constituent list and CIKs. The manifest identifies
  accessions, original URLs and SHA-256 hashes. The new exact-instance path
  matches all **88** metric comparisons (**76 numeric, 12 missing**) against independently decoded inline
  filing evidence from the review. The 44 hidden-liability controls are explicitly
  altered tests, not amounts the companies actually omitted.
* Available ratios in this sample: **22/22 debt/assets**, **11/22 interest
  coverage**. Missing interest coverage is retained, not filled using net
  interest, custom tags, cash interest, or nonoperating interest alone.
  `implementation/real_results.json` contains full source and derivation evidence.
* Constructed regressions cover incompatible currency, duplicate conflicts,
  exact large amounts, precision bounds, nested/inverse equations, nil captions,
  prohibited arcs, custom-schema impersonation, entity/dimension scope,
  annual-context ambiguity, temporary equity, equation order and reconciliation.
  Passing these controls does not establish that every permitted structure is
  covered.
* Database tests use isolated SQLite for transactional upserts and NULL/status
  preservation, and capture exact string binds before database conversion.
  SQLite is **not** evidence of PostgreSQL NUMERIC precision. PostgreSQL migration,
  view execution and consumer integration have not been run here. SQL views were
  reviewed: they retain latest-period missing values, expose audit columns and
  withhold legacy/unavailable values from ratios and ranks.
* The checkpoint test mocks SEC access and writes beneath a temporary test
  directory under `scratch/unchecked_tests/implementation`. It confirms that an interrupted run preserves the completed CSV.
  No live database connection or live full-pipeline run is part of this work.

### Storage compatibility and remaining assessment

New CSV rows include CIK, accession, fiscal start, each ratio's status and JSON
extraction evidence. The loader rejects old CSVs lacking these fields; it cannot
retroactively prove an old number's origin. On a future authorized run, schema
migration adds audit columns and marks existing rows `legacy_unverified` without
erasing their stored numbers. Updated views expose only `available` ratios for
ranking/display and append the audit columns. A ticker/period collision with a
different recorded CIK aborts the financial transaction.

**Confirmed defects corrected:** the currency/precision loss, silent ambiguous
selection, demonstrated nested/inverse and Calculations 1.1 omissions, tested
liability/equity partitions, annual-order heuristic, lack of independent
reconciliation, and missing-state loss described above. Tests and actual-filing
evidence substantiate these specific corrections.

**Remaining coverage gaps / unverified behavior:** US GAAP versions outside
2021–2026, other accepted taxonomies, valid dimension-based consolidation routes,
other standard liability partitions beyond the reviewed branch set, more general
systems with multiple unknowns, and arbitrary imported DTS arrangements are not
fully supported. Explicit referenced calculation documents that are absent from
the supplied attachments disable filed-equation use instead of allowing a partial
sum. This is a pipeline gap, not proof that the filing lacks the amount. The
parser is not a full DTS/SEC validator. Broader issuer/industry sampling and actual
PostgreSQL migration/view tests remain necessary. Depth and numeric-size limits
are explicit implementation limits, not SEC rules.

**Intentional exclusions:** custom monetary concepts, genuinely noncompliant
structures, currency conversion, amendments/restatement selection beyond the
chosen original filings, alternative definitions of the ratios, and assumptions
that omitted components are zero.

**Unavoidable information limits:** a compliant filing may not disclose enough
standard-concept information for a defined ratio. Rounded facts do not identify
unique unrounded amounts. Zero denominators do not define finite ratios. These
cases retain missing statuses or explicit precision bounds; documented convention
cannot supply information the filing does not establish.

The supported claim is that returned results have a traceable standard-concept
basis under the stated extraction and rounding policies, supported by these tests
and review. It is not a universal correctness or completeness guarantee.

## Earlier project notes (historical)

The end goal is a reproducible **SEC EDGAR → Python → CSV → PostgreSQL → Tableau**
workflow for comparing financial risk across S&P 500 companies and fiscal years.
The company list comes from Wikipedia's current S&P 500 constituents table.

| Capability | Status |
|---|---|
| Current constituent list, CIKs, company names, and sectors | Implemented |
| Up to five distinct annual reporting periods per listed ticker | Implemented |
| Debt-to-assets and interest-coverage extraction/calculation | Implemented |
| CSV inspection, progress summaries, and partial extraction checkpoints | Implemented |
| Transactional database upserts and latest-period sector rankings | Implemented |
| Further SQL analysis and interpretation of findings | Next analysis work |
| Tableau dashboards and visual comparisons | Planned |
| Current ratio | Longer-term goal; not implemented |

The project favors explicit, readable modules and supported accounting definitions
over maximizing the number of populated cells. A missing value is an acceptable
result when the required disclosed amounts cannot be obtained.

## Metrics

| Metric | Definition used here | Primary US GAAP concepts |
|---|---|---|
| Debt to assets / leverage | Total liabilities ÷ total assets | `Liabilities`, `Assets` |
| Interest coverage | Operating income or loss ÷ total interest expense | `OperatingIncomeLoss`, `InterestExpense` |

All concept names above use the `us-gaap:` prefix. “Debt” in this project's ratio
means **total liabilities**, not just interest-bearing debt. Operating income is
not silently replaced with EBITDA or a differently defined EBIT. Net interest,
cash interest paid, and nonoperating interest alone are not substitutes for the
defined total interest expense.

## Architecture

```text
src/
├── main.py                      Orchestrates and times six pipeline stages
├── setup_sec_identity.py         Configures EdgarTools SEC identity
├── wiki_pull.py                  Retrieves current constituent metadata
├── table_data/
│   ├── company_status.py         Produces the companies CSV
│   ├── generate_ratios.py        Selects filings and produces the ratios CSV
│   └── checks.py                 Validates and summarizes table inputs
├── value_retrieval/
│   ├── get_value.py              Exact fact lookup and filed calculation sums
│   ├── selection.py              Duplicate accuracy, equation agreement, selection errors
│   ├── get_assets.py             Asset retrieval and approved fallbacks
│   ├── get_liabilities.py        Liability retrieval and approved fallbacks
│   ├── get_equity.py             Permanent and temporary equity components
│   ├── get_operating_income.py   Operating-income retrieval
│   └── get_interest_expense.py   Interest-expense retrieval and fallbacks
├── calculations/                Divides retrieved amounts into the two ratios
└── database/                    Schema, CSV loaders, and SQL view definitions
```

The amount modules retrieve financial amounts. The calculation modules combine
those amounts into ratios. Table-data modules assemble rows; database modules
load them. CSVs are a persistent handoff, not a requirement for module separation.

Neither assets nor liabilities is always the starting amount. Each has a
`*_before_equity()` function that can retrieve it without relying on the other
retrieval function's equity identity. The final asset/liability identities use
those independent paths to avoid circular reconstruction.

## Filing and fact selection

1. Use the CIK supplied by the constituent list to retrieve original `10-K`
   filings with `amendments=False`.
2. Skip filings without a reporting date and repeated reporting-period dates.
   Select at most five distinct periods in the order returned by EdgarTools.
   Companies with fewer qualifying filings produce fewer rows; no dates or
   placeholder histories are invented.
3. Parse each selected filing once. Find its annual duration ending on the
   selected reporting date and use the actual start date from the filing.
   Do not assume every fiscal year starts January 1 or lasts exactly 365 days.
4. Retrieve exact standard concepts and apply the date and scope rules below.

### Data-validation philosophy

- **Meaning before label:** concepts and component classifications were reviewed
  against official FASB US GAAP definitions. Similar text, concept-name substrings,
  custom company tags, or automatic library aliases are not sufficient evidence.
  The code uses reviewed names; it does not download taxonomy definitions at runtime.
- **Exact lookup:** `by_concept(..., exact=True)` requests the full concept name.
  `normalize_concept_name()` converts schema identifiers such as `us-gaap_Assets`
  to the qualified-name spelling `us-gaap:Assets`; it does not validate a definition.
- **Company identity:** retrieval trusts the CIK used to select the filing. There
  is no additional per-fact entity-identifier comparison.
- **Consolidated scope:** dimensioned facts are excluded. A segment amount is not
  substituted for the company's consolidated amount.
- **Period type:** assets, liabilities, and equity are instant amounts and match
  the requested date. Income and expense are duration amounts and must match
  both requested dates. `get_duration_value()` requires both dates; annual-period
  selection happens in `generate_ratios.py`, not in that helper.
- **Missing is not zero:** absent or nonnumeric required components remain missing.
  Explicit zero and negative operating income are preserved. A zero denominator
  returns `None`; it does not produce an infinite ratio.
- **Consistent components:** the same concept, date, scope, and numeric-value rules
  apply to fallback components. Reporting currency consistency within a filing is
  assumed across separately retrieved components. Duplicate candidates must have
  the same nonempty unit identifier before their values can be compared.
- **No fabricated precision:** calculations use the disclosed numeric amounts.
  They do not recover unreported ledger precision or implement interval arithmetic.

Python `None` becomes an empty ratio field in CSV and SQL `NULL` when loaded.
Neither missing ratios nor negative values are automatically treated as errors.

## Retrieval and fallback order

`get_reported_value()` searches the concept, filters dates and scope, drops missing
numeric values, and resolves consistent duplicates using their declared precision.
Equal numeric amounts need no precision tie breaker; differing amounts require
valid decimals metadata and the SEC rounding-consistency checks. `get_value()` tries that
reported amount first, then `get_calculated_value()`. `get_instant_value()` and
`get_duration_value()` make the time basis explicit to the individual amount modules.

### General calculation helper

For each calculation network separately, find arcs whose parent is the requested
concept. Retrieve every immediate child's reported amount and sum `weight × value`.
A missing or nonstandard required child rejects that equation. Every eligible
complete equation is evaluated. They must yield the same amount; otherwise a
`SelectionError` prevents later fallbacks from treating conflicting evidence as
absence. Signed weights are preserved, and sums use Decimal arithmetic before
returning the numeric result.

Both the general helper and special liability route reject a combined-total
equation using parent-only equity when separately reported noncontrolling equity
is nonzero and neither the minority branch nor inclusive-equity branch is present.
This addresses the demonstrated Berkshire scope mismatch in both asset and
liability recovery. Missing minority equity is not inferred to be zero.

This helper does not recursively calculate missing children, mix roles, rearrange
arbitrary equations, or add descendants on top of a reported subtotal. When an
approved fixed formula requests a component, that component can use its own
reported-then-calculation lookup.

### Assets, liabilities, and equity

Assets try, in order:

1. `Assets`, reported or calculated.
2. `AssetsCurrent + AssetsNoncurrent`, requiring both.
3. `LiabilitiesAndStockholdersEquity`, reported or calculated.
4. Independently retrieved liabilities + permanent consolidated equity + total
   temporary equity, requiring every component.

Liabilities try, in order:

1. `Liabilities`, reported or calculated.
2. The special combined liabilities-and-equity equation described below.
3. `LiabilitiesCurrent + LiabilitiesNoncurrent`, requiring both.
4. Independently retrieved assets − permanent consolidated equity − total
   temporary equity, requiring every component.

Permanent equity uses `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest`,
or `StockholdersEquity + MinorityInterest` when both components are available.
Total temporary equity uses
`TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests`.
A missing minority-interest or temporary-equity fact is not inferred to be zero.

### Special combined-equation liability fallback

This route requires a **reported** `LiabilitiesAndStockholdersEquity` amount. It
examines that parent's immediate children in each calculation network, accepting
only `+1` weights and the reviewed liability/equity categories defined in
`get_liabilities.py`. The category sets classify actual filed branches; they are
not a fixed list of amounts to sum for every company.

If the equation contains the missing `Liabilities` total as a child, solve for it
by subtracting the other monetary branches from the combined total. Otherwise,
sum the declared liability branches. All eligible equation results must agree.
Both liability and equity categories must
be present, and all required monetary amounts must be obtainable.

The exact `CommitmentsAndContingencies` child can be skipped only when matching
undimensioned instant facts exist and are blank and nonnumeric. This is treatment
of a caption, not a claim that commitments equal zero. An absent caption, numeric
caption, or another missing monetary component does not qualify for that exception.

**Presentation trees are not used.** The previous requirement that a corresponding
presentation contain `Assets` and the combined total, and the caption's presentation
membership requirement, have been removed. Eligibility now rests on the calculation
relationships, reviewed categories, weights, and matching facts. This broadens
eligible networks; it is not proof that every complete equation is appropriate.
Historical snapshots retain their original presentation data, but tests and
production extraction do not need it.

### Operating income and interest expense

Operating income uses `OperatingIncomeLoss`, reported or calculated. There is no
universal `GrossProfit − OperatingExpenses` fallback.

Interest expense uses `InterestExpense`, reported or calculated. If unavailable,
try `InterestExpenseOperating + InterestExpenseNonoperating`, requiring both.
The operating component may be derived as
`InterestIncomeOperating − InterestIncomeExpenseNet` when both are present,
preserving the net amount's sign. Do not add potentially overlapping lease interest
or replace the total with cash interest, net interest, or only the nonoperating part.

## Tests behind the structural decisions

Tests remain in `scratch/unchecked_tests`: “unchecked” means not personally reviewed
by the project owner. Assistant execution is not equivalent to that review.
Scratch contains executable investigations, fixtures, and result data; explanatory
notes belong in this README. Tests demonstrate specific behavior, not universal accuracy.

| Test / investigation | Evidence and resulting decision |
|---|---|
| `test_calculation_fallbacks.py` — direct precedence and zero | A reported zero wins over a reconstructable total; distinguish zero from missing. |
| Same file — weighted sum and descendants | Signed child weights matter; do not double-count a subtotal and its descendants. |
| Same file — scope, date, custom concepts, separate networks | Reject mismatched components and incomplete equations; never combine children from different roles. |
| Same file — duration matching | A matching end date alone is insufficient; annual income/expense components must match the start date too. |
| Same file — equity and interest formulas | Require permanent/minority/temporary components as applicable and both interest parts; preserve net-interest sign. |
| `test_filing_ratios.py` — saved filings and hidden controls | Exercises 22 snapshots: five each AMD/AAPL/MSFT/WMT and one each JPM/BRK-B. Reconstructs ten AMD/WMT liability totals and checks reconstruction against twelve available totals hidden from the lookup. |
| Same file — branch and caption rejection | Missing equity/liability/caption facts, numeric captions, custom/unknown branches, and wrong scope/date must not silently become zero. |
| Same file — current-only equation | Current liabilities alone establish a total only through an actual complete filed equation, not by assuming missing noncurrent liabilities are zero. |
| Same file — no presentation dependency | AMD/WMT combined-equation recovery runs with no `presentation_trees` attribute; weights, reported combined total, and required categories still constrain it. |
| Same file — ratio edge cases | Zero denominators yield missing ratios; negative operating income remains negative; missing annual starts prevent duration retrieval. |
| `test_database_load.py` | In-memory SQLite checks repeated upserts and replacing an old numeric ratio with NULL, rather than retaining stale values. It does not validate a live Neon deployment. |
| `test_pipeline_checkpoints.py` | Reject invalid CSV keys/dates; permit missing ratios; an interrupted extraction preserves the previous completed CSV and saves completed-company rows separately. |
| `extraction_audit/check_guarantee.py` | 47 complete parent equations matched saved reported amounts: 20 assets, 10 liabilities, 17 operating income; no qualifying total-interest equation. Includes missing-subtotal, net-interest, and rounding counterexamples. |
| `test_amd_liabilities.py` | Separate live case study checks AMD's raw nil-caption markup and reconciles liability components against the combined total. Production checks parsed blanks, not raw markup for every filing. |
| `extraction_audit/sec_crosscheck.py` | Historical SEC CompanyFacts comparison matched 34 available direct asset/liability amounts by accession and end date. This compares two extraction paths over the same filings. |

Verification after removing presentation dependencies (October 12, 2026): **19
offline tests passed**. All 44 before/after comparisons matched across the 22 saved
filings and their hidden-liability variants (assets, liabilities, and interest
coverage). This is sample compatibility evidence; no full-universe extraction or
live database load was run for this change.

Specific findings that informed the rules:

- AMD 2025 had no matching noncurrent-liability subtotal but had $4.472 billion of
  reviewed noncurrent components. Missing subtotal does not mean zero.
- Walmart 2026 had $293 million of redeemable noncontrolling equity. Subtracting
  only permanent equity overstates liabilities by that amount.
- The 20-row AMD/AAPL/MSFT/WMT pilot has interest coverage for 11 rows under the
  approved concepts. Missing gross interest cannot be filled using a different measure.
- Two pairs of gross interest expense/income can produce the same net expense;
  the net figure alone does not determine gross expense.
- Rounded components need not identify a uniquely rounded total. Reconstruction
  is from disclosed amounts, not a guarantee of hidden ledger precision.

`filing_fixtures.py` loads the saved facts and calculation relationships.
`extraction_audit/audit.py` collects snapshots, and `analyze.py` supports the older
comparison scripts. Historical JSONs and reviewed taxonomy definitions are evidence,
not additional tests. Root scratch scripts inspect library totals, concept-prefix
behavior, reporting dates, and filing availability. These probes are distinct from
automated regression assertions. `scratch/financial_ratios_pilot.csv` is historical;
production uses `data/financial_ratios.csv`.

## Selection behavior and remaining limits

The two demonstrated selection defects are integrated into production:

- **Duplicate facts:** `selection.py` checks matching unit identifiers and resolves
  differing numeric amounts using SEC section 9.10. Consistent duplicates return
  the most precise disclosed amount. Missing accuracy on differing amounts,
  inconsistent values, mixed units, and nonfinite amounts raise `SelectionError`.
- **Calculation equations:** the Berkshire parent-only equity network is rejected
  in both reconstruction routes. All remaining complete equations must agree;
  differing amounts produce `SelectionError`, including differences that might
  be due to rounding when no unique disclosed result establishes which to use.
- **Conflict propagation:** retrieval helpers let `SelectionError` propagate
  through every fallback. Each ratio catches it once, prints the reason, and
  returns `None`. The other ratio can still succeed. Extraction prints ticker,
  CIK, and period before retrieval, so diagnostics can be attributed to a row.

These are deliberately conservative selection rules, not a universal accounting
certification. No independent reconciliation requirement has been added to the
liability-component sum: the audit found no real failure among ten such cases.
Cross-component reporting currency remains an assumption supported by the sample;
no currency conversion is performed. Custom concepts, incomplete components,
missing original 10-Ks, and predecessor/CIK histories can leave gaps. The current
constituent list and sectors apply to history; this is not a historical-membership
dataset. Calculations cannot recover undisclosed precision.

## Duplicate precision and targeted equation experiments

These experiments supplied the evidence for the production integration described
above. Scratch retains raw evidence, independent numeric checks, and production
regression tests. The interval-reconciliation experiment remains scratch-only.

`collect_duplicate_precision.py` retrieves the original Apple 2021 Inline XBRL
and records source amounts, scale, decimals, context, and unit in
`duplicate_precision_evidence.json`. Its deliberately limited scope is 183
undimensioned standard numeric tags for the current instant/annual period using
the num-dot-decimal transform. There are 17 duplicate groups, two with differing
numeric amounts:

| Concept | Coarser amount (`decimals=-8`) | More precise amount (`decimals=-6`) |
|---|---:|---:|
| UnrecognizedTaxBenefits | 15,500,000,000 | 15,477,000,000 |
| DebtInstrumentCarryingAmount | 118,100,000,000 | 118,063,000,000 |

SEC XBRL Guide section 9.10 requires numeric duplicates to be consistent with
rounding from one value and consolidates consistent duplicates using the greatest
declared decimals. Equal decimals require equal amounts; differing decimals use
intersecting closed rounding intervals. This selects disclosed precision, not
unknown ledger precision. Sources:
[SEC Guide](https://www.sec.gov/files/edgar/xbrl-guide.pdf) and
[XBRL duplicate-fact guidance](https://www.xbrl.org/WGN/xbrl-duplicates/WGN-2025-01-14/xbrl-duplicates-2025-01-14.html).

`test_duplicate_precision.py` verifies every ordering of all 17 duplicate groups,
rejects inconsistent amounts, missing accuracy, and mixed units, and checks exact
values, negatives, zero, and interval boundaries. It also demonstrates that the
installed EdgarTools deduplicator preserves differing precision. EdgarTools already
exposes decimals in its default fact frame. The prototype requires identical
context/unit IDs; a general implementation must establish equivalent fact scope
and units before ranking candidates. Unresolvable conflicts should be diagnosed,
not silently selected or hidden by an automatic calculation fallback.

`test_equation_selection.py` now tests production rejection of combined-total equations
that subtract parent-only equity while omitting separately reported nonzero
noncontrolling equity. This makes the Berkshire missing-liability experiment return
502.473 billion even with the condensed equation first. The inclusive-equity
equation is retained, so noncontrolling equity is not subtracted twice. The filter
preserves 44 baseline results across 22 snapshots with and without direct
liabilities. This is a targeted remedy, not a complete equation applicability
validator; missing noncontrolling equity is not treated as proof of zero.

## Selection-gap audit (October 12, 2026)

This section records the investigation that preceded integration. Evidence and executable
checks are in `scratch/unchecked_tests/selection_audit/` and
`test_selection_audit.py`. No production CSV or database was regenerated.
At that investigation stage, 35 offline tests passed. The integration converts the
equation characterization cases into production regression assertions.

All real-company cases are AMD, Apple, Microsoft, Walmart, JPMorgan Chase, and
Berkshire Hathaway Class B. The 22 saved filings' ticker/CIK pairs are checked
against the project's constituent list. S&P's own
[sector comparison](https://www.spglobal.com/spdji/en/documents/additional-material/brochure-side-by-side-sectors.pdf)
and [constituent report](https://www.spglobal.com/content/dam/spglobal/mi/en/documents/products/SP%20500%20DIPs%20Report%202025.pdf)
provide independent membership evidence. This is a six-company sample, not an
audit of all S&P 500 constituents or historical index membership.

The collector refreshed original SEC tags for the latest saved filing of each
company: 2,044 undimensioned numeric occurrences at the selected instant/annual
period, including 211 duplicate groups. It records original unit definitions and
decimals. It explicitly excludes unsupported `numwordsen` transforms (18
occurrences across the six filings); these are not counted as validated facts.
The older 22 snapshots are used for broader equation comparisons, without
claiming they contain precision metadata they never captured.

| Proposed gap | Observed evidence | Decision supported by the investigation |
|---|---|---|
| Currency mismatch | No mixed-unit concept group in the six raw samples; available pipeline target concepts resolve to ISO 4217 USD. | No demonstrated currency defect in these results. Unit equality belongs in duplicate comparison; an elaborate currency-conversion fallback is unwarranted. |
| Conflicting equations | 129 complete general equations across all explicitly requested standard targets; only Berkshire's combined-total target produced conflicting role results. | The known fix must cover the shared calculation helper, not only the special liability function. Do not choose unresolved alternatives by iteration order. |
| Liability branch reconciliation | All ten AMD/Walmart branch-sum cases reconcile exactly. Berkshire's condensed equation has a 2.284 billion residual against reported consolidated amounts. | No newly observed branch-sum error. Reconciliation can detect contradictions when independent disclosed totals exist. |
| Duplicate accuracy | All 211 raw duplicate groups pass SEC numeric consistency criteria; the previous Apple 2021 example demonstrates why choosing the most precise matters. | Implement the already tested accuracy policy; equal-value duplicate occurrences do not create numerical ambiguity. |

The additional Berkshire asset test withholds both direct Assets and the combined
total. Before integration, reversing roles changed reconstructed assets from 1,222.176
billion to 1,219.892 billion. Production now returns 1,222.176 billion in either
order by rejecting the parent-only equity equation. This is the same underlying
equity-scope problem, not evidence of a second unrelated filing defect.

The reconciliation control changes an AMD liability component by 1 billion.
Production accepts the altered sum; the experimental check rejects it. A separate
1-million change compatible with the disclosed rounding is accepted. These are
deliberately altered controls, not claims that AMD filed those amounts. Comparing
a reconstructed value to the very equation used to construct it is circular;
reconciliation needs an independently available amount to add evidence.

Official standards used to resolve ambiguity:

- [SEC XBRL Guide](https://www.sec.gov/files/edgar/xbrl-guide.pdf), sections 5.9.3,
  6.6, 9.8, and 9.10: alternate role equations are permitted; currency scale must
  be normalized; units must fit concept types; numeric duplicates must be
  consistent and the most precise is retained. Section 9.10 expressly says
  calculation inconsistencies do not invalidate an EDGAR submission. Acceptance
  therefore does not certify every equation for every selected set of facts.
- [XBRL Calculations 1.1, sections 5.2–5.5](https://www.xbrl.org/Specification/calculation-1.1/REC-2023-02-22%2Bcorrected-errata-2024-02-14/calculation-1.1-REC-2023-02-22%2Bcorrected-errata-2024-02-14.html)
  supplies the interval arithmetic used in the experimental rounding check.
  The experiment uses round-to-nearest and positive-weight combined equations;
  it is not a complete implementation of this specification or an assertion
  that SEC mandates this particular implementation.

### Policy comparison after integration

| Established policy | Current production assessment |
|---|---|
| Reviewed concept meanings, exact searches, trusted filing CIK | Implemented. No new defect established. |
| Undimensioned scope, exact instant or full duration dates | Implemented, including the documented Berkshire correction; universal role applicability is not claimed. |
| Missing is not zero; preserve explicit zero/negative values | Implemented, including required formula components and zero-denominator handling. |
| Immediate children, signed weights, separate networks | Implemented. Complete candidate equations must agree; conflicts cannot trigger further fallbacks. |
| Deterministic supported numeric selection | Implemented: compatible duplicate units, SEC accuracy selection, and explicit conflict propagation. |
| Consistent component currency | Documented assumption, supported in the sample; not a universal guarantee or a demonstrated sample defect. |
| Do not invent precision | Implemented as arithmetic on disclosed amounts. Rounded inputs cannot recover an undisclosed exact total. |
| Missing values remain missing through CSV/database/views | Existing regression checks pass; no live database changes made. |

The two demonstrated production defects are now corrected. Missing
components/custom concepts, uncertainty below disclosed precision, and genuinely
unresolved conflicting evidence remain limits to coverage. Conflicts now produce
an explained missing ratio rather than an invented amount. No additional real
currency or branch-sum failure was established by the investigation.

The production regression suite additionally checks original Apple duplicates,
refreshed standard duplicate groups from all six companies in both row orders,
conflicting reported values that could otherwise fall through to calculations,
conflicting general/special equations, and isolation between the two ratios.
The broad historical equation audit now records 13 unresolved child lookups due
to missing decimals in old snapshots and evaluates 116 complete equations. This
replaces the earlier first-row-based count of 129; it does not establish new errors
in the original filings. All 22 saved ratio cases and 44 normal/hidden-liability
comparisons remain covered. No live extraction or database load was run.
Final integration verification: **44 offline tests passed**. The saved ratio
regressions, both Berkshire fallback orders, and conflict-propagation checks pass.

## CSVs, checkpoints, and database behavior

`data/company_status.csv` contains ticker, CIK, company name, and sector.
`data/financial_ratios.csv` contains ticker, fiscal-period end, and both ratios.
They allow inspection and a separate database retry without another SEC extraction.
Running `main.py` still repeats extraction; it has no automatic skip/resume mode.

After each completed company, extraction atomically replaces
`data/financial_ratios.partial.csv`. A new run starts that checkpoint fresh.
The database loader never reads the partial file. The completed ratios CSV is
replaced atomically only after extraction finishes and validation succeeds.
A failure leaves the previous completed CSV intact; partial rows do not
currently provide automatic restart/resume.

Messages identify stages, selected periods, skipped filings, missing financials
or annual starts, ratio availability, row counts, ranges, and committed writes.
CSV validation rejects duplicate keys, invalid dates, and missing required company
fields. The financial loader reports and drops rows missing key fields before
validating the remaining rows. These diagnostics aid inspection, not accounting certification.

Database tables:

- `companies`: ticker primary key, name, sector, current-constituent flag. A load
  marks existing entries noncurrent, then upserts the supplied constituents in
  one transaction and verifies the current count.
- `financials`: ticker foreign key, fiscal-period end, and both numeric ratios;
  primary key `(ticker, fiscal_period_end)`. Upserts replace existing ratios,
  including replacing numbers with NULL. Historical rows not in the CSV remain.

The ordinary views `sector_leverage_rankings` and `sector_interest_coverage_rankings`
use each ticker's latest financial row and retain every current constituent with
a left join. Higher values rank first within the sector, ties use `RANK`, and a
missing ratio receives no rank. Higher leverage is not a universal “better company”
score. A missing latest metric stays missing; the views do not substitute an older
nonmissing metric. Both view definitions are updated in one transaction and their
row counts are checked against current membership.

## Setup and execution

Run commands from the repository root; CSV and SQL paths are relative. The existing
local environment uses Python 3.13. Dependencies are pinned in `requirements.txt`.
For a fresh environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Provide these variables in a local, uncommitted `.env` file:

```dotenv
SEC_user_agent="Your name your-email@example.com"
db_connection_string="postgresql+psycopg2://USER:PASSWORD@HOST/DATABASE?sslmode=require"
```

Offline regression tests and saved-equation comparisons:

```sh
.venv/bin/python -B -m unittest discover -s scratch/unchecked_tests
.venv/bin/python -B scratch/unchecked_tests/extraction_audit/check_guarantee.py
```

Refresh constituent data or ratios separately (network access; writes CSVs):

```sh
PYTHONPATH=src .venv/bin/python -m table_data.company_status
PYTHONPATH=src .venv/bin/python -m table_data.generate_ratios
```

Run the full pipeline (network access, CSV replacement, and database writes):

```sh
.venv/bin/python src/main.py
```

Load existing completed CSVs without repeating SEC extraction (database writes):

```sh
PYTHONPATH=src .venv/bin/python -c 'from database.create_tables import create_tables; from database.companies_table_info import companies_table_info; from database.financials_table_info import financials_table_info; from database.refresh_view import refresh_view; create_tables(); companies_table_info(); financials_table_info(); refresh_view()'
```

Live investigations are separate from offline discovery:

```sh
.venv/bin/python -B scratch/unchecked_tests/test_amd_liabilities.py
.venv/bin/python -B scratch/unchecked_tests/extraction_audit/sec_crosscheck.py
.venv/bin/python -B scratch/unchecked_tests/inspect_calculations_network.py
```

The first checks raw AMD disclosures; the second refreshes the saved SEC comparison;
the third prints calculation-network evidence. None loads production database rows.

## Definition and evidence references

The reviewed taxonomy definitions are preserved in
`scratch/unchecked_tests/extraction_audit/reviewed_definitions.json`.
Sources used in the original investigations include:

- [FASB 2026 US GAAP concept documentation](https://xbrl.fasb.org/us-gaap/2026/elts/us-gaap-doc-2026.xml).
- [SEC staff XBRL Guide, January 2026](https://www.sec.gov/files/edgar/filer-information/specifications/xbrl-guide-2026-01-16.pdf), sections 6.7.11 and 6.8.1.10, for the nil/blank/zero distinction and caption convention.
- [SEC EDGAR API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).
- [AMD 2025 filing](https://ir.amd.com/financial-information/sec-filings/content/0000002488-26-000018/amd-20251227.htm).
- [Walmart 2026 filing](https://www.sec.gov/Archives/edgar/data/104169/000010416926000055/wmt-20260131.htm).

## Whole-project standards review — October 12, 2026

**Review complete; no production changes integrated by this review.** This section
supersedes the earlier audit's broad statements that selection is solved or that
all remaining missing results are information limits. The checkout already
contained production modifications when this review began; they were reviewed as
found and preserved. Priority P1 means possible incorrect numeric results; P2
means material coverage, selection, or auditability gaps; P3 means lower-impact
numeric/validation limitations. A confirmed implementation gap does not mean a
real company in the sample exhibited it.

The defined metrics remain **total liabilities / total assets** and **operating
income or loss / total interest expense**. Neither ratio is itself a mandated SEC
metric. The scope excludes custom **concepts and members requiring interpretation**
and genuine departures from standards. Filer-defined calculation roles joining
standard concepts are normal permitted structures, not excluded custom tags.

### Evidence, reproducibility, and boundaries

New material is in `scratch/unchecked_tests/full_review/` and
`test_full_project_review.py`. Explanatory conclusions are here. Run from the
repository root:

```sh
# Offline; includes the existing isolated SQLite/mocked-pipeline tests.
.venv/bin/python -B -m unittest discover -s scratch/unchecked_tests
# Offline independent decoding of the downloaded original SEC documents.
.venv/bin/python -B scratch/unchecked_tests/full_review/audit_raw_filings.py
# Offline concept definitions and technical attributes by taxonomy version.
.venv/bin/python -B scratch/unchecked_tests/full_review/compare_taxonomies.py
# Optional read-only official-source retrieval; writes only this scratch folder.
.venv/bin/python -B scratch/unchecked_tests/full_review/collect_sources.py
```

The collector requires the existing SEC identity setting, caches source documents,
and saves source URLs and SHA-256 hashes in `source_manifest.json`. Delete a
specific scratch source copy only if intentionally refreshing it. It does not call
the production extractor or database. `baseline_hashes.json` and
`preservation_check.json` document preservation of production code and CSVs.

- **59 offline tests pass**, including 15 new characterization tests. Several new
  assertions deliberately confirm undesirable current behavior; a pass is evidence
  that a gap is reproducible, not that the behavior is correct. No test changes
  production logic. Mocked extraction tests use isolated temporary directories.
- **22 original SEC filings**, five each AAPL/AMD/MSFT/WMT and one each JPM/BRK-B,
  were downloaded afresh. Their actual namespace and schema references are in
  `filing_versions.json`. Ticker/CIK pairs match `data/company_status.csv`.
  [S&P's sector constituent comparison](https://www.spglobal.com/spdji/en/documents/additional-material/brochure-side-by-side-sectors.pdf)
  and [S&P's 2025 constituent report](https://www.spglobal.com/content/dam/spglobal/mi/en/documents/products/SP%20500%20DIPs%20Report%202025.pdf)
  support selection of these S&P 500 companies. These publications are dated
  membership evidence, not proof of membership on every historical filing date
  or an independently refreshed October 2026 universe.
- Fresh Inline XBRL decoding reproduces **88/88 metric results**, including missing
  results, against the historical snapshots. **66 direct amounts** match separately
  decoded original facts. The raw decoder retains decimals, entity and unit
  metadata; it decoded 14,136 selected standard numeric/nil occurrences and
  explicitly skipped 34 `numwordsen` occurrences. Those skips are coverage limits. It does not
  independently reparse the calculation linkbases: derived results reuse saved
  relationships. Consequently those results are compatibility checks, not an
  independent certification of the dependency's relationship parser.
- The existing ten real AMD/Walmart liability sums reconcile against reported
  balance-sheet totals. The new Walmart 2026 check gives
  **284.668 − 105.887 − 0.293 = 178.488 billion USD**. Temporary equity matters.
  Independent reported totals add evidence; re-summing the same components does not.
- Apple 2021's original differing-precision duplicates remain covered by the
  existing tests. Berkshire's historical condensed-role discrepancy remains a
  diagnostic example; SEC acceptance does not establish that a mismatching
  equation is a compliant consolidated equation. It is **not** counted here as
  a new in-scope filing defect.
- No live pipeline, production CSV replacement, or live database operation was
  performed. SQLite tests establish limited loader behavior, not PostgreSQL view
  execution, deployed schema correctness, permissions, or transactions in Neon.

### Official basis and strength of requirements

Sources used for accounting meaning and structural conclusions are official:

1. [SEC accepted taxonomy index](https://www.sec.gov/data-research/structured-data/taxonomies-schemas/standard-taxonomies)
   and its [operating-company releases](https://www.sec.gov/data-research/structured-data/taxonomies-schemas/standard-taxonomies/operating-companies).
   Acceptance is version-specific; a current list does not retroactively prohibit
   a taxonomy used in an older filing. Accepted families are not interchangeable
   accounting definitions. This implementation specifically maps US GAAP metrics.
2. [FASB 2026 definitions](https://xbrl.fasb.org/us-gaap/2026/elts/us-gaap-doc-2026.xml)
   and [technical schema](https://xbrl.fasb.org/us-gaap/2026/elts/us-gaap-2026.xsd).
   `taxonomy_comparison.json` preserves all **25 explicitly named production
   concepts**, plus six alternative concepts examined, for 2021–2026. Every named
   2026 production concept is monetary; the six income/interest concepts are
   duration, the other nineteen instant. Balance attributes do not require positive
   values. A name/prefix alone is not a definition or proof of a namespace version.
3. [SEC XBRL Guide, August 2026](https://www.sec.gov/files/edgar/xbrl-guide.pdf),
   archived locally with hash. Relevant sections: **3.1.2, 5.9–5.9.3, 6.2–6.3,
   6.5–6.8, 7.5, 8.7, 9.7–9.10, 10.4**. These cover required contexts, calculation
   alternatives, entity/period scope, units, accuracy, captions, and relationships.
4. [SEC staff interpretations and FAQs](https://www.sec.gov/data-research/structured-data/office-structured-disclosure-staff-observations-guidance-trends/staff-interpretations-faqs-related-interactive-data-disclosure),
   especially **D.4–D.8, E.3, E.11, E.16–E.18, E.24–E.27, F.4**.
   Standard-taxonomy exceptions, transition reports, dimensions, and tagging of
   disclosed zero amounts are relevant. These are staff interpretations, not new
   requirements that every ratio component must be disclosed.

| Classification | Review interpretation |
|---|---|
| Mandatory validation/filing rules | Applicable concept types/periods, numeric units, consistent numeric duplicates, and required relationships must satisfy the cited SEC rules. Extension calculation weights are +1 or −1. Equal-accuracy duplicate amounts must agree. |
| Recommendations | SEC encouragement to use the latest accepted version and pre-defined tables/axes is encouragement, not a prohibition of every permitted alternative. |
| Permitted structures | Different calculation roles, nested standard relationships, disclosed amounts in different currencies, and eligible non-12-month reporting contexts require semantic selection. They are not automatically corrupt data. |
| Implementation assumptions | First matching “Annual” period, only undimensioned facts, US GAAP prefix recognition, common currency across separately retrieved values, exact equality of derived sums, one-level forward calculations, and a limited liability whitelist are application choices. |
| Information limits | A missing amount is not zero. A net amount need not identify its gross components. Rounding may leave an interval rather than a unique total. No SEC rule guarantees enough disclosed data to calculate these ratios. |

For duplicate units specifically: the Guide forbids equivalent unit declarations
under different IDs within a compliant instance (§9.8). Thus a constructed
same-currency/two-unit-ID example alone would **not** establish an in-scope SEC
pipeline defect. Distinct currencies, however, are distinct units, not inconsistent
duplicates. The currency findings below do not rely on duplicate equivalent units.

### Prioritized findings and proposed corrections

#### R1 — P1: currency disappears before arithmetic

**Locations:** `src/value_retrieval/selection.py:13–27,61,75`,
`src/value_retrieval/get_value.py:74–83`,
`src/value_retrieval/get_assets.py:9–12,27–28`,
`src/value_retrieval/get_liabilities.py:82–99,113–116,132–133`,
`src/value_retrieval/get_equity.py:19–20`,
`src/value_retrieval/get_interest_expense.py:39–51`, and the final divisions in
`src/calculations/debt_to_asset_ratio.py:20` and
`src/calculations/interest_coverage_ratio.py:20`.

A unit check applies only to occurrences of **one concept**. The returned float
has no unit. Thus Assets=100 USD and Liabilities=50 EUR produce 0.5; current
assets=40 USD and noncurrent assets=60 EUR produce 100 in both fixed and filed
sums. These are confirmed **constructed** cases in
`test_currency_is_lost_before_ratio` and
`test_currency_is_lost_before_fixed_and_filed_sums`. A calculation relationship
cannot make unlike units arithmetically compatible. The examples expose an
application error without claiming those values constitute one valid bound
calculation equation.

Conversely, Assets disclosed in USD and EUR causes a duplicate conflict even
when a matching USD liability amount is available
(`test_distinct_currency_facts_are_treated_as_conflicting_duplicates`). Currency
selection precedes duplicate comparison. Official basis: Guide §§6.6, 7.5, 9.8–9.10
and the monetary types in the FASB schema.

**Correction:** return an amount with its resolved unit, dates, entity/scope,
accuracy, and provenance. Select the appropriate reporting-currency fact set
before duplicate comparison; require matching currency throughout equations,
identities, and ratios. Do not invent FX conversions. If reporting currency or a
compatible pair cannot be established, retain a diagnosed missing result.
**Limit:** no mixed-currency target failure was observed in the real sample.
That does not validate the current cross-component assumption.

#### R2 — P2: approved branch lists and temporary-equity retrieval omit standard alternatives

**Locations:** `src/value_retrieval/get_liabilities.py:11–22,56,74–75` and
`src/value_retrieval/get_equity.py:22–26`.

The complete standard equation
`LiabilitiesAndStockholdersEquity = AccountsPayableCurrent + inclusive permanent equity`
with amounts 100=60+40 returns missing liabilities. The official
`AccountsPayableCurrent` definition identifies a liability, but the list excludes
it. `test_standard_liability_branch_not_in_allowlist` demonstrates this without
assuming missing noncurrent liabilities are zero: completeness is stipulated by
the supplied equation. `DeferredRevenueNoncurrent` is another reviewed standard
liability absent from the list; expanding names by substring would be unsafe.

A separately supplied parent temporary-equity amount of 10 and redeemable
noncontrolling-equity amount of 5 are not assembled into total temporary equity.
With assets=100 and inclusive permanent equity=40, the fallback misses liabilities
of 45 (`test_temporary_equity_split_is_not_retrieved`). Both components are
explicit; neither is inferred as zero. The official parent temporary-equity,
redeemable noncontrolling-interest, and total temporary-equity definitions establish
the disjoint ownership portions, subject to matching scope and complete coverage.

**Correction:** maintain a versioned, explicitly reviewed semantic registry;
expand eligible liability/equity alternatives and documented component formulas.
Support legitimate signed contra-equity branches with their filed weights, not
only +1. Use complete applicable relationships and independent reconciliation
where available; do not simply sum every fact that seems to be a liability.
**Limit:** these new failures are constructed. The existing ten AMD/Walmart
examples happen to fit the whitelist. Unknown standard concepts are coverage
work, not custom-tag exclusions. Missing minority/temporary equity still cannot
be assumed absent merely because it is undisclosed.

#### R3 — P2: rounded alternative equations block usable independent evidence

**Locations:** `src/value_retrieval/selection.py:64–75`,
`src/value_retrieval/get_value.py:85–92`,
`src/value_retrieval/get_assets.py:7–16`.

Every complete derived amount must be numerically identical. In the constructed
`test_rounding_conflict_blocks_independent_reported_total`, one asset equation
sums to 100 and another to 110. The first has two inputs rounded to tens; the second expands current assets
into two disclosed components and has three inputs. Their supported total
intervals are [90,110] and [95,125]. A separately reported
`LiabilitiesAndStockholdersEquity` of 105 is compatible with both, but the first
asset lookup throws and blocks that independent asset-equivalent fallback.
Different sums are not by themselves proof of inconsistent source facts.
Official basis: FASB combined-total definition and Guide §§5.9.3, 6.6.4, 9.10.

**Correction:** preserve declared accuracy and distinguish rounding-compatible
estimates from genuine contradictions. Check independently reported equivalents
against the candidate intervals before rejecting the metric. Preserve provenance
and evaluate dependencies so an alleged independent check is not the same
reconstruction repeated. **Limit:** overlapping intervals alone do not supply a
unique disclosed point value; do not choose a midpoint, average, or whichever
role comes first. When no supported point exists, missing/interval output remains
appropriate. This finding does not require treating genuinely inconsistent
filings as in scope.

#### R4 — P2: one-level forward retrieval misses permitted standard equations

**Locations:** `src/value_retrieval/get_value.py:63–83`,
`src/value_retrieval/get_liabilities.py:27–31,61–71`,
`src/value_retrieval/get_interest_expense.py:4–53`.

`get_calculated_value` retrieves only **reported** immediate children. A supplied
standard network for operating income, with gross profit absent but fully
recoverable from revenue and cost, produces missing rather than 50.
`test_complete_nested_standard_equation_is_not_evaluated` demonstrates it.
Some asset components do get one additional level through the fixed formula;
that incidental behavior is not general recursive support.

Similarly, a filed relationship `InterestCostsIncurred = InterestExpense +
InterestCostsCapitalized`, with 12 incurred and 2 capitalized and one unknown,
is not solved (`test_filed_inverse_interest_equation_is_not_solved`). This test
relies on the supplied applicable relationship; it does not authorize a universal
replacement of total interest with borrowing costs under any taxonomy year.

The special liability route handles a nil `CommitmentsAndContingencies` caption,
but the general combined-total route does not. Hiding the combined total while
retaining its otherwise complete standard components and the nil caption prevents
asset reconstruction (`test_nil_caption_blocks_general_assets_reconstruction`).
Nil caption handling must remain a documented exception, not a rule converting
nil monetary amounts to zero. Official basis: Guide §§5.9, 6.7.11, 6.8.1.10.

**Correction:** evaluate applicable effective standard relationships recursively,
with cycle detection, context/unit matching, signed weights, and traceable
one-unknown rearrangements. Reuse the justified caption rule consistently.
Do not add descendants to a reported subtotal, mix roles, or treat a partially
observed network as proof of exhaustive coverage. **Limit:** the tests supply
constructed relationships, not complete SEC-validating XML instances or proof
that this sample contains these missing-parent cases. They establish identifiable
implementation restrictions on otherwise permitted standard arithmetic structures.

#### R5 — P2: annual period selection depends on incidental ordering

**Location:** `src/table_data/generate_ratios.py:64–76`.

The first library period labeled `Annual` and ending on the report date wins.
The installed dependency's `edgar/xbrl/core.py:197–216` classifies 350–380 days as
Annual; `edgar/xbrl/parsers/instance.py:933–954` builds these descriptions from
contexts. The production selector never verifies that the duration belongs to
the reporting entity's required annual context. Two matching-end candidate
periods in opposite orders produce different starts in
`test_annual_selection_depends_on_period_order`. This test calls only mocked,
isolated extraction, not the live pipeline.

**Correction:** identify the required reporting context using DEI/document and
entity metadata, then require the same actual start/end on duration facts. If
multiple periods remain genuinely applicable, diagnose the ambiguity. Do not add
a preferred-day-count heuristic. Guide §§3.1.2, 6.3, 9.7 and FAQ D.6.1 distinguish
reporting context from an assumed twelve-month interval. **Limit:** no wrong
annual start was demonstrated in the 22 real cases. Original 10-K only, five
periods, no amendments, no 10-KT, and no later restatement replacement are explicit
application policies; they must not be described as a full corrected annual
history. A latest-restated-history requirement would need a separate policy.

#### R6 — P2: missing reasons and provenance do not survive the handoff

**Locations:** ratio functions' `except SelectionError` and missing/zero branches
(`src/calculations/debt_to_asset_ratio.py:7–18`,
`src/calculations/interest_coverage_ratio.py:7–18`),
`src/table_data/generate_ratios.py:20,93–98`,
`src/database/create_tables.py:24–32`, and
`src/database/financials_table_info.py:21–45`.

Absent facts, incomplete standard coverage, selection conflicts, and a zero
denominator all become indistinguishable `None`, then empty CSV cells and SQL
NULL. `test_missing_states_collapse_before_csv` demonstrates the first three.
The CSV/database retain neither source amounts, units, periods' start dates,
accession, taxonomy version, reconstruction method, nor reason codes. Printing a
conflict is useful but cannot make a persisted row independently reproducible.
This is an implementation auditability defect, not a claimed SEC schema mandate.

**Correction:** preserve per-metric status/reason and source evidence in additional
CSV fields or an associated evidence table keyed by stable company identity,
accession, period, metric and run. Preserve zero and signed values separately from
missing. Continue overwriting old numeric values with NULL at matching keys when
a new evaluated result is missing. **Limit:** truly different unknown causes
cannot be recovered retrospectively from current empty cells alone.

The financial loader also drops missing-key rows before validation
(`financials_table_info.py:16`). This can leave a previous database value untouched;
it is not equivalent to recording the new row as unavailable. Prefer a rejected
batch or an explicit quarantine/count policy. Historical rows absent from an
input CSV remain stored by design. With no run/as-of identity, the views can show
an older persisted row when the current extraction yields no rows for a company;
that is a freshness limitation, not evidence that SQL converted NULL to a number.

#### R7 — P3: exact disclosed values are converted to float; infinity passes the handoff

**Locations:** `src/value_retrieval/selection.py:27,61,75`,
`src/table_data/checks.py:30–34`,
`src/database/financials_table_info.py:12,36–44`.

The exact constructed integer 9,007,199,254,740,993 with `decimals=INF` returns
9,007,199,254,740,992 after float conversion
(`test_float_conversion_does_not_preserve_exact_integer`). Decimal arithmetic
applied after this conversion cannot restore the original value. Pandas fact
frames already impose float limitations in the dependency. CSV reload is another
float boundary; SQL NUMERIC does not recover previously lost precision.
`test_csv_validation_accepts_infinite_ratios` confirms that nonfinite output is
not rejected by `check_ratios`.

**Correction:** preserve exact transformed decimal source values through selection
and calculation; specify ratio precision/rounding explicitly and bind Decimal
values to NUMERIC. Add finite-result validation before writing and loading.
**Limit:** no material float loss or infinite ratio was demonstrated in these
real filings. These constructed tests establish behavior, not observed investor
impact. SEC decimals describe disclosed accuracy, not an instruction to invent
additional significant digits.

### Review of every current retrieval route

All conclusions below require the same entity, period, currency and accounting
scope. “Supported” means semantic support for the formula, not a guarantee that
all components exist or that current metadata checks enforce those conditions.

| Route | Assessment and limitation |
|---|---|
| Direct Assets, Liabilities, OperatingIncomeLoss, InterestExpense | Correct named targets in 2026. Exact lookup and correct instant/full-duration matching are sound. Version differences below remain material. Direct precedence is reasonable; it is not independent reconciliation. |
| Generic calculation of any requested standard target | Uses separate roles and immediate arcs with signed weights. Does not double count descendants of a reported subtotal. Applicability, recursive/inverse coverage, metadata and accuracy need R1/R3/R4; the installed parser's effective-arc handling remains unverified. |
| AssetsCurrent + AssetsNoncurrent | Supported partition; requires both or explicit derivation. Missing one is not zero. R1 applies. |
| Assets from LiabilitiesAndStockholdersEquity | Supported whole-balance equivalence under matching consolidated scope; R3 can block the independently reported route. The generic nil-caption route has R4. |
| Assets from liabilities + inclusive permanent + total temporary equity | Supported partition; code avoids a direct circular call between the final identities. Explicit absence or complete filed structure is needed before omitting an equity component. R1/R2 apply. |
| Liabilities from combined total's branches | Correct for an applicable exhaustive disjoint liability/equity partition. A reported combined total is required, but when summing liability branches its numeric value is not actually checked against all branches. No independent reconciliation is implemented. R2/R4 limit coverage. |
| LiabilitiesCurrent + LiabilitiesNoncurrent | Supported when both available; current-only cannot become total without affirmative complete structure. R1 applies. |
| Assets − inclusive permanent − total temporary equity | Supported matching-scope identity. R2 misses explicitly disclosed temporary-equity components. Neither missing NCI nor missing temporary equity proves zero. |
| Inclusive permanent equity, otherwise parent equity + MinorityInterest | Definitions distinguish parent and noncontrolling ownership; do not add NCI again to inclusive equity. Both required for the split route. No unconditional assumption that parent equity equals consolidated equity. |
| Total temporary equity | Appropriate total concept; R2 identifies incomplete component coverage. Redeemable NCI is not universally the whole total. |
| OperatingIncomeLoss | Supported target. No universal GrossProfit − OperatingExpenses fallback absent an applicable relationship; classification varies. R4 concerns an explicitly supplied relationship, not a guessed identity. |
| InterestExpenseOperating + InterestExpenseNonoperating | Supported by 2024–2026 definitions, requiring both portions or evidence establishing complete coverage. One portion alone is not the total. |
| InterestIncomeOperating − InterestIncomeExpenseNet | Supported operating-interest reconstruction with the net sign preserved. It still needs the nonoperating expense for total expense. No arbitrary absolute value. |
| Ratio division | Preserve negative numerator and explicit zero. A zero denominator is undefined and appropriately missing. R1/R6/R7 cover units, reasons and numeric representation. |

No rule was found justifying universal use of cash interest paid, net expense,
`InterestAndDebtExpense`, debt-only interest, or a lease-interest add-on as the
defined total. The reviewed `InterestAndDebtExpense` definition covers
nonoperating financing activities and debt-related expenses; its label is not an
alias for total operating-plus-nonoperating interest. The four-company pilot's
missing interest cases cannot simply be filled with these substitutes.

### Historical taxonomy checks

The actual primary documents reference these versions (fiscal year/end, not
filing year):

| Company / fiscal ends | Namespace years used |
|---|---|
| AAPL 2021–2025 | 2021, 2022, 2023, 2024, 2025 |
| AMD 2021–2025 | 2021, 2022, 2023, 2024, 2025 |
| WMT January 2022–January 2026 | 2021, 2022, 2023, 2024, 2025 |
| MSFT June 2022–June 2026 | 2022, 2023, **2023**, **2024**, **2025** |
| JPM and BRK-B December 2025 | 2025 |

The 2021 files use the `2021-01-31` filename/namespace suffix, unlike later years.
Official archived definitions and schemas were downloaded for all six versions.
Sources include [2021 definitions](https://xbrl.fasb.org/us-gaap/2021/elts/us-gaap-doc-2021-01-31.xml),
[2022 definitions](https://xbrl.fasb.org/us-gaap/2022/elts/us-gaap-doc-2022.xml),
[2023 definitions](https://xbrl.fasb.org/us-gaap/2023/elts/us-gaap-doc-2023.xml),
[2024 definitions](https://xbrl.fasb.org/us-gaap/2024/elts/us-gaap-doc-2024.xml), and
[2025 definitions](https://xbrl.fasb.org/us-gaap/2025/elts/us-gaap-doc-2025.xml).
The corresponding schemas and all differences are in the hashed evidence set.

- `InterestExpenseOperating` and `InterestExpenseNonoperating` are absent in
  2021–2023 and present from 2024 in the checked releases. `InterestExpense` in
  2021–2023 describes cost of borrowed funds accounted for as interest expense;
  2024–2026 explicitly covers operating and nonoperating expense, including but
  not limited to borrowing cost. The older definition cannot silently be quoted
  as the newer one. Numerical comparability beyond the historical definition is
  **unverified**, not a proved sample misstatement.
- `InterestIncomeExpenseNet` wording changes from net operating interest to
  interest income/expense classified as operating. The signed operating net
  reconstruction remains supported; this is not a net-to-gross identity without
  the separately disclosed income.
- Assets, AssetsCurrent and Liabilities definitions change between 2023 and 2024
  to present rights/obligations wording. The reviewed current/noncurrent partition
  is not invalidated merely by that wording change.
- Parent/inclusive equity and MinorityInterest wording changes after 2022;
  current definitions explicitly separate permanent ownership portions and
  exclude temporary equity. Parent-only must not become inclusive by naming.
- `LongTermDebtNoncurrent` changes from the longer 2021 wording, to 2022 wording
  excluding unamortized premium/discount and issuance cost, to 2023–2026 wording
  describing deduction of those amounts. Preserve that actual version distinction;
  do not reinterpret historical disclosed debt using a 2026 label alone.
- The comparison finds **29 year/concept differences** across the checked set.
  The other checked definitions and relevant type/period/balance attributes match
  2026, aside from the absent new concepts. This is not an audit of every concept
  reachable through arbitrary filing calculation networks, deprecation labels,
  accounting references, or every accepted taxonomy family.

**Proposed correction:** preserve namespace/version and use a reviewed versioned
concept registry for targets, components, and derived definitions. No runtime
web download is necessary: checked local metadata can be versioned with the code.
`get_value.py:7–16` currently normalizes spelling and tests a prefix, not semantic
version membership. Historical differences establish an unverified comparability
risk, not permission to replace old facts with guessed modern equivalents.

### Scope, calculations, storage, and remaining coverage

**Company/consolidated scope.** The default SEC context normally represents the
consolidated registrant; excluding ordinary segment facts is justified. A selected
filing CIK is not a complete proof of fact scope in co-registrant or consolidating
reports. `get_value.py:24` rejects all dimensions without reviewing their meaning;
the raw sample checks found the expected default identifiers. Coverage of other
standard dimensional reporting bases has not been established. Do not sum
segments or accept parent-only amounts to fill a consolidated gap. Custom entity
members requiring interpretation remain excluded. A claim that *every*
dimensioned standard fact is outside scope is broader than this review supports.

**Calculation applicability and reconciliation.** A role name, presentation
membership, or an available list of children does not establish an exhaustive
applicable equation for every context. Reintroducing a blanket presentation-tree
requirement would also reject permitted structures. Preserve effective arcrole,
role, priorities/prohibitions, period, unit, entity and dimensional applicability.
The dependency's `edgar/xbrl/parsers/calculation.py:144–146,202–210` materializes
filed arcs; full effective-DTS resolution has not been validated here. Production
consumes `all_arcs` directly. Test future changes with prohibited/overridden and
multi-link cases before claiming coverage.

The NCI omission guard (`get_value.py:42–55`) is a targeted check, not an
applicability proof. It neither proves temporary-equity coverage nor establishes
that absent NCI is zero. General calculations short-circuit on reported totals;
fixed fallbacks also stop at the first usable path. There is no systematic
cross-route reconciliation. The previous altered-AMD test proves the code lacks
that check, **not** that a compliant AMD filing was wrong. Genuine malformed,
overlapping, or inconsistent equations remain outside the user's scope; independent
checks are still valuable to detect a selection or parser error made by this code.
Where no independent total exists, report that reconciliation is unavailable.

**Duplicate selection.** Current overlap checks and most-precise selection match
the cited numeric-duplicate policy for the supported cases. Equal decimals with
different amounts are rejected; zero/negative and INF cases are tested. Nonnumeric
and nil values are dropped, preserving their absence as missing numeric input.
A nil caption exception is distinct from monetary zero. Decimal accuracy metadata
is discarded after selection (R3/R7); entity/unit equivalence and scope must be
established before comparing facts (R1). The raw audit skips unsupported
`numwordsen` occurrences and does not claim all Inline transforms are verified.

**Database and views.** `financials_table_info.py:25–27,36–45` correctly replaces
existing values with NULL for matching keys. The two SQL views choose the latest
stored period per ticker before computing rank; they keep current companies via
LEFT JOIN and do not substitute an older nonmissing metric. CASE suppresses a
rank for NULL and NULLS LAST prevents missing values from ranking first. These
are static PostgreSQL conclusions; no live or local PostgreSQL instance was used.
Zeros, negative ratios, and ties are retained; RANK gaps on ties are intentional.
The view count check is a membership-row check, not metric or accounting validation.

`companies_table_info.py` updates membership transactionally; `main.py` does not
make all six stages one atomic transaction. Failure between company and financial
loads can expose mixed refresh states. `create_tables.py`'s IF NOT EXISTS is not a
complete migration validator. Company CIK is discarded on database load, while
ticker is the primary identity, creating historical rename/reuse and multi-share-
class comparability risks. The six-company sample does not exercise these cases.
Use stable issuer identity and a run/as-of boundary if these views are intended
to represent one coherent extraction. Higher interest coverage and higher leverage
have different meanings; descending ranks are not a universal risk score.

**Other modules.** `wiki_pull.py` retrieves current membership from a third-party
HTML table, without timeout/status checking or a pinned as-of source; this is an
operational/reproducibility limitation, not an official accounting definition.
`company_status.py` validates keys but writes its CSV nonatomically.
`generate_ratios.py` has useful atomic completed/partial CSV handling, but skips
missing report dates, consumes original filings in library order, and lacks
per-filing retry/isolation. `setup_sec_identity.py` is configuration, not evidence
of data correctness. Requirements pin versions, but do not replace parser coverage
checks. Root scratch probes and historical audit collectors were read; they are
not production paths or proof that reported numbers are universally correct.

### Final assessment

- **Confirmed defects/gaps:** loss of currency before arithmetic; multi-currency
  facts misclassified as duplicate conflicts; omitted standard branch/equity
  alternatives; blocked independent evidence after rounding-compatible sums;
  limited recursive/inverse/caption coverage; order-sensitive annual selection;
  collapsed missing reasons/provenance; float and nonfinite-validation limits.
  Newly demonstrated adverse outcomes are constructed tests. No new incorrect
  numeric result was established in the 22 unaltered real filings.
- **Unverified coverage:** all S&P 500 issuers and periods; full effective-DTS and
  parser behavior; every standard dimensional structure; historical metric
  comparability across changed definitions; all Inline transformations; real
  mixed-currency selection; deployed PostgreSQL tables/views and refresh behavior.
  The review is complete, but these coverage claims are deliberately not made.
- **Intentional exclusions/policies:** custom concepts or members requiring
  interpretation; actual standards departures; currently original 10-Ks only,
  five periods and current constituents. The latter are application policies,
  not mandatory SEC restrictions or proof that other valid annual structures are
  outside the user's broader goal.
- **Unavoidable information limits:** genuinely undisclosed required amounts,
  unresolved gross components behind net figures, unestablished absence of NCI or
  temporary equity, incompatible currencies without a supported common basis,
  and indeterminate values below disclosed accuracy. Return a reasoned missing
  state for these. Do not relabel recoverable standard structures as unavoidable.

**Integration remains deferred.** Proposed corrections need review, versioned
semantic decisions, and regression tests against both valid alternatives and
information-limit cases. Passing this sample is not proof of universal correctness.

### Follow-up: arithmetic recoverability versus established completeness

`implementation/inspect_liability_identity.py` records direct inputs for the ten
AMD/WMT filings in `liability_identity_inputs.json`. Assets minus parent equity
for AMD, and assets minus inclusive permanent equity minus reported redeemable
noncontrolling equity for WMT, numerically match all ten linkbase-derived
liabilities results (`liability_identity_comparison.json`). These are candidate
identities, not newly approved production fallbacks: AMD lacks the reported
inclusive equity/NCI and temporary-equity inputs; WMT lacks a reported total
temporary-equity amount and parent temporary-equity input. Numeric agreement
does not independently establish that missing categories are zero or that the
selected components exhaust equity. The ablation demonstrates dependence on the
current implementation, not mathematical impossibility of another derivation.

### Foreign-currency evidence (October 14, 2026)

An offline scan of the 22 archived instance documents found 38 facts using
non-USD ISO4217 units. Reproduce with
`.venv/bin/python scratch/unchecked_tests/implementation/inspect_foreign_currency.py`;
full facts, units, contexts and official URLs are in
`implementation/foreign_currency_evidence.json` under `scratch/unchecked_tests`.
Examples: Microsoft's 2025 10-K reports `us-gaap:DebtInstrumentFaceAmount`
EUR4.1 billion; Walmart's 2024 10-K reports the same concept in EUR850 million
and JPY70 billion. Those examples have dimensioned contexts. No non-USD fact in
this sample uses a concept in the current retrieval allowlist. These findings
refute the claim that every amount anywhere in an S&P 500 filing is USD, but do
not establish a non-USD consolidated target metric or a need for general
multicurrency selection in the current metric set. USD-only acceptance with an
explicit unit filter would be a different, narrower implementation policy; simply
ignoring units is not equivalent. No production logic was changed by this scan.

### External research: USD reporting rule and its limits (October 14, 2026)

The official [S&P U.S. Indices Methodology](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-indices.pdf),
Eligibility Factors, requires U.S. domicile for index purposes and domestic-form
periodic reporting. This does not mean all constituents are U.S.-incorporated.
[Regulation S-X 3-20(a)(2), official 2025 CFR](https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol3/pdf/CFR-2025-title17-vol3-sec210-3-20.pdf)
requires a non-foreign-private issuer to present financial statements in USD.
The [SEC Financial Reporting Manual section 6640](https://www.sec.gov/about/divisions-offices/division-corporation-finance/financial-reporting-manual/frm-topic-6)
describes limited staff non-objection to another reporting currency where there
are little/no U.S. assets/operations and substantially all operations use that
single foreign functional currency. This is staff guidance on limited exceptions,
not a general permission for domestic issuers to choose any currency.

Targeted external searches for non-USD assets, current/noncurrent assets and
liabilities, equity and interest concepts, including Linde, Accenture and Aon,
did not establish a qualifying S&P 500 consolidated counterexample. This was
not an exhaustive scan of all issuers, periods or accepted concepts. As affirmative
evidence of normal practice outside the archived sample, [Linde's 2024 SEC-filed
annual report](https://www.sec.gov/Archives/edgar/data/1707925/000114036125016583/ef20048246_ars.pdf)
explains translation of foreign operations to its USD reporting currency.
Previously documented foreign debt-face-amount disclosures do not demonstrate
non-USD consolidated amounts for the current allowlist. Therefore USD-only
acceptance is a defensible explicit coverage policy, but an assertion that no
compliant domestic issuer can ever report these metrics in another currency is
too strong. Retaining a USD unit filter would implement that narrower scope;
it would not require general multicurrency discovery or currency conversion.
No production code changed during this research.
