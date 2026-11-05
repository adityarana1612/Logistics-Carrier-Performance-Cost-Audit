# Cost Analysis

*Source: `data/processed/carrier_scorecard.csv`, `reallocation_scenario.csv`, `mode_shift_scenario.csv`, `penalty_sensitivity.csv`, `sql/carrier_audit.sql` §C and §F, Excel `Carrier_Cost_Analysis` and `Cost_Model`. Penalty, damage and reshipment costs are **modelled** (2% of revenue / 25% write-off / Air $2.50 per kg). Synthetic data.*

## 1. True cost by carrier

| Carrier | Freight | Late penalty | Damage write-off | Air reshipment | Failure cost | **True cost** | Share of network |
|---|---:|---:|---:|---:|---:|---:|---:|
| CARR-1 Road | $2,498,056 | $257,518 | $473,554 | $167,752 | $898,825 | **$3,396,880** | 13.8% |
| CARR-2 Rail | $1,509,684 | $207,501 | $439,542 | $129,154 | $776,197 | **$2,285,882** | 9.3% |
| CARR-3 Air | $16,068,162 | $229,242 | $499,889 | $142,371 | $871,501 | **$16,939,663** | 68.7% |
| CARR-4 Sea | $1,001,147 | $253,099 | $592,815 | $178,516 | $1,024,430 | **$2,025,577** | 8.2% |
| **Network** | **$21,077,049** | **$947,360** | **$2,005,800** | **$617,793** | **$3,570,953** | **$24,648,002** | 100% |

True cost is **16.9% above** the freight invoice network-wide. Damage-related costs (write-off plus reshipment, $2.62M) are 2.8× the late penalties.

## 2. Unit economics

| Carrier | Contract $/kg | Actual freight $/kg | Freight / shipment | **True cost / shipment** | Freight / unit | **True cost / unit** | Freight / on-time delivery | **True cost / successful delivery** | Hidden-cost uplift |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CARR-4 Sea | $0.15 | $0.1576 | $844 | **$1,708** | $1.95 | **$3.94** | $995 | **$2,108** | **102.3%** |
| CARR-2 Rail | $0.25 | $0.2626 | $1,375 | **$2,082** | $3.20 | **$4.84** | $1,587 | **$2,493** | 51.4% |
| CARR-1 Road | $0.40 | $0.4204 | $2,290 | **$3,114** | $5.09 | **$6.93** | $2,663 | **$3,774** | 36.0% |
| CARR-3 Air | $2.50 | $2.6249 | $14,283 | **$15,057** | $32.67 | **$34.44** | $16,582 | **$18,195** | 5.4% |
| Network | | $0.8722 | $4,684 | $5,477 | $10.71 | $12.52 | $5,455 | $6,645 | 16.9% |

### Why the cheapest carrier *could* be the most expensive, and why it is not here
Freight scales with **weight**. Failure costs scale with **value**: revenue for penalties, goods cost for write-offs. Every carrier carries the same product mix, so failure cost per unit is similar across carriers, at $1.64 to $1.99. In relative terms, though, it is enormous for a cheap carrier: Sea's failure cost per unit ($1.99) is larger than its freight per unit ($1.95). Its true cost is double its invoice.

The cheapest carrier would become the most expensive only if its failure gap over the next carrier exceeded its freight advantage. For Sea vs Rail:

| per unit | Sea | Rail | Sea − Rail |
|---|---:|---:|---:|
| Freight | $1.95 | $3.20 | −$1.25 |
| Failure cost | $1.99 | $1.64 | +$0.35 |
| **True cost** | **$3.94** | **$4.84** | **−$0.90** |

The failure gap (+$0.35) is only 28% of the freight advantage (−$1.25), so Sea stays cheapest.

## 3. Sensitivity to the penalty assumption

