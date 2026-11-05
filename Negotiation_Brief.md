# Carrier Contract Negotiation Brief

**Prepared for:** Logistics Manager, Meridian Components
**Subject:** True cost of each carrier, reliability, problem lanes and recommended allocation
**Basis:** 4,500 outbound shipments, January 2024 to December 2025

> **Data notice.** This analysis uses the *Meridian Supply Chain Dataset* from Kaggle, which its publisher describes as **synthetic** (generated for teaching, MIT licence). Meridian Components is a fictional company. Freight cost, on-time flags and damage flags come from the data. The dataset has **no penalty or reshipment fields**, so late penalties, damage write-offs and expedited reshipments are **modelled** from stated assumptions (Section 4). Treat the findings as a worked example of the method, not as facts about real carriers.

---

## 1. Executive Summary

The company suspected that its cheapest carrier, **CARR-4 (Sea, $0.15/kg)**, becomes the most expensive once late deliveries, damage and reshipments are counted. **The data does not support this.**

| | Finding |
|---|---|
| **Cheapest carrier is still cheapest** | CARR-4's true cost is **$3.94 per unit**, the lowest of the four carriers. CARR-2 (Rail) is $4.84, CARR-1 (Road) $6.93 and CARR-3 (Air) $34.44. |
| **But its hidden costs are large** | CARR-4's modelled failure costs (**$1.02M**) are *larger than its whole freight bill* (**$1.00M**), a 102% uplift. That is a strong argument for SLA and claims clauses. It is not an argument to drop the carrier. |
| **Reliability is effectively equal** | On-time rates range only from 84.8% to 86.6%, and damage rates from 3.9% to 4.3%. No pairwise difference is statistically significant (all p > 0.2). |
| **The proposed reallocation does not reach the target** | Moving 20% of CARR-4's volume to CARR-2 on CARR-4's three worst lanes changes total true cost by **+$548 (+0.002%)**, against a target of **−12% (−$2.96M)**. |
| **The real lever is Air** | CARR-3 (Air) carries 25% of the weight but takes **76% of freight spend**, with no reliability advantage. Moving about **20% of Air weight to Rail** would cut network true cost by roughly **12%** (about $2.9M), *if* that volume is not genuinely urgent. |

**Recommendation in one line:** keep CARR-4 as the low-cost backbone, but negotiate SLA credits and damage liability into its contract. Make CARR-2 (Rail) the preferred carrier for overall value. Then test, and phase in, a move of non-urgent Air volume to Rail. That is the only option in the data that is large enough to reach the 12% target.

---

## 2. Business Problem

The company is preparing to renegotiate its carrier contracts. Comparing carriers on contract rate ($/kg) alone ignores what happens after the invoice: late shipments trigger customer service credits, damaged goods are written off, and replacements are re-sent by expedited freight. The questions are:

1. What is the **true cost** of each carrier per shipment, per unit and per successful delivery?
2. How **reliable** is each carrier, and are the differences real or noise?
3. Which **origin-to-destination lanes** cause the most failure cost?
4. Does the proposed strategy reach the target? The strategy: *shift 20% of volume from the cheapest carrier to the second-cheapest carrier on the three most problematic lanes*. The target: *a 12% reduction in total landed cost*.

---

## 3. Dataset Overview

| Item | Detail |
|---|---|
| Source | Kaggle: `nadhirmazariboufares/supply-chain-dataset` ("Meridian Supply Chain Dataset"), MIT licence |
| Nature | **Synthetic**, publisher-generated (Python/NumPy) |
| Size | 11 tables, 44,917 rows |
| Used for this audit | `shipment` (4,500), `shipment_line` (9,059), `carrier` (4), `warehouse` (4), `customer` (30), `product` (40) |
| Period | Ship dates from 1 Jan 2024 to 30 Dec 2025 |
| Carriers | CARR-1 Road ($0.40/kg, quoted 3 days), CARR-2 Rail ($0.25/kg, 5 days), CARR-3 Air ($2.50/kg, 1 day), CARR-4 Sea ($0.15/kg, 14 days) |
| Lanes | 20 = 4 origin warehouse regions × 5 destination customer regions |

