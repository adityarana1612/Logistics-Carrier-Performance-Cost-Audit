# Lane Analysis

*Lane = origin warehouse region → destination customer region. Source: `data/processed/lane_scorecard.csv`, `carrier_lane_scorecard.csv`, `sql/carrier_audit.sql` §D, Excel `Lane_Analysis` and `Pivot_Analysis`. Synthetic data.*

## 1. All 20 lanes, ranked by failure cost per shipment

Failure cost = modelled late penalty + damage write-off + Air reshipment.

| Rank | Lane | Shipments | Late % | Damage rate | Avg quoted d | Avg actual d | Variance d | Freight/kg | Freight/kg CV | Failure cost / shipment | True cost / shipment |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | West-EU → Central-EU | 147 | 18.4% | 5.44% | 5.69 | 4.90 | -0.78 | $0.9651 | 1.17 | $1,830 | $6,853 |
| 2 | Asia → East-EU | 236 | 15.3% | 6.36% | 5.75 | 5.00 | -0.75 | $0.9930 | 1.16 | $1,563 | $6,728 |
| 3 | East-EU → West-EU | 359 | 17.0% | 5.85% | 6.05 | 4.92 | -1.14 | $0.7969 | 1.27 | $1,038 | $5,357 |
| 4 | Asia → Americas | 226 | 14.6% | 5.31% | 5.14 | 4.72 | -0.42 | $0.9839 | 1.11 | $990 | $6,372 |
| 5 | East-EU → Central-EU | 147 | 11.6% | 6.12% | 5.88 | 5.35 | -0.53 | $0.7903 | 1.24 | $968 | $5,299 |
| 6 | Central-EU → East-EU | 229 | 14.8% | 5.24% | 5.94 | 5.27 | -0.68 | $0.7790 | 1.25 | $941 | $5,311 |
| 7 | Central-EU → Americas | 204 | 12.7% | 2.94% | 5.73 | 5.28 | -0.45 | $0.8744 | 1.15 | $839 | $5,408 |
| 8 | West-EU → West-EU | 365 | 13.2% | 3.84% | 5.81 | 5.11 | -0.70 | $0.8466 | 1.24 | $816 | $5,325 |
| 9 | West-EU → Americas | 213 | 19.2% | 2.82% | 5.97 | 4.85 | -1.12 | $0.8477 | 1.22 | $757 | $5,543 |
| 10 | Asia → West-EU | 321 | 10.0% | 4.36% | 5.86 | 5.05 | -0.81 | $0.8382 | 1.18 | $694 | $4,905 |
| 11 | East-EU → Americas | 245 | 16.3% | 4.90% | 5.93 | 4.96 | -0.97 | $1.0442 | 1.12 | $691 | $6,744 |
| 12 | Central-EU → West-EU | 331 | 10.3% | 3.63% | 6.17 | 4.92 | -1.24 | $0.7970 | 1.23 | $685 | $5,145 |
| 13 | East-EU → East-EU | 225 | 14.7% | 3.11% | 5.71 | 5.04 | -0.67 | $0.8033 | 1.19 | $679 | $4,972 |
| 14 | Central-EU → Asia | 200 | 13.0% | 4.00% | 6.20 | 4.83 | -1.37 | $0.7431 | 1.25 | $591 | $4,329 |
| 15 | West-EU → East-EU | 225 | 12.9% | 4.00% | 5.64 | 4.97 | -0.66 | $0.9222 | 1.14 | $479 | $5,012 |
| 16 | East-EU → Asia | 169 | 21.3% | 0.59% | 5.94 | 4.92 | -1.02 | $0.9736 | 1.20 | $471 | $5,868 |
| 17 | Asia → Central-EU | 152 | 13.2% | 3.95% | 6.03 | 4.93 | -1.10 | $0.9676 | 1.19 | $466 | $5,679 |
| 18 | Central-EU → Central-EU | 153 | 13.1% | 3.92% | 5.93 | 5.24 | -0.69 | $0.9589 | 1.22 | $410 | $5,472 |
| 19 | Asia → Asia | 171 | 16.4% | 1.17% | 5.91 | 5.36 | -0.54 | $0.9061 | 1.16 | $392 | $5,507 |
| 20 | West-EU → Asia | 182 | 8.2% | 3.85% | 6.46 | 5.04 | -1.42 | $0.7513 | 1.26 | $389 | $4,346 |
| | **Network** | **4,500** | **14.1%** | **4.16%** | **5.89** | **5.02** | **-0.86** | **$0.8722** | | **$794** | **$5,477** |

