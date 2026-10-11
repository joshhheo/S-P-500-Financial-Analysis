Use SEC EDGAR to compute Leverage Ratio, Interest Coverage Ratio, and Current Ratio

Analyze financial risk for equity investors and creditos

Do not use edgartools get total method (unrelaible fallbacks)


Data validation and concept selection

The project uses the official FASB U.S. GAAP taxonomy accepted by the SEC to define the financial amounts used in each ratio. Concept selection is based on published definitions, rather than statement labels, similar tag names, or a library’s automatic mappings.

The review established four primary concepts:

| Financial amount | Primary concept |
| Total assets | `us-gaap:Assets` |
| Total liabilities | `us-gaap:Liabilities` |
| Operating income or loss | `us-gaap:OperatingIncomeLoss` |
| Total interest expense | `us-gaap:InterestExpense` |

Related concepts were reviewed for differences in scope. For example, nonoperating interest expense is only part of total interest expense, while cash interest paid measures cash payments rather than recognized expense. Neither is treated as an interchangeable substitute. No synonymous alternatives were identified for the selected primary and component tags in the reviewed 2026 taxonomy.

When a primary amount is unavailable, a fallback is permitted only when an accounting equation and the official component definitions support the reconstruction. Examples include:

- Total assets = current assets + noncurrent assets.
- Total liabilities = current liabilities + noncurrent liabilities.
- Total interest expense = operating interest expense + nonoperating interest expense.

Reviewing equity definitions also identified a limitation in the earlier assets-minus-equity fallback: permanent equity excludes temporary equity. Any reconstruction using equity must account for that distinction. An absent component is not automatically treated as zero, because a missing tag may represent an omitted subtotal rather than an absent balance.

Extraction selects undimensioned facts for consolidated amounts and matches them to the relevant fiscal period. Balance-sheet amounts use the fiscal year-end date; income-statement amounts must share the same annual start and end dates. Required amounts that cannot be obtained through a supported method remain null. Ratios with a zero denominator also remain null.

Pilot runs check that filing retrieval, period selection, component extraction, and ratio calculations work together across companies and years. This validates the pipeline’s use of reported facts; it does not independently audit companies’ accounting or guarantee the accuracy of their filings. Company-specific custom tags are outside the current extraction scope.

The taxonomy review defines acceptable extraction rules. Additional fallbacks identified during that review are not considered implemented until they are added to the pipeline.

### Calculation fallback order

Each standard component uses its direct reported fact first, then a complete
calculation equation from the same filing, then the approved fixed formulas
in the component modules. Missing required values remain `None`.

`src/quick_setup/get_calculated_value.py` shares the already-parsed XBRL object.
It matches the filing entity, excludes dimensioned facts, and matches the instant
date or both duration dates. It keeps the first matching numeric fact, including
zero and negative values.

The calculation step sums a target's immediate children using each declared
relationship's weight. Roles stay separate; the first complete equation in filing
order is used. Every child must be a standard US GAAP concept with a matching
reported value. It does not recursively reconstruct children, rearrange equations,
or add descendants to reported subtotals in this general helper. The existing fixed formulas remain in
the assets/liabilities and operating-income/interest-expense modules and their
components also receive the direct-then-calculation lookup.

Run the focused checks with `python -m unittest discover -s scratch/tests`.
Run the full company-list extraction with `python src/generate_ratios.py`.
The database pipeline is separate; `src/main.py` also performs database writes.


### Ratio extraction

Debt to assets means **total liabilities / total assets** in this project.
Interest coverage means **operating income (loss) / total interest expense**.
A missing input or zero denominator produces an empty CSV cell. Negative operating
income remains negative. Duration facts require both annual dates.

The liabilities module now also examines the filing's combined liabilities-and-
equity equation before its fixed-formula fallbacks. It requires a matching balance-
sheet presentation role containing Assets and LiabilitiesAndStockholdersEquity.
Each immediate monetary branch must have an exact reviewed US GAAP definition
classifying it as a liability or equity, and each required amount must pass the
same entity, consolidated-scope, and date filters. It sums only the declared
liability branches, or rearranges the equation when Liabilities itself is the
missing child. Temporary equity is included where the equation declares it;
redeemable noncontrolling interest is not treated as a synonym for all temporary
equity. Unknown required branches stop this fallback.

The one caption exception is the exact CommitmentsAndContingencies concept when
present as a blank nonnumeric balance-sheet caption. Its official definition is
of a caption, not a monetary total. Excluding that caption does not assert that
commitments are zero. All other missing monetary children remain required.

Definition references: [official FASB taxonomy documentation](https://xbrl.fasb.org/us-gaap/2026/elts/us-gaap-doc-2026.xml)
and [SEC staff tagging guidance](https://www.sec.gov/files/edgar/filer-information/specifications/xbrl-guide-2026-01-16.pdf),
sections 6.7.11 and 6.8.1.10. Reviewed balance-sheet definitions are also saved in
`scratch/extraction_audit/reviewed_definitions.json`.

No generic missing-tag-to-zero rule is implemented: no reviewed convention here
makes absence of an interest or noncurrent subtotal alone unambiguously zero.
A complete filed equation containing only a current component can still establish
the total. Total interest expense retains the operating + nonoperating fallback,
including operating interest income minus signed net operating interest when both
facts exist. Cash interest, net interest alone, and nonoperating expense alone do
not replace total interest expense.

The extraction processes every entry in `data/company_status.csv`, using up to five annual periods per ticker.
Run `.venv/bin/python src/generate_ratios.py` from the repository root to refresh
`data/financial_ratios.csv`. The database loader uses this same file. Run `.venv/bin/python -m unittest discover -s scratch/tests -v`
for the focused tests and 22 saved-filing regression checks. These checks need the
saved JSON extracts under `scratch/extraction_audit`; they do not contact SEC or
write to the database. Historical audit policy documents describe earlier research;
this section describes the implemented behavior. Derived amounts use reported
precision; no interval-arithmetic framework is introduced.

Tests live in `scratch/tests/`; the earlier four-company pilot output is kept in
`scratch/pilots/financial_ratios_pilot.csv`. Production uses `data/financial_ratios.csv`.