**Data quality:** the data passed every structural check: no nulls, duplicate keys, orphan foreign keys, invalid dates or negative quantities in the tables used. One material inconsistency exists. The `on_time_flag` disagrees with the delivery dates for **2,224 of 4,500 shipments (49%)**. For example, Sea is quoted 14 days but every delivery arrives within 1 to 9 days, and Air is quoted 1 day yet most deliveries take longer. The flag is used as the SLA metric of record, and date-based transit times are reported separately with this caveat ([limitations.md](limitations.md)).

---

## 4. Methodology

1. **Clean and model.** Shipment lines are summed to one row per shipment *before* joining, so shipment-level flags are never multiplied by line count. Each shipment carries its carrier, lane, units, weight, revenue, goods value, freight and flags.
2. **True cost per shipment:**

   ```
   True Cost = Freight (actual)
             + Late penalty      = late flag    × shipment revenue × 2%
             + Damage write-off  = damaged flag × goods value      × 25%
             + Air reshipment    = damaged flag × weight × 25% × $2.50/kg (CARR-3 contract rate)
   ```

   Each component is computed once per shipment, so nothing is double-counted. A shipment that is both late and damaged incurs both a penalty and a write-off, because these are separate costs.
3. **Reliability:** on-time %, late %, damage rate and "successful delivery" (on time **and** undamaged), with 95% confidence intervals and two-proportion z-tests.
4. **Lanes:** failure cost per shipment, late %, damage %, quoted vs actual transit days, and freight-rate variation.
5. **Strategy test:** the moved volume is costed at *expected values* for both carriers on the same lane (lane freight/kg, lane late rate × penalty, lane damage rate × write-off and reshipment), which keeps the comparison like-for-like.
6. **Three-way reconciliation:** the same numbers come independently from PostgreSQL ([sql/carrier_audit.sql](sql/carrier_audit.sql)), Excel formulas ([excel/cost_model_excel.xlsx](excel/cost_model_excel.xlsx)) and Python. They agree to the cent on every shipment.

| Assumption | Value | Why |
|---|---|---|
| Late penalty | 2% of shipment revenue | Mid-to-low point of typical B2B on-time service credits (1–5%); tested from 0 to 15% |
| Damage write-off | 25% of units in a damaged shipment | Partial damage rather than total loss |
| Reshipment | Written-off units re-sent by Air at $2.50/kg | CARR-3 contract rate, taken from the data |

---

## 5. Carrier Performance Findings

| Carrier | Shipments | Contract $/kg | Freight cost | Failure cost (modelled) | **True cost** | **True cost / unit** | On-time % | Damage rate | True cost / successful delivery |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CARR-4 (Sea) | 1,186 | $0.15 | $1,001,147 | $1,024,430 | **$2,025,577** | **$3.94** | 84.8% | 4.30% | $2,107.78 |
| CARR-2 (Rail) | 1,098 | $0.25 | $1,509,684 | $776,197 | **$2,285,882** | **$4.84** | 86.6% | 3.92% | $2,492.78 |
| CARR-1 (Road) | 1,091 | $0.40 | $2,498,056 | $898,825 | **$3,396,880** | **$6.93** | 86.0% | 4.22% | $3,774.31 |
| CARR-3 (Air) | 1,125 | $2.50 | $16,068,162 | $871,501 | **$16,939,663** | **$34.44** | 86.1% | 4.18% | $18,195.13 |
| **Network** | **4,500** | | **$21,077,049** | **$3,570,953** | **$24,648,002** | **$12.52** | **85.9%** | **4.16%** | **$6,645.46** |