**Reading the table**
* **Failure cost is driven mostly by damage.** The top 6 lanes all have damage rates above 5%, against a network rate of 4.16%. Damage triggers both a write-off and an Air reshipment, so it costs far more per event than a late penalty.
* **Highest late rates:** East-EU → Asia (21.3%) and West-EU → Americas (19.2%). These lanes rank low on failure cost because their damage rates are low.
* **East-EU origin** has the highest late rate (16.3%), and **Americas destination** the highest by destination (15.8%).
* **Freight-rate variation (CV of about 1.1–1.3)** reflects the carrier mix on each lane: Air at about $2.6/kg sits alongside Sea at about $0.16/kg. It does not mean that rates are inconsistent within a carrier.
* **Quoted vs actual days.** Every lane shows negative variance (faster than quoted) on average, because Sea's 14-day quote dominates the averages. Because the dates conflict with on-time flags, variance is descriptive only.

## 2. Highest transit-variance lanes (absolute deviation from quoted days)

| Lane | Avg absolute deviation | Std dev of actual days | Shipments |
|---|---:|---:|---:|
| East-EU → Americas | 4.84 | 2.64 | 245 |
| West-EU → Asia | 4.74 | 2.57 | 182 |
| Asia → Asia | 4.74 | 2.67 | 171 |
| East-EU → Central-EU | 4.71 | 2.63 | 147 |
| Central-EU → Asia | 4.71 | 2.51 | 200 |

Deviation is about 4.5–4.8 days on *every* lane, which is consistent with transit times that do not depend on carrier mode in this synthetic data.

## 3. Carrier × lane: failure cost per shipment ($)

| Lane | Road | Rail | Air | Sea |
|---|---:|---:|---:|---:|
| West-EU → Central-EU | 1,182 | 711 | 1,904 | **3,422** |
| Asia → East-EU | **2,496** | 1,523 | 1,609 | 743 |
| East-EU → West-EU | 1,021 | 588 | 789 | **1,694** |
| East-EU → Central-EU | **2,359** | 697 | 232 | 572 |
| West-EU → Americas | **1,654** | 359 | 557 | 425 |
| Asia → West-EU | 333 | 659 | 333 | **1,404** |
| Central-EU → Asia | 379 | 220 | 323 | **1,274** |
| East-EU → Americas | 317 | 461 | 635 | **1,185** |
| East-EU → East-EU | 388 | 402 | **1,732** | 153 |
| West-EU → West-EU | 479 | **1,347** | 826 | 440 |

*Top 10 problem cells shown. Full matrix: `data/processed/carrier_lane_scorecard.csv` and Excel `Pivot_Analysis`. Each cell holds 29 to 112 shipments, so individual cells are noisy.*

**No carrier is uniformly bad.** Each carrier has its own problem lanes:
* Sea: West-EU → Central-EU ($3,422) and East-EU → West-EU ($1,694)
* Road: Asia → East-EU ($2,496) and East-EU → Central-EU ($2,359)
* Air: West-EU → Central-EU ($1,904) and East-EU → East-EU ($1,732)
* Rail: Asia → East-EU ($1,523) and West-EU → West-EU ($1,347)

This argues for **lane-specific SLA clauses** rather than wholesale carrier switches.

## 4. Lanes selected for the strategy test

The cheapest carrier is CARR-4 (Sea). Its lanes with at least 30 shipments were ranked by failure cost per shipment:

| Rank | Lane | Sea shipments | Sea failure / shipment | Rail failure / shipment (same lane) |
|---:|---|---:|---:|---:|
| 1 | West-EU → Central-EU | 37 | $3,422 | $711 |
| 2 | East-EU → West-EU | 96 | $1,694 | $588 |
| 3 | Asia → West-EU | 85 | $1,404 | $659 |

Rail has lower failure costs on all three lanes, but its freight is about $0.10/kg dearer. Rail wins on net only on West-EU → Central-EU (see [cost_analysis.md](cost_analysis.md) §4).
