# Executive Summary - Logistics Carrier Performance & Cost Audit

**Question:** Is our cheapest carrier secretly the most expensive once late deliveries, damage, penalties and reshipments are counted? Would shifting 20% of its volume to the second-cheapest carrier on the three worst lanes cut landed cost by 12%?

**Data:** Meridian Supply Chain Dataset (Kaggle, synthetic, fictional company). 4,500 shipments, 4 carriers, 20 lanes, 2024–2025. Penalty, damage and reshipment costs are modelled (2% of revenue / 25% write-off / Air reshipment).

## Headline numbers

| Shipments | Freight cost | True cost | On-time | Damage rate | True cost / successful delivery |
|---:|---:|---:|---:|---:|---:|
| 4,500 | $21.08M | $24.65M | 85.9% | 4.16% | $6,645 |

## Answers

1. **No, the cheapest carrier is still the cheapest.** CARR-4 (Sea) costs $3.94 per unit all-in, against $4.84 for Rail, $6.93 for Road and $34.44 for Air. Penalties would have to reach 35.8% of revenue to change the ranking.
2. **Its hidden costs are nonetheless large.** Sea's modelled failure costs ($1.02M) exceed its freight bill ($1.00M). That is negotiation leverage for SLA and damage clauses.
3. **Carriers are equally reliable.** On-time ranges from 84.8% to 86.6% and damage from 3.9% to 4.3%. No difference is statistically significant.
4. **The proposed strategy does not work.** The 20% Sea→Rail shift on 3 lanes changes true cost by **+$548 (+0.002%)**, against a −12% (−$2.96M) target.
5. **Air is the opportunity.** It takes 76% of freight spend for 25% of the weight, with no reliability advantage. Moving about 20% of Air weight to Rail saves about **$2.9M ≈ 12%**, subject to confirming that the volume is not urgent.

## Recommended actions

| Action | Impact |
|---|---|
| Keep Sea; add SLA credits and damage liability to its contract | Recovers part of $1.02M in failure cost (for example, about $386K if half of damage costs are recovered) |
| Make Rail the preferred carrier and the negotiation benchmark | Best overall value (composite 98.5/100) |
| Pilot a 5% move of non-urgent Air volume to Rail, then scale towards 20% | About $0.7M at the pilot, about $2.9M at 20% |
| Move part of the Sea volume on West-EU → Central-EU only | −$7K; the one lane where the shift pays |
| Reconcile on-time flags with dates; record actual penalties and claims | Turns modelled costs into measured costs |

**Bottom line:** do not move volume away from the cheapest carrier. Tighten its contract, and take the 12% from Air.

→ Full brief: [../Negotiation_Brief.md](../Negotiation_Brief.md) · Dashboard: [../dashboard/carrier_negotiation_dashboard.html](../dashboard/carrier_negotiation_dashboard.html) · Model: [../excel/cost_model_excel.xlsx](../excel/cost_model_excel.xlsx)
