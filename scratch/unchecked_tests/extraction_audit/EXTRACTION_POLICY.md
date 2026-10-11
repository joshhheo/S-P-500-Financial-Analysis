# Evidence-based extraction policy for the four financial amounts

## What can and cannot be promised

This policy targets the correct financial amount, entity, scope, period, and
reported precision, assuming filings are correct. It permits None. It does not
promise a number for every company, recover undisclosed ledger precision, or
certify that the software has zero implementation defects.

S&P 500 eligibility narrows the issuer/reporting universe; it does not require a
uniform set of all four requested numeric concepts or eliminate reporting
rounding. The July 2026 S&P methodology's domestic-reporting eligibility is not
an additional financial-data completeness guarantee.

Two different notions of accuracy must remain separate:

- Reported value: reproduce the correct fact as disclosed, at its stated precision.
- Derived value: a supported calculation from disclosed facts. Its precision can
  be weaker than that of a directly reported total.

For a literal no-ambiguous-number policy, emit a derived point value only if the
admissible input ranges and proven equation determine a unique value at the chosen
output precision. Otherwise return None (or a range in a separate future product).
Do not advertise a calculated midpoint as exact.

## Search and fallback order

1. Fix the filing accession and its annual period. Keep the original-report series
   policy; do not silently substitute a later restatement or a comparative from
   another filing. Work from one parsed filing.
2. Search the exact standard concept, using its definition in that filing's
   taxonomy version. Match the reporting entity, consolidated scope, reporting
   date for balance-sheet amounts, and both dates for income/expense. Preserve the
   reported units and scale. The project assumes a consistent reporting currency.
3. If no reported value matches, consider only equations whose applicability to
   this requested amount and context has been established. Retrieve effective
   relationships within one role. The current first-complete-network heuristic
   alone is not such a proof.
4. Preserve weights and every required monetary component; do not count a subtotal
   and its descendants twice. Reject unknown/custom required components under
   current policy. An applicable reviewed equation can be used directly or
   rearranged only when the requested amount is uniquely identified.
5. Apply the approved fixed identities below with every required component present
   or its absence/zero specifically established. Reaching this stage supplies no
   additional evidence that a missing amount is zero.
6. If meaning, completeness, context, or required precision is unresolved, return
   None. A correct missing result is preferable to a different financial measure.

Keep the ordinary first-matching numeric direct-fact behavior; this policy does
not introduce conflict audits, isfinite checks, or unit-reference-ID comparisons.
For calculations that claim literal numerical exactness, precision propagation is
necessary even with correct filings; it is not an audit of hypothetical errors.

## Permitted amount definitions and fixed equations

Every concept below is in the us-gaap namespace.

Assets:
- Direct: Assets.
- Applicable filed equation for Assets.
- AssetsCurrent + AssetsNoncurrent.
- LiabilitiesAndStockholdersEquity as the balance-sheet identity.
- Liabilities + permanent consolidated equity + temporary equity.

Liabilities:
- Direct: Liabilities.
- Applicable filed equation for Liabilities.
- A reviewed combined-total equation with an exhaustive classification of its
  monetary branches can identify the liability portion. This is not inferred
  from indentation or a name substring. The AMD/Walmart prototype is experimental,
  not a universally proven classification algorithm.
- LiabilitiesCurrent + LiabilitiesNoncurrent.
- Assets - permanent consolidated equity - temporary equity.

Permanent consolidated equity:
- StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest.
- StockholdersEquity + MinorityInterest, requiring both.

Temporary equity:
- TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests.
- RedeemableNoncontrollingInterestEquityCarryingAmount is not a synonym for that
  total. It can be an explicitly classified branch in a reviewed filed equation.

Operating income:
- Direct: OperatingIncomeLoss.
- An applicable complete filed equation for that amount.
- No universal GrossProfit - OperatingExpenses fallback is approved.

Total interest expense:
- Direct: InterestExpense.
- An applicable complete filed equation for that amount.
- InterestExpenseOperating + InterestExpenseNonoperating.
- Operating interest can use InterestIncomeOperating - InterestIncomeExpenseNet,
  preserving the net amount's sign and requiring both values.
