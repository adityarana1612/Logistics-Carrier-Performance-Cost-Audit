# Methodology

## Step 1 - Acquisition
The Meridian Supply Chain Dataset was located on Kaggle (`nadhirmazariboufares/supply-chain-dataset`). Its metadata confirms 11 tables, about 45,000 rows, an MIT licence, and that the data is synthetic. It was downloaded through the Kaggle API. The 11 CSVs are stored **unaltered** in `data/raw/`.

## Step 2 - Profiling and data quality
Every table was profiled for row counts, data types, nulls, fully duplicated rows and duplicate primary keys. The shipment tables were also checked for orphan foreign keys, unparseable or reversed dates, invalid flag values, non-positive quantities, negative money values, repeated SKU lines, and agreement between `on_time_flag` and the dates. The results are in `data/processed/data_quality_report.csv` and are repeated in SQL §A.5.

Key outcomes:
* The tables used are structurally clean, so no rows were removed or imputed.
* 157 shipment–product pairs appear on two lines with different quantities. They were kept as legitimate split lines.
* `on_time_flag` disagrees with `delivery_date − ship_date` vs the quoted days for 2,224 shipments (49%). The flag is used for SLA metrics, and date-based transit is reported with a caveat.

## Step 3 - Relational model
Primary keys: every `*_id` column. Foreign keys:

```
carrier ─┐
warehouse├─< shipment >─┬─< shipment_line >── product
customer ┘              │
supplier ──< purchase_order ──< purchase_order_line >── product
warehouse, product ──< inventory_snapshot        product ──< production_run
```

These keys are enforced as constraints in `sql/carrier_audit.sql`, and the load succeeds with no violations.

## Step 4 - Shipment fact table (grain control)
1. `shipment_line` ⋈ `product` gives line weight (`qty × unit_weight_kg`) and goods value (`qty × standard_cost`).
2. **Aggregate to `shipment_id`**: line count, units, weight, revenue, goods value, freight.
3. Join the aggregated lines to `shipment`, `carrier`, `warehouse` and `customer`, one-to-one at shipment grain.
4. Derive the lane, actual transit days, variance, late flag and successful flag.
5. Add the modelled cost components and true cost (formulas in `requirements_and_assumptions.md` §4).

Output: `data/processed/shipment_fact.csv` (4,500 rows), Excel `Cleaned_Data`, SQL `v_shipment_true_cost`.

## Step 5 - Metrics
For any grouping (carrier, lane, carrier × lane, month, year):

| Metric | Formula |
|---|---|
| On-time % | Σ on_time_flag ÷ shipments |
| Late % | Σ late_flag ÷ shipments |
| Damage rate | Σ damaged_flag ÷ shipments |
| Success rate | Σ (on time and undamaged) ÷ shipments |
| Freight per kg | Σ freight ÷ Σ weight (weighted, not an average of ratios) |
| True cost per shipment / unit | Σ true cost ÷ shipments / Σ units |
| Freight per on-time delivery | Σ freight ÷ on-time shipments |
| True cost per successful delivery | Σ true cost ÷ successful shipments |
| Hidden-cost uplift | Σ true cost ÷ Σ freight − 1 |
| Failure cost per shipment | Σ (penalty + damage + reshipment) ÷ shipments |
| Transit variance | avg(actual days) − avg(quoted days) |
| Freight-rate CV (lane) | stdev(freight/kg per shipment) ÷ mean |

## Step 6 - Statistical testing
* **Wilson 95% confidence intervals** for on-time and damage rates (shown in the dashboard).
* **Two-proportion z-tests** for every carrier pair on on-time % and damage rate (`data/processed/significance_tests.csv`). None is significant at α = 0.05; the smallest p-value is 0.22.

## Step 7 - Ranking
`RANK()` on true cost per unit (ascending), on-time % (descending) and damage rate (ascending). The composite score min-max scales each measure across carriers to 0–1, with higher meaning better, then weights them 50/30/20.

## Step 8 - Strategy test
1. Cheapest and second-cheapest carriers come from the rate card: Sea and Rail.
2. The cheapest carrier's lanes with at least 30 shipments are ranked by failure cost per shipment, and the top 3 are taken.
3. For each lane, the moved volume = 20% × Sea's kg, revenue and goods value on that lane.
4. Baseline = expected cost of the moved volume at Sea's lane rates. Scenario = expected cost at Rail's lane rates on the same lane.
5. Change = scenario − baseline. This is compared with 12% × network true cost.

## Step 9 - Alternative lever and sensitivity
* **Air → Rail:** expected true cost per kg of Air's freight mix under each carrier's network-level rates. Saving = difference × kg moved, for 5% to 30% of Air weight. The share needed for 12% is solved directly.
* **Penalty sensitivity:** true cost per unit by carrier for penalty rates from 0 to 15%, plus the closed-form break-even rate at which Sea equals Rail.

## Step 10 - Independent reconciliation (validation)

| Check | Result |
|---|---|
| PostgreSQL 16.2 executes the whole script with `ON_ERROR_STOP=1` | Pass |
| SQL vs Python, every column of the 4,500-row fact table | Max difference **$0.00** |
| Line-level freight = fact-level freight | $21,077,048.77 = $21,077,048.77 |
| Excel: 37,041 formulas evaluated with an independent engine (`formulas` library) | **0 errors** |
| Excel vs SQL headline results (strategy change, required Air share, break-even, ranks, lanes) | Identical. Network true cost within $0.10 because of the engine's rounding of exact half-cent values |
| Dashboard (headless Chrome) vs SQL: KPIs, carrier table, scenario table | Identical |
| Dashboard filter, slider and sort interactions vs pandas | Identical |
