# EDGAR extraction investigation — October 10, 2026

## Conclusion

The pilot's missing balance-sheet totals are recoverable with a narrowly defined,
filing-specific equation rule. The evidence does not support treating arbitrary
missing facts as zero, using one fixed list of liability components for all
companies, or guaranteeing every financial metric for every EDGAR filing.

The next production change should extend the linkbase stage to classify the
immediate children of the filing's combined liabilities-and-equity equation.
Subtract the equity categories actually declared there, including temporary
or redeemable equity. Handle a reviewed nil CommitmentsAndContingencies caption
as a presentation reference, not a monetary operand. Unknown components must
still stop that route. Preserve direct-first lookup and existing fixed formulas.

Production extraction and the production CSV were not changed by this study.
The new rule remains an experiment in experiments.py.

## Tests performed

Scope: five original annual filings each for AMD, Apple, Microsoft, and Walmart;
one latest annual filing each for JPMorgan and Berkshire Hathaway. The last two
are additional controls with different financial-statement presentations.

| Check | Result |
|---|---|
| Filings inspected | 22 |
| Direct assets available | 22/22 |
| Direct liabilities available | 12/22 |
| Parsed assets/liabilities facts matched to SEC Company Facts by accession and date | 34/34 available facts |
| Assets reconstructed from complete immediate calculation children | 20 matched reported assets |
| Liabilities reconstructed from complete immediate calculation children | 10 matched reported liabilities |
| Operating income reconstructed through the current complete-child helper | 16 matched reported operating income |
| Experimental combined-equation rule, without reading direct Liabilities | 12/12 controls matched reported totals |
| Missing liabilities reconstructed by the experimental rule | 10/10 AMD/Walmart cases |
| Synthetic rejection cases applied to actual Walmart evidence | 9 passed |
| Existing extraction behavior unit tests | 9 passed |

An unavailable calculation is not counted as a failed numeric comparison. The
20/10/16 comparisons only include cases where the current helper found a complete
standard-concept equation. Other networks can contain custom or unavailable facts.
The SEC cross-check is a comparison of two extraction paths over the same filings,
not an independent accounting audit. All equality statements refer to the amounts
and precision reported in the filings, not unreported ledger precision.

The nine rejection cases removed the redeemable-equity fact, removed a liability
component, removed the caption fact, substituted a custom concept, substituted an
unreviewed standard concept, made the caption numeric, changed a component's
entity, changed its date, or made it dimensioned. The separate existing tests cover
signed weights, direct zero precedence, annual date matching, network separation,
no descendant double counting, required equity components, and interest formulas.

## Recovered liability amounts

These are experimental results, not values written to the production CSV.
The known liability components also summed to these amounts in every case.

| Company | Reporting date | Total liabilities (USD) |
|---|---|---:|
| AMD | 2021-12-25 | 4,922,000,000 |
| AMD | 2022-12-31 | 12,830,000,000 |
| AMD | 2023-12-30 | 11,993,000,000 |
| AMD | 2024-12-28 | 11,658,000,000 |
| AMD | 2025-12-27 | 13,927,000,000 |
| WMT | 2022-01-31 | 152,969,000,000 |
| WMT | 2023-01-31 | 159,206,000,000 |
| WMT | 2024-01-31 | 161,828,000,000 |
| WMT | 2025-01-31 | 163,131,000,000 |
| WMT | 2026-01-31 | 178,488,000,000 |

## Why the reporting convention matters

The SEC staff XBRL Guide, (PDF page 132), specifically describes
using a nil fact for the commitments-and-contingencies balance-sheet line when
its columns are blank or dashes. Section 6.7.11 separately distinguishes nil from
zero and from an absent fact. FASB's definition describes CommitmentsAndContingencies
as a caption on the balance sheet. This supports a targeted caption treatment;
it does not establish that the company's commitments are zero.

Source: https://www.sec.gov/files/edgar/filer-information/specifications/xbrl-guide-2026-01-16.pdf

AMD's raw 2025 HTML was separately checked and explicitly uses xsi:nil="true".
The multi-filing experiment uses the parsed empty caption facts and presentation
membership; it does not independently inspect the raw nil attribute in every
historical filing. Production implementation should preserve the nil distinction
rather than equate every missing numeric value with the caption case.

