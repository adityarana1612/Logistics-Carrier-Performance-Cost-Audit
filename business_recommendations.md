# Business Recommendations

*Based on the Meridian Supply Chain Dataset (synthetic). Costs marked "modelled" depend on the assumptions in [requirements_and_assumptions.md](requirements_and_assumptions.md).*

## Summary

| # | Recommendation | Financial basis | Priority |
|---|---|---|---|
| 1 | Do **not** use the 20% Sea→Rail shift on 3 lanes as the route to 12% | Projected change **+$548 (+0.002%)** | Immediate |
| 2 | Keep CARR-4 (Sea) as the cost backbone and renegotiate its **terms**: SLA credits and damage liability | Lowest true cost ($3.94/unit). Modelled failure cost of $1.02M exceeds its freight bill | High |
| 3 | Make CARR-2 (Rail) the **preferred carrier** and the negotiation benchmark | Best composite score (98.5). Best on-time (86.6%) and damage (3.9%) rates | High |
| 4 | Launch an **urgency-based Air→Rail programme**: pilot 5%, scale towards about 20% of Air weight | About $2.9M ≈ **11.8%** of network true cost at 20%; 20.4% reaches 12% | High |
| 5 | Move part of the Sea volume on **West-EU → Central-EU** only | Only lane where the shift saves money (−$7,011 on the 20% slice) | Medium |
| 6 | Challenge the Air **rate**: no reliability premium is demonstrated | Air 86.1% on-time vs Rail 86.6% (not significant) | Medium |
| 7 | Fix the **data**: reconcile on-time flags with dates; capture actual penalties, claims and expedites | 49% of shipments have a flag/date conflict | Medium |

## 1. Reject the proposed reallocation as framed
The strategy moves a slice of volume whose total cost is only about $98K (0.4% of network true cost). Even if that cost fell to zero, the saving could not approach 12%. On two of the three selected lanes, Rail's higher freight rate outweighs its better failure rates.

## 2. Negotiate Sea's terms, not its volume
CARR-4 (Sea) is the cheapest carrier on every cost measure: per unit, per shipment and per successful delivery. Its weakness is service: last on on-time rate (84.8%) and damage rate (4.3%). Contract asks:

* **On-time SLA with service credits.** For example, credit X% of freight for each late shipment above a 90% on-time threshold.
* **Damage liability / claims recovery.** Its modelled write-off plus reshipment cost is **$771K** over two years; recovering half would return about **$386K** (illustrative arithmetic).
* **Accurate transit reporting.** Its quoted 14 days does not match the recorded delivery dates, and the discrepancy should be explained.

## 3. Make Rail the preferred carrier
Rail is the second-cheapest carrier ($4.84/unit) and the most reliable, so it is the best overall value. Use Rail's rates and performance as the benchmark when negotiating with Road and Air. Secure capacity for extra volume from Air.

## 4. Air → Rail mode-shift programme
Air takes **76% of freight spend for 25% of weight**, at $34.44 per unit, about 7× Rail's cost. It shows no measurable reliability advantage in this data.

| Air weight moved | Saving | % of network true cost |
|---:|---:|---:|
| 5% (pilot) | $0.73M | 2.9% |
| 10% | $1.45M | 5.9% |
| 20% | $2.90M | 11.8% |
| 20.4% | $2.96M | **12.0%** |

**Prerequisite:** classify Air shipments by real urgency (customer delivery window, product criticality). The dataset does not hold this, so the movable share is an assumption until it is validated.

## 5. Lane-selective adjustments
* **West-EU → Central-EU** is the worst lane network-wide ($1,830 failure cost per shipment, 2.3× average). Sea's damage rate there is 13.5% vs Rail's 3.1%. Move part of the Sea volume to Rail, and monitor, because samples are small (37 and 32 shipments).
* **East-EU → West-EU** and **Asia → West-EU**: keep Sea; moving to Rail raises cost.
* Investigate **East-EU → Asia** (21.3% late) and **West-EU → Americas** (19.2% late) with carriers, since these have the highest late rates.

## 6. Build measurement into the contracts
Track monthly with `sql/carrier_audit.sql` and the dashboard: true cost per unit, hidden-cost uplift, on-time % and damage rate by carrier and lane. Re-tender if a carrier's hidden-cost uplift rises more than 10 percentage points above baseline.

## Negotiation talking points

| Carrier | Position | Ask |
|---|---|---|
| CARR-4 Sea | "You are our lowest-cost partner, but late and damaged shipments cost us as much again as your freight." | SLA credits, damage liability, transit-time transparency |
| CARR-2 Rail | "You are our best-value carrier and we plan to grow your share." | Rate held or reduced for extra Air-converted volume; capacity guarantee |
| CARR-1 Road | "Your reliability is no better than Rail's at 1.6× the rate." | Rate reduction towards Rail parity, or a smaller share |
| CARR-3 Air | "We pay about 10× Rail per kg with no measurable reliability benefit." | Significant rate reduction; volume concentrated on genuinely urgent orders |
