# Requirements and Assumptions

## 1. Business requirements

| # | Requirement | Where it is met |
|---|---|---|
| R1 | Calculate the true cost of each carrier (freight + late penalties + damage + reshipment) | `sql/carrier_audit.sql` §C · Excel `Carrier_Cost_Analysis` · dashboard Cost view |
| R2 | True cost per shipment, per unit and per successful on-time delivery | Same as R1 |
| R3 | Evaluate reliability: on-time %, late %, damage rate, quoted vs actual transit | SQL §B · Excel `Carrier_Performance` · dashboard Reliability view |
| R4 | Identify problematic origin-to-destination lanes | SQL §D · Excel `Lane_Analysis` · dashboard lane section |
| R5 | Rank carriers by true cost, reliability, damage and overall | SQL §E · Excel `Carrier_Performance` · dashboard tables |
| R6 | Test: shift 20% of volume from the cheapest to the 2nd-cheapest carrier on the 3 most problematic lanes. Treat the 12% landed-cost reduction as a **hypothesis** | SQL §F.2–F.3 · Excel `Cost_Model` §3 · Negotiation Brief §10 |
| R7 | Recommend an optimal carrier allocation | Negotiation Brief §11 · `business_recommendations.md` |
| R8 | Deliverables usable without installing software | Excel workbook, self-contained HTML dashboard, Markdown reports |

## 2. Scope

* **In scope:** outbound shipments (`shipment`, `shipment_line`) and the dimension tables needed to cost them (`carrier`, `warehouse`, `customer`, `product`), Jan 2024 – Dec 2025.
* **Profiled but out of scope:** procurement (`supplier`, `purchase_order`, `purchase_order_line`), `inventory_snapshot` and `production_run`. They do not describe carrier performance.

## 3. Business definitions

| Term | Definition used |
|---|---|
| Carrier | Each of the 4 rows in `carrier`, labelled `CARR-n (Mode)` |
| Lane | Origin warehouse region → destination customer region (20 combinations) |
| Cheapest carrier | Lowest contracted `cost_per_kg` in the rate card: CARR-4 (Sea, $0.15). Second cheapest: CARR-2 (Rail, $0.25) |
| On-time / late | Source `on_time_flag` = 1 / 0 (metric of record) |
| Successful delivery | On time **and** not damaged |
| Quoted transit days | `carrier.avg_transit_days` (the carrier's contracted transit time) |
| Actual transit days | `delivery_date − ship_date` in calendar days |
| Units | Sum of `qty_shipped` across a shipment's lines |
| Total landed cost (for the 12% test) | Network true cost = sum of true cost over all 4,500 shipments ($24.65M). This is the most generous denominator for the hypothesis. Product cost is excluded because the strategy does not change it |
| Most problematic lane (for the strategy) | Highest **failure cost per shipment** for the cheapest carrier, among lanes where it has at least 30 shipments |

## 4. Cost-model assumptions

The dataset contains freight cost, on-time and damage flags, but **no penalty, claim or reshipment amounts**. These components are modelled. The same parameters are used everywhere: `scripts/build_analysis.py` (`ASSUMPTIONS`), SQL table `audit.audit_params`, Excel `Cost_Model!C6:C12`, and the dashboard sliders.

| Parameter | Value | Basis | Sensitivity tested |
|---|---|---|---|
| Late-delivery penalty | **2% of shipment revenue** per late shipment | Typical B2B on-time service credits fall at 1–5% of invoice value; 2% is a conservative mid-low point | 0% – 15%; break-even 35.8% |
| Damage write-off | **25% of the units** in a damaged shipment, at standard cost | Damaged shipments are usually partial losses; the dataset flags damage per shipment, not per unit | 0% – 100% (dashboard slider) |
| Expedited reshipment | Written-off units re-sent by **Air at $2.50/kg** (CARR-3 contract rate) | Uses an actual rate from `carrier.csv` | Moves with the write-off share |
| Strategy volume shift | 20% of the cheapest carrier's weight, revenue and goods value on each selected lane | Given in the brief | Editable in Excel `Cost_Model!C9` |
| Problem lanes | 3, with at least 30 shipments for the cheapest carrier | Given in the brief; the minimum avoids tiny samples | Editable in `Cost_Model!C11` |
| Target | 12% reduction of network true cost | Given in the brief (hypothesis) | Editable in `Cost_Model!C12` |
| Composite ranking weights | 50% true cost per unit, 30% on-time %, 20% damage rate | Cost-led procurement weighting | Editable in `Cost_Model!C71:C73` |

### Double-counting rules
1. Shipment lines are summed to shipment level **before** any join to shipment-level data.
2. Each cost component is computed once per shipment from a single flag.
3. A shipment that is both late and damaged gets both a penalty and a write-off/reshipment. These are distinct cash costs: a credit to the customer, a loss of goods, and freight for the replacement.
4. Freight for the *original* shipment is never reduced or repeated. Reshipment is an additional Air movement of the replaced units only.

### Scenario costing rule
Moved volume is valued at **expected cost** for both the current and the new carrier on the same lane:

```
expected cost = kg × lane freight/kg
              + revenue × lane late rate × penalty rate
              + goods value × lane damage rate × write-off share
              + kg × lane damage rate × write-off share × Air $/kg
```

This keeps the comparison like-for-like and avoids treating random historical failures as certain.

## 5. Technical requirements and environment

| Item | Choice |
|---|---|
| SQL dialect | PostgreSQL 13+ (validated on 16.2). Date differences use `date − date` (integer days), not `DATEDIFF` |
| SQL client | `psql`, run from the repository root (`\copy` uses relative paths) |
| Spreadsheet | Excel 2010 or later. Only Excel-2007-era functions are used (no dynamic arrays). The workbook recalculates fully on open |
| Dashboard | Any modern browser. Single HTML file, no external requests |
| Reproducibility (optional) | `scripts/` regenerates all outputs with Python 3.10+, pandas, openpyxl and formulas. Already run; not needed to use the deliverables |
