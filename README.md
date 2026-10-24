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

The average line shows the arithmetic mean of ticker ratios for each sector and
comparison period, giving each ticker equal weight. Extreme values can pull the
average away from the median, which is the middle value.

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

[![Previous and Latest liabilities-to-assets distributions by sector, zoomed to 0–1.5](<images/Liabilties-to-Assets-Distribution (0-1.5).png>)][tableau]

**Full-Range View**

[![Previous and Latest liabilities-to-assets distributions by sector, full range](<images/Liabilties-to-Assets-Distribution.png>)][tableau]

**Coverage:** 401 of 503 tickers have a latest ratio (79.72%); 102 are missing
(20.28%). The paired charts include 396 tickers (78.73% of all current tickers),
with two observations each: 792 rows. The remaining 107 tickers are excluded.
These counts use the October 21, 2026 repository CSV snapshot.
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

### Liabilities-to-Assets Observations

#### Utility Extraction Errors

The unusually low ratios for PPL, PSEG, and NiSource reproduce a calculation that
omits separately reported long-term debt. Their 2025 consolidated balance sheets
give the following comparison:

| Company | Stored ratio | Including all reported liabilities |
| --- | ---: | ---: |
| [PPL](https://www.sec.gov/Archives/edgar/data/0000922224/000119312526136009/ppl_2025_annual_report.pdf) | 0.273 | 0.671 |
| [PSEG](https://s24.q4cdn.com/601515617/files/doc_financials/2025/q4/PSEG_2025_10-K.pdf) | 0.329 | 0.705 |
| [NiSource](https://d18rn0p25nwr6d.cloudfront.net/CIK-0001111711/e5c9b499-c076-4b24-96c8-1c551acb79de.pdf) | 0.244 | 0.675 |

These errors remain in the CSVs. The exact retrieval path, earlier periods, and
other utilities need review. Both annual periods and the chart statistics need
updating before interpreting the corrected utility distribution.

#### Extreme Company Ratios

##### Domino's

Domino's has the highest latest ratio in the matched sample: **3.273**, compared
with **3.281** previously. Its 2025 balance sheet reports approximately
**$5.62 billion of liabilities against $1.72 billion of assets**.

**Business and asset base.** Franchisees sell pizzas and pay royalties; Domino's
supply-chain business also sells food and other supplies to stores. About **99% of
stores are franchised**, so most stores' buildings and equipment are not on the
listed company's balance sheet. This lets Domino's earn recurring income without
owning every restaurant. It has assets, but its recorded asset base is relatively
small compared with its liabilities.

**Liabilities and cash use.** Domino's borrows through **securitized bonds backed
by franchise agreements, supply-chain agreements, intellectual property, and
related rights**. Its debt is supported by that cash-generating business system,
not just physical restaurants.
[Debt structure and collateral](https://www.sec.gov/Archives/edgar/data/1286681/000119312525198332/d946118d8k.htm).
Buybacks have historically used operating cash flows, recapitalization proceeds,
and borrowings. Cash distributed to shareholders reduces assets and equity while
debt can remain outstanding. Repaying bond principal, by contrast, reduces debt;
issuing new bonds to repay older bonds generally replaces an existing obligation.

**What the ratio says about stability.** The ratio identifies substantial leverage
and negative book equity, but is **weak evidence of immediate payment distress on
its own**. Domino's reported **$792.1 million of operating cash flow in 2025**:
the business continued generating cash despite its high ratio. The vulnerability
is that debt payments remain due if franchise and supply-chain cash flows weaken,
and future refinancing may be needed. The ratio is therefore a reason to examine
cash available after investment, interest costs, and repayment dates, rather than
a conclusion that the business is unstable.
[Annual report](https://www.sec.gov/Archives/edgar/data/1286681/000128668126000014/dpz_ars_2026.pdf).

##### Verisign

Verisign's ratio rises from **2.392 to 2.625**, with approximately **$3.48 billion
of liabilities against $1.33 billion of assets** at year-end 2025.

**Business and asset base.** Registrars pay Verisign for domain registrations and
renewals, and Verisign operates the registry services over the registration period.
Its business uses computing infrastructure and staff rather than a separate
physical location for every customer. Cash returned through buybacks and dividends
also leaves fewer assets on the balance sheet. The recorded asset total therefore
does not represent the value of all the future registrations the business may earn.

**Liabilities and cash use.** Approximately **$1.38 billion is deferred revenue**:
customers have already paid for services Verisign still owes them. Another
**$1.79 billion is senior-note debt**. These obligations are different. Deferred
revenue generally requires providing the service over time, with the associated
operating costs; debt requires interest and principal payments. Treating the full
liability balance as borrowed money would misread its financial structure.
[Annual filing](https://www.sec.gov/Archives/edgar/data/1014473/000101447326000006/vrsn-20251231.htm).

**What the ratio says about stability.** This is a **limited standalone indicator
of payment pressure**, because it combines financing debt with prepaid services
and an asset base reduced by shareholder distributions. Verisign generated about
**$1.09 billion of operating cash flow in 2025**, which provides important context
alongside its negative book equity.
[2025 results](https://www.sec.gov/Archives/edgar/data/1014473/000101447326000005/q42025earningsrelease.htm).
The service obligations and debt are still real. A stronger stability assessment
would examine whether registrations and renewals can continue funding operations
and debt service, and how much cash is retained rather than distributed. The
2.625 ratio alone does not establish deterioration in that ability.

##### SBA Communications

SBA Communications' ratio decreases from **1.443 to 1.413**, with approximately
**$16.35 billion of liabilities against $11.58 billion of assets** at year-end
2025.

**Business and asset base.** SBA owns and operates tower sites and leases antenna
space to wireless service providers. Tenant payments fund site operations,
investment, debt service, and shareholder distributions. Unlike Domino's, this is
a business with substantial physical assets. However, depreciation of towers and
amortization of acquired assets reduce their recorded values over time, even while
sites can continue earning rent. Buybacks and dividends also reduce assets and
equity. A comparatively small denominator here means small relative to its
liabilities, not that SBA owns few assets.
[Annual report](https://www.sec.gov/Archives/edgar/data/1034054/000119312526149691/d875239dars.pdf).

**Liabilities and cash use.** Borrowing is a substantial part of the financing
structure supporting its tower portfolio and capital allocation. SBA reported
about **$13.0 billion of debt principal** at year-end 2025, alongside other
obligations such as ground leases. The business therefore depends on collecting
lease income while meeting its own financing and site commitments.

**What the ratio says about stability.** The high ratio is **a relevant warning
about leverage, although it does not establish current distress**. SBA also
reported net debt equal to **6.4 times annualized adjusted EBITDA**, a separate
company-defined leverage measure. This corroborates that the borrowing burden is
substantial relative to that earnings measure; depreciation alone is not the full
explanation.
[Debt and leverage figures](https://ir.sbasite.com/news-events/press-releases/news-details/2026/SBA-Communications-Corporation-Reports-Fourth-Quarter-2025-Results-Provides-Full-Year-2026-Outlook-and-Declares-Quarterly-Cash-Dividend/default.aspx).
Recurring tenant payments help support the obligations, but lost rental income,
higher refinancing costs, or large repayments could create pressure. Assessing
stability requires checking those commitments against cash generation, rather
than treating the book value of towers as either their sale value or proof that
the debt is safe.

##### What These Companies Have in Common

The common feature is **large obligations relative to the assets still recorded on
the balance sheet**. That can result from different combinations of borrowing,
shareholder payouts, operating liabilities, and reductions in asset values. The
business model explains why a company can generate cash despite that structure;
it does not make the obligations disappear.

For example, a company with assets of 100 and liabilities of 80 has a ratio of
0.80. Paying shareholders 20 of cash, with liabilities unchanged, raises the ratio
to 1.00. The ratio rose because assets and equity fell, even though the company
did not borrow more. Borrowing alone initially adds both cash and debt, so how the
cash is subsequently used matters.

Across the stored sample, **18 tickers in seven sectors have latest ratios above
1**, generally indicating negative book equity. The useful question is whether
their businesses can generate enough cash, at the right times, to meet their
specific obligations. Domino's franchise cash flows, Verisign's prepaid services,
and SBA's tower rents require different assessments. A high ratio identifies a
balance-sheet feature to investigate; its meaning for stability depends on the
company behind it.

#### Sector Differences

##### Utilities Have a Narrow Central Distribution

**What the chart shows.** Utilities have an **IQR of approximately 0.060**, the
narrowest in the stored sample. Expressed as percentages of assets, the middle
half of their ratios fit within a range of about **6 percentage points**. That
is a statement about how similar the covered companies look, not how low their
liabilities are: their latest median is approximately **0.750**.

**Business and financing.** Utilities invest in infrastructure that provides
services over many years. Customer payments fund operations and investment, as
well as payments to lenders and shareholders. For regulated utilities, rate-setting
considers the cost of financing that infrastructure with debt and equity. Similar
operating requirements and regulatory arrangements could therefore encourage
similar financing choices across companies.
[Utility financing context](https://www.cpuc.ca.gov/industries-and-topics/electrical-energy/electric-costs/cost-of-capital).

**What it means.** The cluster could reflect a common business structure rather
than unusually similar financial health. Two utilities with the same ratio can
still face different interest costs, investment needs, and repayment schedules.
Regulatory financing assumptions also do not directly determine the listed
parent's total liabilities/assets ratio. The identified extraction errors must be
corrected before confirming the sector's median and spread. A narrow box alone
establishes neither stability nor distress.

##### Energy Has the Lowest Stored Median

**What the chart shows.** Energy's latest median is approximately **0.471**:
liabilities equal about **47.1% of assets** for the middle covered ticker.
Information Technology is close at **0.488**, so Energy sits at the low end of the
sample without being sharply separated from every other sector.

**Business and financing.** For oil and gas producers, producing and selling energy
generates cash that can be reinvested, used to repay lenders, or returned to
shareholders. The choice affects the balance sheet. Earlier strong industry cash
flows supported debt repayment and shareholder distributions; the IEA documents
these uses of cash in 2022–2023.
[Industry cash-flow context](https://www.iea.org/reports/world-energy-investment-2024/overview-and-key-findings).

Debt repayment can lower a ratio that starts below 1, while profits retained in
the business can build equity. For example, a company with liabilities of 60 and
assets of 100 has a ratio of 0.60. Using 10 of cash to repay debt leaves liabilities
of 50 and assets of 90, lowering the ratio to about 0.56. Paying that cash to
shareholders instead would leave liabilities at 60 and raise the ratio to about
0.67. A large physical asset base alone therefore does not explain a low ratio;
how it was financed and how cash is used matter.

**What it means.** The chart suggests relatively less reliance on liabilities in
these companies' recorded funding mix. It does not establish the most stable
future cash flows. As an example of industry cash-flow variability, the EIA reports
that operating cash flow in its global upstream sample fell by 10% in real terms
in 2024. That is a different population and period from this chart, but illustrates
why a low balance-sheet ratio does not guarantee steady cash generation.
[EIA financial review](https://www.eia.gov/finance/review/).
Only **11 of 21 Energy tickers** are matched here, and a producer-focused explanation
does not cover every Energy business. Debt repayment is a possible contributor to
the low median, not an established explanation for the full sample.

##### Consumer Discretionary Sits High and Varies Widely

**What the chart shows.** The latest median is approximately **0.754**, and
**seven of 35 matched tickers** have ratios above 1. Its **0.365 IQR** means the
middle half span about **36.5 percentage points**. The sector therefore combines
an elevated typical ratio with substantial differences between companies; its
position is not just a reflection of Domino's extreme value.

**Business and financing.** The sector combines companies that own very different
assets and earn cash in different ways. A retailer carries inventory and uses
stores; a franchisor can earn royalties while franchisees operate the locations.
Borrowing, property ownership, leases, and shareholder payouts can consequently
produce different ratios even among profitable businesses.

Distributions are a concrete example. McDonald's returned **$7.1 billion** through
dividends and buybacks in 2025. As with Domino's, cash paid out can reduce equity
without requiring operating losses.
[McDonald's annual filing](https://www.sec.gov/Archives/edgar/data/63908/000006390826000035/mcd-20251231.htm).
Leases also matter, but generally add both an obligation and a right-of-use asset.
Adding equal amounts moves the ratio toward 1, so leases can help explain an
increase from a lower ratio without explaining every value above 1.

**What it means.** The wide spread makes individual business models particularly
important. An elevated ratio could reflect payouts and leased locations, or it
could accompany weak earnings and growing borrowing. The chart cannot distinguish
those explanations. If sales weaken while rent and debt payments remain due, cash
pressure could increase; whether that is happening requires company-level evidence.
The median is a comparison point, not a diagnosis of the sector's financial health.

##### Financials Have the Highest Stored Median

**What the chart shows.** Financials have the highest latest median, approximately
**0.795**, across **74 matched tickers**. Consumer Discretionary has prominent
extremes, but Financials have the higher middle value. This separates the typical
sector position from the most dramatic individual points.

**Business and financing.** For a bank, customer deposits are liabilities because
the bank owes that money back. Deposits and other financing support assets such
as loans and securities, which generate income. A large liability balance can
therefore be part of the ordinary business model. JPMorgan describes deposits,
secured and unsecured funding, and equity as sources of balance-sheet financing.
[JPMorgan's financing and balance sheet](https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/jpm-20251231.htm).

**What it means.** The high ratio is relevant to how much of the asset base is
funded by obligations rather than equity. However, it does not reveal the quality
of loans, the market value of securities, or how quickly funding might leave.
Those differences can matter greatly: deposit withdrawals may require a bank to
raise cash, and selling assets at a loss can weaken its equity position.
[Bank asset values and funding pressure](https://www.stlouisfed.org/on-the-economy/2023/feb/rising-rates-complicate-banks-investment-portfolios).

A high ratio is therefore neither automatically abnormal for a bank nor sufficient
evidence that it is safe. Financials also include insurers, exchanges, and asset
managers. Comparing companies within those narrower business groups would be more
informative than treating the whole sector as one financing model.

##### Materials Also Have a Relatively Narrow Middle Range

**What the chart shows.** Materials have an **IQR of approximately 0.139**, so the
middle half span about **13.9 percentage points**, compared with **36.5** for
Consumer Discretionary and Communication Services. Their latest median is about
**0.563**. The observation is that central ratios are relatively similar, rather
than that liabilities are especially low.

**Possible explanation.** Comparable investment and financing policies among some
producers could contribute, but a shared cause has not been established. The sector
contains chemicals, packaging, mining, and construction materials, so its members
do not all have the same operating process. The sample also covers only **17 of
24 tickers**; the companies with usable data may influence the apparent clustering.

**What it means.** Similar total ratios can conceal different obligations. As a
hypothetical example, two companies could each have assets of 100 and liabilities
of 55. One might have 45 of borrowing and 10 of supplier obligations; the other
might have 10 of borrowing and 45 of supplier obligations. Both ratios are 0.55,
but their interest costs and payment schedules could differ considerably. The
compact box establishes similarity in the totals, not a common explanation or
identical financial stability.

##### Technology Combines a Low Median With High Outliers

**What the chart shows.** Information Technology has a latest median of
approximately **0.488**, yet **three of 66 matched tickers** exceed 1. Verisign's
**2.625** ratio is therefore very different from that of the middle covered
company. The low median and high extremes are both meaningful observations.

**Business and financing.** Companies can differ in how they retain or distribute
cash, how much they borrow, and whether customers pay before services are provided.
Verisign illustrates the last point: prepaid registrations create liabilities
alongside its debt, while shareholder payouts reduce the assets it retains.
That particular combination helps explain its outlier without establishing a
sector-wide cause for the lower median.

**What it means.** The company label matters less than the underlying flow of cash
and obligations. A low ratio could reflect substantial retained assets, while a
high ratio could reflect distributions, borrowing, or operating liabilities.
Neither establishes whether future income can support payments when they fall due.

This is also a useful comparison of the average and median lines. A few very high
values can pull the average upward much more than the median. If the average sits
well above the median, the high end of the distribution is influencing it; the
middle company need not have a similarly high ratio. Neither line weights a
company more heavily just because it is larger.

#### Changes Between Annual Periods

**What the chart shows.** Most sector boxes overlap substantially, and every
sector's median changes by less than **4 percentage points**. There are still
differences in direction:

| Sector | Previous median | Latest median | Change in percentage points |
| --- | ---: | ---: | ---: |
| Energy | 0.472 | 0.471 | −0.1 |
| Materials | 0.524 | 0.563 | +3.9 |
| Information Technology | 0.524 | 0.488 | −3.6 |

These are rounded differences between sector medians. They are not percentage
changes of −0.1%, +3.9%, and −3.6%, or the median changes of individual companies.

**Why ratios can stay similar.** Assets and liabilities are balances accumulated
over time, so one year's sales or profits need not transform their proportions.
A company can also grow while keeping the same ratio: liabilities of 60 against
assets of 100 give the same 0.60 ratio as liabilities of 66 against assets of 110.
The business expanded, but its funding proportions stayed similar.

**Why a stable median can hide movement.** Some companies' ratios can rise while
others fall, leaving the middle value or box largely unchanged. Because Previous
and Latest include the same tickers within each metric, a changing participant
list does not explain the difference between those two plots. However, the
companies still have different fiscal dates, and each ratio can change through
borrowing, repayment, payouts, or changes in recorded assets.

**What it means for stability.** A stable ratio does not prove stable cash flow,
and a rising ratio does not establish deteriorating operations. For example, a
profitable company's buyback can raise its ratio. A company with a ratio below 1
could lower it by selling assets and repaying debt, even if financial pressure
prompted the sale. The reason for the movement matters alongside its direction.

To determine whether a sector-wide shift was widespread, the next useful measures
are the **median individual-company change** and the **share of matched companies
whose ratios increased**. A change between two sector medians answers where the
middle of each distribution sits; those additional measures would show how the
same companies actually moved.

### Interest Coverage Distribution

**Zoomed View (−10–65×)**

[![Previous and Latest interest-coverage distributions by sector, zoomed to −10–65 times](<images/Interest Coverage Ratio Distribution (-10-65).png>)][tableau]

**Full-Range View**

[![Previous and Latest interest-coverage distributions by sector, full range](<images/Interest Coverage Ratio Distribution.png>)][tableau]

**Coverage:** 96 of 503 tickers have a latest ratio (19.09%); 407 are missing
(80.91%). The paired charts include 94 tickers (18.69% of all current tickers),
with two observations each: 188 rows. The remaining 409 tickers are excluded.
These counts use the October 21, 2026 repository CSV snapshot.
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

Interest coverage is expressed as a multiple (×).

### Interest Coverage Observations

#### Limited Data and Interpretation

**These charts describe a small, selected group of companies and should not be
used to rank whole sectors by financial stability.** Only **94 of 503 tickers
(18.69%)** appear in the paired plots. The 188 plotted rows are two annual
observations for each of those tickers, not 188 different companies.

Coverage is uneven: Financials have only two matched tickers and Energy has three.
Even Industrials, which includes EMCOR, covers only **13 of 83 tickers**. A sector's
box, median, or average can therefore be heavily influenced by a few available
companies. Missing results may reflect unsupported filing structures or unavailable
inputs; they do not mean zero coverage or financial distress. The companies with
usable ratios should not be assumed to represent those without them.

**Apparent year-to-year volatility may therefore misrepresent the wider sector.**
Large shifts in a box, median, or average may be driven by a small set of covered
companies, while most sector members are absent. These plots are not a reliable
measure of how volatile interest coverage was across the full sector, or whether
a change was widespread. Previous and Latest use the same matched tickers, so
limited coverage does not itself make a verified company's change inaccurate;
it limits how confidently that change can be generalized.

My observations focus on individual companies whose reported inputs can be checked.
A large movement is a reason to examine both operating income and interest expense,
not by itself evidence that a company has become less stable. A very small positive
interest expense can produce an enormous ratio, making percentage changes look
dramatic even when interest remains modest relative to earnings.

#### EMCOR's Coverage Falls by About 60 Percent

EMCOR's ratio falls from **355.88× in FY2024 to 142.55× in FY2025**, a decline of
**59.94%**. Both stored ratios can be reproduced from the operating income and
gross interest expense in its annual filing:

| Measure | FY2024 | FY2025 | Change |
| --- | ---: | ---: | ---: |
| Operating income | $1,344.863 million | $1,713.418 million | +27.40% |
| Interest expense | $3.779 million | $12.020 million | +218.07% |
| Interest coverage | 355.88× | 142.55× | −59.94% |

[Reported financial statements](https://www.sec.gov/Archives/edgar/data/105634/000010563426000025/eme-20251231.htm).

**What caused the drop.** Interest expense more than tripled from a very small
base, while operating income grew by about 27%. The denominator therefore grew
much faster than the numerator. Coverage fell even though reported operating
income increased: this is a financing-cost change, rather than evidence of a
collapse in operating earnings.

**Business and borrowing context.** EMCOR attributes the higher interest expense
to temporary use of its revolving credit facility during 2025. Such a facility
allows borrowing and repayment during the year. Its debt note reports **no
outstanding debt at either year-end, excluding finance lease liabilities**. Annual
interest expense can therefore rise despite there being no outstanding revolving
borrowings on the final balance-sheet date. The ratio measures financing costs
incurred over the year, not just the debt held on December 31.
[Interest-expense discussion and Note 9](https://www.sec.gov/Archives/edgar/data/105634/000010563426000025/eme-20251231.htm).

**An earnings qualification.** FY2025 operating income includes a **$144.9 million
gain from selling its UK operations**. That gain should not be assumed to recur,
so the reported ratio is not a measure of recurring operating earnings alone.
Subtracting that gain alone still leaves operating income about $223.7 million
above FY2024; this is not a full adjustment for every nonrecurring item.
[Operating-income and sale-gain details](https://emcorgroup.com/application/files/4817/7205/3638/4Q25_Earnings_Release.pdf).

**What it says about stability.** At 142.55×, reported operating income remains
very large relative to annual interest expense. The percentage decline is therefore
**weak evidence of financial instability on its own**. It shows that interest
became a larger claim on earnings, but began from an exceptionally small base.
The relevant question is whether higher borrowing costs persist and whether cash
from the business can support future interest, investment, and principal payments.
Operating income is not cash available to pay every obligation, and this ratio
does not measure those principal payments.

This is a checked company-level observation. It does not establish a decline in
interest coverage across Industrials or the wider S&P 500.

#### Kraft Heinz

Kraft Heinz's ratio falls from **1.85× to −4.93×**, a **367.17% decrease**.
Dollar amounts below are in millions.

| Measure | FY2024 | FY2025 |
| --- | ---: | ---: |
| Operating income / (loss) | $1,683 | −$4,669 |
| Interest expense | $912 | $947 |
| Interest coverage | 1.85× | −4.93× |

**Operating income.** Goodwill and intangible-asset impairments rose from
**$3.669 billion to $9.306 billion**, explaining most of the earnings decline.
These write-downs recognize reduced asset values without an equivalent cash
payment that year. There was also weaker performance beyond those charges:
company-defined adjusted operating income fell **11.5%**, from $5.360 billion
to $4.745 billion.

**Interest expense.** Expense increased about **3.8%**. That added pressure, but
the much larger change came from operating income turning negative. The ratio
crosses zero because of an operating loss, while interest expense remains positive.
[Annual report and earnings reconciliation](https://www.sec.gov/Archives/edgar/data/1637459/000163745926000009/khc-20251227.htm).

**What the ratio says about stability.** Reported operating earnings no longer
cover interest. However, the negative ratio includes substantial noncash charges,
so it does not establish that cash generated was insufficient to pay interest.
The write-downs still matter as evidence of reduced asset values; recurring
earnings, cash flow, and repayment needs require separate assessment.

#### Willis Towers Watson

WTW's ratio rises from **2.38× to 8.59×**, a **260.41% increase**.
Dollar amounts below are in millions.

| Measure | FY2024 | FY2025 |
| --- | ---: | ---: |
| Operating income | $627 | $2,234 |
| Interest expense | $263 | $260 |
| Interest coverage | 2.38× | 8.59× |

**Operating income.** FY2024 included a **$1.042 billion goodwill impairment
associated with TRANZACT**, which did not recur in FY2025. Transaction and
transformation expenses also fell from **$409 million to $23 million**. These
changes explain most of the rebound: the comparison starts from a year depressed
by unusually large expenses. Company-defined adjusted operating income grew
only about **3%**, from $2.378 billion to $2.449 billion.

**Interest expense.** Expense declined about **1.1%**, so reduced financing costs
made only a small contribution. The coverage increase primarily reflects the
recovery in reported operating income.
[Annual report and earnings reconciliation](https://www.sec.gov/Archives/edgar/data/0001140536/000119312526127631/wtw_ars_123125.pdf).

**What the ratio says about stability.** Reported earnings provide a larger
margin over annual interest costs. The 260% improvement nevertheless overstates
the growth in underlying operating performance, because much of it reflects
prior-year charges disappearing. It does not establish a proportionate improvement
in financial stability or cash available for debt repayment.

#### Baxter International

Baxter's ratio falls from **0.0343× to −1.0621×**, a **3,195.17% decrease**.
Dollar amounts below are in millions.

| Measure | FY2024 | FY2025 |
| --- | ---: | ---: |
| Operating income / (loss) | $14 | −$308 |
| Interest expense | $408 | $290 |
| Interest coverage | 0.0343× | −1.0621× |

**Operating income.** Earnings were already barely positive in FY2024. FY2025
included **$485 million of goodwill impairments** and a **$290 million trade-name
impairment**, alongside other operating costs. The business's reported earnings
therefore moved from near break-even to a loss. The write-downs reduce accounting
income without equivalent current-year cash payments.

**Interest expense.** Expense fell about **28.9%**. The filing presents interest
expense before deducting interest income separately from net interest expense;
this calculation uses **$290 million**, rather than the $238 million net amount.
Lower interest expense did not prevent coverage turning negative because
operating income deteriorated.
[Annual report, operating results, and interest note](https://www.sec.gov/Archives/edgar/data/10456/000162828026007733/bax-20251231.htm).

**What the ratio says about stability.** Neither year's reported operating
earnings cover interest. That deserves investigation, but the enormous percentage
is amplified by the **near-zero starting ratio**. It does not mean payment
pressure increased thirtyfold. Cash generation, the reasons for the impairments,
and debt obligations matter more than that percentage alone.

#### Viatris

Viatris's ratio falls from **0.0184× to −5.6505×**, a **30,870.27% decrease**.
Dollar amounts below are in millions.

| Measure | FY2024 | FY2025 |
| --- | ---: | ---: |
| Operating income / (loss) | $10.1 | −$2,663.1 |
| Interest expense | $550.0 | $471.3 |
| Interest coverage | 0.0184× | −5.6505× |

**Operating income.** Goodwill impairment rose from **$321.0 million to
$2,936.8 million**, a major driver of the loss. Gross profit also fell from
$5,623.6 million to $5,013.5 million. The decline therefore includes both a large
noncash write-down and weaker gross profit; it should not all be dismissed as
an accounting adjustment.

**Interest expense.** Expense fell about **14.3%**, providing some relief in
dollar terms. The ratio still became negative because of the operating loss.
Dividing a negative loss by a smaller positive interest amount makes its negative
multiple larger in magnitude; that is not evidence that lower interest costs
made the company worse off.
[Reported results](https://investor.viatris.com/news-releases/news-release-details/viatris-reports-fourth-quarter-and-full-year-2025-financial).

**What the ratio says about stability.** The loss warrants examination, but
**30,870% is dominated by the tiny positive starting ratio**. It is not a comparable
measure of deterioration across companies. Assessing payment capacity requires
cash flow and obligations alongside the earnings changes and impairment.

#### Air Products

Air Products' ratio falls from **20.41× to −4.10×**, a **120.08% decrease**.
Dollar amounts below are in millions. Its fiscal year ends on September 30.

| Measure | FY2024 | FY2025 |
| --- | ---: | ---: |
| Operating income / (loss) | $4,466.1 | −$877.0 |
| Interest expense | $218.8 | $214.0 |
| Interest coverage | 20.41× | −4.10× |

**Operating income.** FY2025 included **$3.747 billion of business and asset
charges**, including project exits. FY2024 also benefited from a **$1.576 billion
business-sale gain**. The comparison therefore combines a year boosted by a gain
with a year burdened by charges. Company-defined adjusted operating income fell
about **3%**, much less than the reported earnings swing.
[Reported results and reconciliation](https://www.sec.gov/Archives/edgar/data/2969/000000296925000051/exhibit99130sep25.htm).

**Interest expense.** Reported expense declined about **2.2%**. However, total
interest incurred rose from **$507.9 million to $615.8 million**; more was
capitalized into construction projects rather than expensed immediately. The
ratio uses expense after capitalization, so its denominator does not capture
all financing costs incurred that year.
[Annual report, interest-expense discussion](https://www.airproducts.com.cn/-/media/files/en/900/900-25-045-glb-annual-report-2025.pdf).

**What the ratio says about stability.** The negative ratio signals a reported
operating loss, but does not alone establish an inability to pay interest.
Project charges deserve scrutiny, while capitalized interest makes cash funding
needs important even when reported interest expense looks stable. Adjusted
results provide context; they do not replace the plotted accounting measure.

#### What These Company Changes Show

The companies examined show much larger annual percentage changes in interest
coverage than in their liabilities-to-assets ratios. This illustrates **greater
sensitivity to annual earnings and financing costs**. Operating income can swing
with business performance, impairments, sale gains, and restructuring expenses;
assets and liabilities are accumulated balances that may change more gradually
or move together.

There are two different mathematical effects. A small **interest-expense
denominator** can produce a very high coverage multiple, as with EMCOR. A small
**previous coverage ratio** can produce an enormous percentage change, as with
Baxter and Viatris. Moving from positive earnings to a loss also allows a decrease
greater than 100%. These changes cannot be ranked as equivalent changes in
financial stability.

Two annual observations establish a change, rather than persistent volatility.
These checked examples also do not establish that interest coverage was more
volatile across the full S&P 500, given the limited sample. Company-defined
adjusted earnings are included only to explain the reported movements; the
charts continue to use reported operating income and interest expense.

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

The next analysis step is to investigate the identified utility extraction errors
and update the affected data and charts. Automatic chart updates are not planned
as part of the tool.

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