* The **contract-rate ranking and the true-cost ranking are identical** (Sea < Rail < Road < Air).
* **CARR-4 (Sea)** has the worst on-time rate and the highest damage rate. It also ships the most units, so its failure costs are the highest in absolute terms. Even so, its freight advantage ($0.16/kg vs Rail's $0.26/kg) is far larger than the extra failure cost.
* **CARR-2 (Rail)** has the best on-time and damage rates, and the best composite score (98.5/100: 50% true cost, 30% on-time, 20% damage).
* **CARR-3 (Air)** costs about 10× more per kg than Rail, yet is *not* more reliable on any measure in this data.

---

## 6. True Cost Analysis

**Why the cheapest carrier *can* be the most expensive, and why it is not here.** A carrier with a low rate but poor service pushes cost into other budgets. The customer is credited for late deliveries, damaged stock is written off, and replacements are sent by premium freight. Those costs scale with the *value* of the goods, while freight scales with *weight*. With high-value, light goods, a cheap but unreliable carrier can easily cost more than a dearer, reliable one.

Meridian's numbers show the effect clearly but not decisively:

| | CARR-4 (Sea) | CARR-2 (Rail) | Gap (Sea − Rail) |
|---|---:|---:|---:|
| Freight / unit | $1.95 | $3.20 | **−$1.25** |
| Failure cost / unit | $1.99 | $1.64 | **+$0.35** |
| **True cost / unit** | **$3.94** | **$4.84** | **−$0.90** |
| Hidden-cost uplift over freight | 102% | 51% | |

Sea's poorer service costs about $0.35 per unit, but its freight saving is $1.25 per unit, so it stays cheaper.

**Sensitivity: how high would penalties have to be?**

| Late-penalty rate | Sea $/unit | Rail $/unit | Road $/unit | Air $/unit | Cheapest |
|---|---:|---:|---:|---:|---|
| 0% | 3.45 | 4.40 | 6.40 | 33.97 | Sea |
| 2% (base) | 3.94 | 4.84 | 6.93 | 34.44 | Sea |
| 5% | 4.68 | 5.50 | 7.71 | 35.14 | Sea |
| 10% | 5.91 | 6.60 | 9.03 | 36.30 | Sea |
| 15% | 7.14 | 7.69 | 10.34 | 37.47 | Sea |

The **break-even late-penalty rate is 35.8% of shipment revenue**. Only above that level would Sea's true cost exceed Rail's, which is far outside any normal contract.

---

## 7. Reliability Analysis

| Carrier | On-time % (95% CI) | Late % | Damage rate (95% CI) | Successful deliveries | Avg actual transit (quoted) |
|---|---|---:|---|---:|---|
| CARR-2 (Rail) | 86.6% (84.5–88.5) | 13.4% | 3.9% (2.9–5.2) | 917 (83.5%) | 4.90 d (5) |
| CARR-3 (Air) | 86.1% (84.0–88.0) | 13.9% | 4.2% (3.2–5.5) | 931 (82.8%) | 5.07 d (1) |
| CARR-1 (Road) | 86.0% (83.8–87.9) | 14.0% | 4.2% (3.2–5.6) | 900 (82.5%) | 4.92 d (3) |
| CARR-4 (Sea) | 84.8% (82.7–86.8) | 15.2% | 4.3% (3.3–5.6) | 961 (81.0%) | 5.18 d (14) |

* **No pairwise difference in on-time or damage rate is significant at the 5% level.** The largest gap, Rail vs Sea on-time, gives z = 1.22 and p = 0.22. Statistically, the four carriers are equally reliable.
* As a result, **reliability cannot justify a price premium** in negotiations: not for Air over Rail, and not for Road over Rail.
* Transit times: by the dates, every carrier averages about 5 days, so Air's 1-day promise and Sea's 14-day quote are both far from what the data records. Because the dates contradict the on-time flag, transit days are **not** used to rank carriers (see [limitations.md](limitations.md)).

---

## 8. Problematic Shipping Lanes

**Network view (all carriers): highest failure cost per shipment**

| Rank | Lane | Shipments | Late % | Damage rate | Failure cost / shipment | True cost / shipment |
|---:|---|---:|---:|---:|---:|---:|
| 1 | West-EU → Central-EU | 147 | 18.4% | 5.44% | $1,830 | $6,853 |
| 2 | Asia → East-EU | 236 | 15.3% | 6.36% | $1,563 | $6,728 |
| 3 | East-EU → West-EU | 359 | 17.0% | 5.85% | $1,038 | $5,357 |
| 4 | Asia → Americas | 226 | 14.6% | 5.31% | $990 | $6,372 |
| 5 | East-EU → Central-EU | 147 | 11.6% | 6.12% | $968 | $5,299 |
| … | Network average | 225 | 14.1% | 4.16% | $794 | $5,477 |
| 20 | West-EU → Asia | 182 | 8.2% | 3.85% | $389 | $4,346 |

The worst lane, West-EU → Central-EU, has 2.3× the network failure cost per shipment. East-EU → Asia (21.3%) and West-EU → Americas (19.2%) have the highest late rates.

**CARR-4 (Sea) view, which selects the strategy lanes** (minimum 30 Sea shipments per lane):

| Lane | Sea shipments | Sea late % | Sea damage rate | Sea failure cost / shipment |
|---|---:|---:|---:|---:|
| West-EU → Central-EU | 37 | 16.2% | 13.5% | $3,422 |
| East-EU → West-EU | 96 | 16.7% | 6.3% | $1,694 |
| Asia → West-EU | 85 | 7.1% | 7.1% | $1,404 |

Note that each carrier–lane cell holds only 29 to 112 shipments. Lane-level rates for a single carrier are therefore noisy, and a ranking built on them partly reflects chance.

---

## 9. Carrier Comparison

| Criterion | 1st | 2nd | 3rd | 4th |
|---|---|---|---|---|
| Lowest contract rate | Sea | Rail | Road | Air |
| **Lowest true cost / unit** | **Sea** | Rail | Road | Air |
| Highest on-time % | Rail | Air | Road | Sea |
| Lowest damage rate | Rail | Air | Road | Sea |
| **Best overall (composite)** | **Rail (98.5)** | Road (68.8) | Sea (50.0) | Air (28.3) |

*Composite = 50% true cost per unit + 30% on-time % + 20% damage rate, each scaled from 0 to 1 across carriers.* Sea's low composite score reflects its last-place reliability. Since that reliability gap is not statistically significant, cost should carry the most weight in contract decisions.

---

## 10. Financial Implications

### 10.1 The proposed strategy: 20% shift, Sea → Rail, on the 3 most problematic lanes

| Lane | Moved weight (kg) | Cost of moved volume on Sea | Cost on Rail | Change |
|---|---:|---:|---:|---:|
| West-EU → Central-EU | 35,059 | $22,964 | $15,953 | **−$7,011** |
| East-EU → West-EU | 108,118 | $40,571 | $42,905 | **+$2,335** |
| Asia → West-EU | 92,742 | $34,512 | $39,736 | **+$5,224** |
| **Total** | **235,919** | **$98,047** | **$98,594** | **+$548** |

| Measure | Result |
|---|---|
| Change vs network true cost ($24.65M) | **+0.002%** |
| Change vs true cost on the three lanes ($4.51M) | +0.012% |
| Change needed for the 12% target | −$2,957,760 |
| **Verdict** | **Target not supported.** The strategy is roughly cost-neutral. |

**Why it fails:** (a) the volume moved is tiny, about $98K of cost against a $24.6M network. (b) On two of the three lanes, Rail's higher freight rate outweighs its lower failure rates. (c) Even a perfect outcome on this volume could not save more than about 0.4% of network cost. Under its own assumptions, the 12% target is unreachable.

The only positive part is **West-EU → Central-EU**, which saves about $7K. There, Sea's damage rate (13.5%) is far above Rail's (3.1%), although on just 37 and 32 shipments.

### 10.2 Alternative lever: move Air volume to Rail

| Share of Air weight moved to Rail | Weight moved | Projected saving | % of network true cost |
|---:|---:|---:|---:|
| 5% | 306,074 kg | $725,485 | 2.9% |
| 10% | 612,147 kg | $1,450,970 | 5.9% |
| 15% | 918,221 kg | $2,176,454 | 8.8% |
| **20%** | 1,224,295 kg | **$2,901,939** | **11.8%** |
| 25% | 1,530,368 kg | $3,627,424 | 14.7% |
| 30% | 1,836,442 kg | $4,352,909 | 17.7% |

Moving **20.4% of Air weight** (about 1.25M kg) reaches the 12% target. The saving is about $2.37 per kg moved: Air's expected true cost is about $2.77/kg against Rail's $0.40/kg for the same goods. **Caveat:** the data does not record shipment urgency or customer-required delivery windows. The share of Air volume that can actually move must be confirmed with Sales and Operations before it is contracted.

### 10.3 Contract levers on CARR-4 (illustrative arithmetic, not a projection)

CARR-4's modelled damage write-off and reshipment cost is **$771,331** over two years. If a new contract made the carrier liable for half of that through a damage-claims clause, Meridian would recover about **$385,700**, or 1.6% of network true cost, without moving any volume.

---

## 11. Strategic Recommendations

1. **Do not adopt the 20% Sea→Rail reallocation as the route to 12%.** The data shows it is cost-neutral (+$548).
2. **Keep CARR-4 (Sea) as the cost backbone, and renegotiate its *terms* rather than its volume.**
   - Add an on-time SLA with service credits, since 15.2% of its shipments are late.
   - Add damage liability or claims recovery, since its damage rate of 4.3% is the highest.
   - Require correct transit-time reporting, since its quoted 14 days does not match the recorded dates.
3. **Make CARR-2 (Rail) the preferred carrier for overall value** (rank 1 on the composite). Use its best-in-class on-time and damage rates as the benchmark in every other negotiation.
4. **Open a structured Air reduction programme.** Classify Air shipments by real urgency, then move non-urgent volume to Rail in phases, targeting about 20% of Air weight (about $2.9M, about 12% of true cost). Air shows no reliability premium, so its rate should be challenged.
5. **Use a lane-selective approach.** On West-EU → Central-EU, where Sea's damage rate is unusually high, a partial move to Rail is justified. Elsewhere, decide lane by lane on true cost, not on contract rate.
6. **Fix the data before the next review.** Reconcile `on_time_flag` with the delivery dates, and capture actual penalties, claims and reshipment costs, so that true cost is measured rather than modelled.

---

## 12. Implementation Plan

| Phase | Timing | Actions | Owner | Success measure |
|---|---|---|---|---|
| 0. Data validation | Weeks 1–2 | Reconcile on-time flags with dates; pull actual credit-note, claims and expedite costs; tag Air shipments by urgency | Logistics analytics, Finance | Penalty and reshipment costs measured, not modelled |
| 1. Negotiation prep | Weeks 2–4 | Share this brief and the dashboard; set target terms: Sea SLA and damage clause, Air rate challenge, Rail volume commitment | Logistics Manager, Procurement | Negotiation pack approved |
| 2. Carrier negotiations | Weeks 4–8 | Sea: SLA credits plus damage liability. Rail: capacity and rate for extra volume. Air: rate reduction tied to lower volume | Procurement | Signed terms |
| 3. Pilot | Months 3–4 | Move about 5% of non-urgent Air weight to Rail; partial Sea→Rail move on West-EU → Central-EU | Operations | Saving ≥ 2.5% of true cost with on-time ≥ 85% |
| 4. Scale | Months 5–9 | Increase the Air→Rail shift towards about 20% if the pilot holds | Operations, Logistics | True cost down by about 12% against baseline |
| 5. Monitor | Ongoing | Monthly carrier scorecard from `carrier_audit.sql`, with the dashboard refreshed | Logistics analytics | Hidden-cost uplift tracked per carrier |

---

## 13. Risks and Limitations

* **Synthetic data.** The dataset is generated and its patterns are by construction. In particular, reliability is nearly uniform across carriers by design.
* **Modelled costs.** Penalties, write-offs and reshipments rest on assumptions. Conclusions about Sea vs Rail hold up to a 35.8% penalty rate, but absolute true-cost figures move with the assumptions.
* **Flag/date inconsistency.** Because on-time flags and dates disagree in 49% of shipments, transit-time findings are unreliable.
* **Small cells.** Carrier–lane samples (29 to 112 shipments) make lane-level selection noisy.
* **Air urgency is unknown.** The Air→Rail saving assumes the moved volume can tolerate Rail transit times. Customer service risk must be assessed.
* **Capacity and rate response.** The projections assume current per-kg rates hold when volume moves. Carriers may reprice.

Full list: [limitations.md](limitations.md).

---

## 14. Conclusion

On a true-cost basis, Meridian's cheapest carrier is still its cheapest. Late deliveries and damage double CARR-4's effective cost, but not by enough to overturn its freight advantage. The proposed reallocation of 20% of Sea volume on three lanes is cost-neutral and cannot deliver a 12% reduction. The money is in **Air**: three-quarters of freight spend buys no measurable reliability benefit. A disciplined, urgency-based move of about a fifth of Air volume to Rail, combined with SLA and damage-liability terms for Sea, is the evidence-based route to the 12% target.

*Supporting material: [Excel cost model](excel/cost_model_excel.xlsx) · [SQL audit](sql/carrier_audit.sql) · [Interactive dashboard](dashboard/carrier_negotiation_dashboard.html) · [Methodology](methodology.md) · [Recommendations](business_recommendations.md)*
