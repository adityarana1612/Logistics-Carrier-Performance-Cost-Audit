# Carrier Performance Analysis

*Source: `data/processed/carrier_scorecard.csv`, `significance_tests.csv`, `sql/carrier_audit.sql` §B and §E, Excel `Carrier_Performance`. Synthetic data.*

## 1. Scorecard

| Carrier | Mode | Shipments | On-time | Late | Damaged | Successful | On-time % | Late % | Damage rate | Success rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CARR-1 | Road | 1,091 | 938 | 153 | 46 | 900 | 86.0% | 14.0% | 4.22% | 82.5% |
| CARR-2 | Rail | 1,098 | 951 | 147 | 43 | 917 | **86.6%** | **13.4%** | **3.92%** | **83.5%** |
| CARR-3 | Air | 1,125 | 969 | 156 | 47 | 931 | 86.1% | 13.9% | 4.18% | 82.8% |
| CARR-4 | Sea | 1,186 | 1,006 | 180 | 51 | 961 | 84.8% | 15.2% | 4.30% | 81.0% |
| **Network** | | **4,500** | **3,864** | **636** | **187** | **3,709** | **85.9%** | **14.1%** | **4.16%** | **82.4%** |

## 2. Are the differences real?

Two-proportion z-tests for every carrier pair:

| Comparison | On-time z | p-value | Damage z | p-value |
|---|---:|---:|---:|---:|
| Rail vs Sea (largest gap) | 1.22 | 0.22 | −0.46 | 0.64 |
| Road vs Sea | 0.78 | 0.44 | −0.10 | 0.92 |
| Air vs Sea | 0.89 | 0.37 | −0.15 | 0.88 |
| Road vs Rail | −0.43 | 0.67 | 0.36 | 0.72 |
| Rail vs Air | 0.33 | 0.74 | −0.31 | 0.75 |
| Road vs Air | −0.11 | 0.91 | 0.05 | 0.96 |

**None of the 12 tests is significant at the 5% level.** The 95% confidence intervals for on-time % overlap heavily: Rail 84.5–88.5%, Air 84.0–88.0%, Road 83.8–87.9%, Sea 82.7–86.8%. In practice the four carriers are equally reliable, so reliability cannot justify a price premium.

## 3. Transit time (with caveat)

| Carrier | Quoted days | Avg actual days | Variance |
|---|---:|---:|---:|
| CARR-1 Road | 3 | 4.92 | +1.92 |
| CARR-2 Rail | 5 | 4.90 | −0.10 |
| CARR-3 Air | 1 | 5.07 | +4.07 |
| CARR-4 Sea | 14 | 5.18 | −8.82 |

By the dates, all carriers average about 5 days, so mode makes no difference to recorded speed. These dates conflict with `on_time_flag` for 49% of shipments. For example, Air would be "late by dates" on 1,009 shipments but is flagged late on only 156. Transit time is therefore reported here but **not used for ranking** (see [limitations.md](../limitations.md)).

## 4. Year-over-year

| Carrier | On-time 2024 | On-time 2025 | Damage 2024 | Damage 2025 | True cost/unit 2024 | 2025 |
|---|---:|---:|---:|---:|---:|---:|
| Road | 87.3% | 84.5% | 4.59% | 3.82% | $7.04 | $6.81 |
| Rail | 86.5% | 86.8% | 3.57% | 4.28% | $4.57 | $5.14 |
| Air | 85.3% | 86.9% | 4.41% | 3.96% | $34.13 | $34.72 |
| Sea | 86.2% | 83.5% | 4.89% | 3.71% | $4.14 | $3.75 |

Sea's on-time rate fell 2.7 points in 2025, which is worth raising in negotiation, while its damage rate improved. Year-to-year changes are within normal sampling noise for about 550–600 shipments per carrier per year.

## 5. Ranking

| Carrier | True cost / unit | Rank: cost | Rank: on-time | Rank: damage | Composite (0–100) | **Overall** |
|---|---:|---:|---:|---:|---:|---:|
| CARR-2 Rail | $4.84 | 2 | 1 | 1 | 98.5 | **1** |
| CARR-1 Road | $6.93 | 3 | 3 | 3 | 68.8 | **2** |
| CARR-4 Sea | $3.94 | 1 | 4 | 4 | 50.0 | **3** |
| CARR-3 Air | $34.44 | 4 | 2 | 2 | 28.3 | **4** |

*Composite = 50% true cost per unit + 30% on-time % + 20% damage rate, min-max normalised.* Min-max scaling stretches small gaps: Sea's last place on reliability (a 1.8-point gap that is not significant) costs it 50 composite points. On cost alone, Sea ranks first.

## Takeaways
1. Rail is the best all-round carrier and the right benchmark.
2. Sea is the cheapest but has the weakest service. Use SLA and damage clauses rather than moving volume away.
3. Air buys no measurable reliability benefit for its premium.
4. Reliability gaps are too small to drive allocation. Cost should lead.