FASB concept definitions reviewed for the classifications are saved in
reviewed_definitions.json (2025 and 2026 taxonomy documentation). Redeemable
noncontrolling equity is a category within equity outside permanent equity; it
is not a universal synonym for all temporary equity. Historical taxonomy-version
support should be explicit when broadening the implementation.

## A real counterexample to the earlier simple equity formula

Walmart's 2026 balance sheet reports assets of $284.668 billion, permanent
consolidated equity of $105.887 billion, and redeemable noncontrolling equity of
$0.293 billion. Thus liabilities are $178.488 billion. Subtracting only permanent
equity gives $178.781 billion: an overstatement of $293 million.

The equivalent omissions in Walmart's 2023, 2024, and 2025 filings would overstate
liabilities by $237 million, $222 million, and $271 million. The earlier simpler
method can agree for some companies while still making this concrete error.

Source: https://www.sec.gov/Archives/edgar/data/104169/000010416926000055/wmt-20260131.htm

## The proposed algorithm

1. Keep the direct exact standard-concept lookup, with requested entity,
   consolidated scope, and instant or complete annual interval.
2. Keep complete immediate-parent calculations in applicable statement roles.
3. For missing liabilities, inspect a balance-sheet role shared by presentation
   and calculation data containing Assets and LiabilitiesAndStockholdersEquity.
4. Classify every immediate child of the combined total using reviewed standard
   definitions: liabilities, permanent equity, temporary/redeemable equity, or
   the specifically recognized nil caption. Do not classify by a name substring
   or by credit balance type. Unknown/custom monetary concepts stop the route.
5. Use the filing's actual equation. Require the needed facts; do not invent
   missing equity zeros. Avoid adding both a total and its descendants. The
   experiment supports +1 combined-equation branches only; other weights need
   an explicit design rather than being silently accepted.
6. Return the reconstructed liabilities, then continue to the existing approved
   fixed identities when the filing-relationship route is unavailable.

The experiment recognizes a limited, explicit set of reviewed concepts. That set
classifies components; it is not a prescribed sum applied to every company. AMD's
2021 equation, for example, differs from later years, and Walmart has additional
lease and equity categories. More concepts need review as other filings require.
No indefinite recursion or general symbolic solver is needed for these cases.

For provenance, keep accession, reporting dates, chosen role, contributing
concepts, and whether the value was reported or derived. A reconstruction should
remain identifiable as derived even when it matches a reported control exactly.

## Interest coverage is a separate availability problem

All 20 pilot rows have operating income and assets. Current-policy total interest
expense is available for 11/20. The remaining nine gaps are not fixed by the
balance-sheet rule:

- Apple 2024–2025: no matching total or approved component facts were found. The
  2025 statement reports other income/expense net. It does not identify gross
  interest expense, and hypothetical interest-rate sensitivity is not actual
  interest expense.
- Microsoft 2025–2026: InterestExpenseNonoperating is reported ($2.385 billion and
  $3.051 billion), but the approved operating component is unavailable. Finance
  lease interest cannot simply be added because overlap has not been established.
- Walmart's five years: the income-statement equation uses a company-specific
  finance-lease-and-financing-obligation interest concept. The existing policy
  excludes that custom component. Net interest and cash paid are not substitutes
  for the defined gross total.

This is evidence of present route limitations, not proof that no further
filing-specific disclosure analysis could recover some amounts. No unapproved
interest fallback was introduced.

Sources:
https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm
https://www.microsoft.com/investor/reports/ar25/index.html
https://www.sec.gov/search-filings/edgar-application-programming-interfaces

## Reproduce

From this directory in the repository's environment:

    python audit.py                 # retrieve/cache filing evidence
    python experiments.py           # run saved-evidence comparisons and rejection tests
    python sec_crosscheck.py         # compare direct facts against SEC API

From the repository root:

    python -m unittest discover -s tests

results.csv includes each accession and role. test_summary.json summarizes the
experiment. sec_crosscheck.json records each API comparison. The individual JSON
files retain the matching facts and filed relationships for inspection.

Long text-block values in the evidence snapshots are marked and truncated to 500 characters; numeric facts and relationship lists are retained.