- Nonoperating expense alone, net interest alone, cash interest paid, and a lease
  interest subset are not the target total. Do not substitute them to fill a blank.

Apply direct-then-equation retrieval to each supporting component as appropriate.
Do not create circular asset/liability reconstruction.

## Omitted-zero conventions

A missing tag can legitimately correspond to zero, and the search must consider
that possibility. A documented implication that zero may be omitted is not the
reverse implication that every omission establishes zero.

Accept a zero supporting component when the relevant amount is established by:
- A reported numeric zero.
- An explicit disclosure that the exact category is absent at the requested
  scope and date, such as no noncurrent liabilities. No long-term debt is narrower
  and cannot establish no noncurrent liabilities.
- An applicable explicit reporting convention or table legend establishing that
  the particular omitted/blank amount means zero, rather than nil, unavailable,
  immaterial, rounded, or included elsewhere.
- A complete applicable equation that identifies the requested amount without
  needing the omitted subtotal. For example, if a complete Liabilities equation
  consists only of LiabilitiesCurrent, use that equation. This does not require
  inventing a LiabilitiesNoncurrent fact.

Search disclosures when needed, but do not invent an unrestricted phrase matcher
that assumes a statement about debt applies to all liabilities. Record the source
supporting each specifically established zero.

SEC staff guidance section 6.8.1.10 allows some dash cells to be untagged, nil, or
zero depending on their meaning. Regulation S-X 4-02 also permits immaterial
amounts to be combined instead of separately displayed. Therefore no generic
absence-only zero rule follows from compliance.

Real counterexample: AMD 2025 has no matching LiabilitiesNoncurrent subtotal but
has $4.472 billion of reviewed noncurrent liability components. Current-only
would understate its liabilities by that amount without any filing error.

Sources:
https://www.sec.gov/files/edgar/filer-information/specifications/xbrl-guide-2026-01-16.pdf
https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol3/pdf/CFR-2025-title17-vol3-sec210-4-04.pdf

## Nil caption rule

SEC staff guidance describes nil tagging for the blank CommitmentsAndContingencies
balance-sheet caption and explicitly distinguishes nil from zero and absence.
This supports recognizing a presentation convention. It does not by itself prove
that an otherwise incomplete total can be reconstructed.

Before excluding that caption from an arithmetic reconstruction, establish the
actual nil caption pattern and the applicable complete monetary equation. An empty
numeric field in a parsed table alone is insufficient. Do not generalize this to
other nil concepts or assume commitments are zero.

## Double-check results

The earlier investigation examined 22 filings, compared 34 direct numeric facts
with the SEC API, matched 12 withheld liability controls, and reconstructed ten
missing pilot liabilities under the reviewed experimental pattern.

The follow-up enumerated ALL complete standard-concept parent equations for the
four requested amounts where a reported control existed: 47/47 matched (20 assets,
10 liabilities, 17 operating-income equations). There were zero qualifying total
interest-expense parent equations; this supplies no new interest fallback evidence.

Two constructed arithmetic tests establish why universal exact recovery is not
just a testing issue:

- Component facts of 1 million and 1 million can both arise from underlying values
  of 1.1 + 1.1 million or 1.4 + 1.4 million. The correctly rounded totals are 2
  million and 3 million respectively. Without the total or finer precision, the
  inputs do not identify which total is correct.
- Net expense of 100 can arise from gross expense/income of 120/20 or 150/50.
  Without another independent relationship or amount, gross expense is unknown.

These examples do not assert that either pattern appeared in a sampled filing.
They show an information limit that cannot be removed by further sample tests.

## Sources

- S&P U.S. Indices Methodology, July 2026, eligibility criteria:
  https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-indices.pdf
- XBRL Calculations 1.1, sections 5.2 and 5.7, reported precision and intervals:
  https://www.xbrl.org/Specification/calculation-1.1/REC-2023-02-22%2Bcorrected-errata-2024-02-14/calculation-1.1-REC-2023-02-22%2Bcorrected-errata-2024-02-14.html
- SEC staff XBRL Guide, January 2026, sections 6.7.11 and 6.8.1.10:
  https://www.sec.gov/files/edgar/filer-information/specifications/xbrl-guide-2026-01-16.pdf

No production helper or production CSV was changed by these follow-up checks.