| Late penalty (% of revenue) | Road | Rail | Air | Sea | Cheapest |
|---:|---:|---:|---:|---:|---|
| 0% | $6.40 | $4.40 | $33.97 | $3.45 | Sea |
| 1% | $6.66 | $4.62 | $34.20 | $3.69 | Sea |
| **2% (base)** | **$6.93** | **$4.84** | **$34.44** | **$3.94** | **Sea** |
| 3% | $7.19 | $5.06 | $34.67 | $4.19 | Sea |
| 5% | $7.71 | $5.50 | $35.14 | $4.68 | Sea |
| 7.5% | $8.37 | $6.05 | $35.72 | $5.30 | Sea |
| 10% | $9.03 | $6.60 | $36.30 | $5.91 | Sea |
| 15% | $10.34 | $7.69 | $37.47 | $7.14 | Sea |

**Break-even: 35.8%.** Sea's true cost per unit equals Rail's only if each late shipment costs 35.8% of its revenue in penalties, which is not a realistic contract term.

## 4. Proposed strategy: 20% Sea → Rail on the 3 most problematic lanes

| Lane | Moved kg | Moved revenue | Sea freight/kg | Rail freight/kg | Sea late / damage | Rail late / damage | Baseline (Sea) | Scenario (Rail) | Change |
|---|---:|---:|---:|---:|---|---|---:|---:|---:|
| West-EU → Central-EU | 35,059 | $635,583 | $0.1610 | $0.2637 | 16.2% / 13.5% | 25.0% / 3.1% | $22,964 | $15,953 | **−$7,011** |
| East-EU → West-EU | 108,118 | $1,552,270 | $0.1572 | $0.2655 | 16.7% / 6.3% | 15.8% / 3.2% | $40,571 | $42,905 | **+$2,335** |
| Asia → West-EU | 92,742 | $1,365,106 | $0.1562 | $0.2558 | 7.1% / 7.1% | 9.2% / 5.3% | $34,512 | $39,736 | **+$5,224** |
| **Total** | **235,919** | **$3,552,959** | | | | | **$98,047** | **$98,594** | **+$548** |

| Result | Value |
|---|---:|
| Network true cost | $24,648,002 |
| Projected change | **+$548** |
| As % of network | **+0.002%** |
| As % of the three lanes' true cost ($4,505,077) | +0.012% |
| Required for 12% | −$2,957,760 |
| **Verdict** | **Target not supported by the data** |

The hypothesis fails on scale and on direction. The moved slice is worth about 0.4% of network cost, and Rail's freight premium offsets its lower failure rates on 2 of the 3 lanes.

## 5. Alternative: Air → Rail mode shift

Expected true cost per kg of Air's freight mix: **$2.77 on Air** vs **$0.40 on Rail**, a saving of **$2.37 per kg moved**.

| Air weight moved | kg | Saving | % of network true cost |
|---:|---:|---:|---:|
| 5% | 306,074 | $725,485 | 2.94% |
| 10% | 612,147 | $1,450,970 | 5.89% |
| 15% | 918,221 | $2,176,454 | 8.83% |
| 20% | 1,224,295 | $2,901,939 | 11.77% |
| **20.4%** | **≈1,247,800** | **$2,957,760** | **12.00%** |
| 25% | 1,530,368 | $3,627,424 | 14.72% |
| 30% | 1,836,442 | $4,352,909 | 17.66% |

Condition: the moved volume must not need Air speed. The data does not record urgency.

## 6. Spend concentration

| Carrier | % of freight spend | % of weight | % of shipments | On-time % |
|---|---:|---:|---:|---:|
| CARR-3 Air | **76.2%** | 25.3% | 25.0% | 86.1% |
| CARR-1 Road | 11.9% | 24.6% | 24.2% | 86.0% |
| CARR-2 Rail | 7.2% | 23.8% | 24.4% | 86.6% |
| CARR-4 Sea | 4.7% | 26.3% | 26.4% | 84.8% |

Three-quarters of freight spend goes on a quarter of the volume, with no reliability return. That is where the negotiation leverage and the savings are.
