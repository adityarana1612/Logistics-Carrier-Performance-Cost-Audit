# Data Dictionary

**Dataset:** Meridian Supply Chain Dataset (Kaggle: `nadhirmazariboufares/supply-chain-dataset`, MIT licence).
**Nature:** synthetic, publisher-generated teaching data about the fictional manufacturer *Meridian Components*.
**Files:** `data/raw/*.csv` (11 tables, unaltered). Derived outputs are in `data/processed/`.

## Entity-relationship overview

```
                 ┌──────────┐
                 │ carrier  │ 4
                 └────┬─────┘
┌──────────┐          │            ┌──────────┐
│warehouse │ 4 ───────┼─────────── │ customer │ 30
└────┬─────┘          │            └──────────┘
     │          ┌─────▼──────┐
     │          │  shipment  │ 4,500 ──< shipment_line 9,059 >── product 40
     │          └────────────┘
     ├──< inventory_snapshot 16,800 >── product
     │
supplier 20 ──< purchase_order 3,000 ──< purchase_order_line 7,460 >── product
                                          production_run 4,000 >── product
```

## Table: `shipment` (4,500 rows) - outbound shipment header
| Column | Type | Key | Description |
|---|---|---|---|
| shipment_id | INTEGER | PK | Shipment identifier |
| ship_date | DATE | | Date shipped (2024-01-01 … 2025-12-30) |
| warehouse_id | INTEGER | FK → warehouse | Shipping warehouse (lane origin) |
| customer_id | INTEGER | FK → customer | Receiving customer (lane destination) |
| carrier_id | INTEGER | FK → carrier | Carrier used |
| delivery_date | DATE | | Date delivered (1–9 days after ship_date) |
| on_time_flag | SMALLINT 0/1 | | 1 = delivered on time (SLA metric of record) |
| damaged_flag | SMALLINT 0/1 | | 1 = arrived damaged |

## Table: `shipment_line` (9,059 rows) - shipment lines
| Column | Type | Key | Description |
|---|---|---|---|
| ship_line_id | INTEGER | PK | Line identifier |
| shipment_id | INTEGER | FK → shipment | Parent shipment |
| product_id | INTEGER | FK → product | Product shipped |
| qty_shipped | INTEGER | | Units (6–558) |
| revenue | NUMERIC | | Invoice value (= qty × list price) |
| freight_cost | NUMERIC | | Freight billed for the line |

## Table: `carrier` (4 rows) - rate card
| Column | Type | Key | Description |
|---|---|---|---|
| carrier_id | INTEGER | PK | 1–4 |
| carrier_name | TEXT | UNIQUE | CARR-1 … CARR-4 |
| mode | TEXT | | Road / Rail / Air / Sea |
| cost_per_kg | NUMERIC | | Contract rate: 0.40 / 0.25 / 2.50 / 0.15 |
| avg_transit_days | INTEGER | | Quoted transit days: 3 / 5 / 1 / 14 |
| co2_kg_per_km | NUMERIC | | Emission factor (not used) |
| reliability_score | NUMERIC | | Publisher's nominal score (not used; observed rates are used instead) |

## Table: `warehouse` (4 rows)
| Column | Type | Key | Description |
|---|---|---|---|
| warehouse_id | INTEGER | PK | 1–4 |
| warehouse_name | TEXT | | WH-1 … WH-4 |
| region | TEXT | | West-EU, Central-EU, East-EU, Asia (lane origin) |
| capacity_units, operating_cost_monthly, automation_level | | | Not used |

## Table: `customer` (30 rows)
| Column | Type | Key | Description |
|---|---|---|---|
| customer_id | INTEGER | PK | 1–30 |
| customer_name | TEXT | | CUST-001 … |
| region | TEXT | | West-EU (9), East-EU (6), Americas (6), Asia (5), Central-EU (4) (lane destination) |
| industry_segment, priority_tier, credit_limit, contract_type, since_year | | | Not used |

## Table: `product` (40 rows)
| Column | Type | Key | Description |
|---|---|---|---|
| product_id | INTEGER | PK | 1001–1040 |
| product_code | TEXT | UNIQUE | e.g. FAS-01 |
| category | TEXT | | Fasteners, Bearings, Casings, Electronics, Hydraulics |
| unit_weight_kg | NUMERIC | | Used for shipment weight |
| standard_cost | NUMERIC | | Used for damaged-goods write-off |
| list_price | NUMERIC | | Revenue / qty matches list price on every line |
| abc_class, hazardous, shelf_life_days | | | Not used |

## Out-of-scope tables (profiled, loaded with keys, not analysed)
| Table | Rows | PK | FKs | Note |
|---|---:|---|---|---|
| supplier | 20 | supplier_id | | |
| purchase_order | 3,000 | po_id | supplier_id | 193 NULL `actual_delivery_date` (open/cancelled POs) |
| purchase_order_line | 7,460 | po_line_id | po_id, product_id | |
| inventory_snapshot | 16,800 | snapshot_id | warehouse_id, product_id | Weekly stock levels |
| production_run | 4,000 | production_id | product_id | |

## Derived: `data/processed/shipment_fact.csv` (4,500 rows, one per shipment)
Also Excel `Cleaned_Data` and SQL view `audit.v_shipment_true_cost`.

| Column | Derivation | Type |
|---|---|---|
| shipment_id, ship_date, delivery_date | shipment | key / dates |
| ship_month, year | from ship_date | text / int |
| carrier_id, carrier, carrier_name, mode, cost_per_kg | carrier (`carrier` = "CARR-n (Mode)") | |
| warehouse_id, warehouse_name, origin_region | warehouse | |
| customer_id, customer_name, dest_region | customer | |
| lane | origin_region + " > " + dest_region | text |
| line_count | COUNT(lines) | int |
| units | Σ qty_shipped | int |
| weight_kg | Σ qty × unit_weight_kg | decimal |
| revenue | Σ revenue | $ |
| goods_cost | Σ qty × standard_cost | $ |
| quoted_transit_days | carrier.avg_transit_days | int |
| actual_transit_days | delivery_date − ship_date | int |
| transit_variance_days | actual − quoted | int |
| on_time_flag, damaged_flag | shipment | 0/1 |
| late_flag | 1 − on_time_flag | 0/1 |
| successful_flag | on_time = 1 AND damaged = 0 | 0/1 |
| freight_cost | Σ line freight (actual) | $ |
| late_penalty_cost | late_flag × revenue × 2% (**modelled**) | $ |
| damage_cost | damaged_flag × goods_cost × 25% (**modelled**) | $ |
| reshipment_cost | damaged_flag × weight_kg × 25% × $2.50 (**modelled**) | $ |
| true_cost | freight + penalty + damage + reshipment | $ |

## Other processed outputs
| File | Grain | Content |
|---|---|---|
| `data_quality_report.csv` | check | Every data-quality check with records affected and action |
| `carrier_scorecard.csv` | carrier | All cost and reliability metrics, ranks, composite score |
| `lane_scorecard.csv` | lane | Lane metrics, sorted by failure cost per shipment |
| `carrier_lane_scorecard.csv` | carrier × lane (80) | Same metrics per carrier per lane |
| `reallocation_scenario.csv` | strategy lane | Proposed 20% Sea → Rail test |
| `mode_shift_scenario.csv` | shift share | Air → Rail savings |
| `penalty_sensitivity.csv` | rate × carrier | True cost per unit at penalty rates 0–15% |
| `significance_tests.csv` | carrier pair × metric | Two-proportion z-tests |
| `monthly_carrier_trend.csv` | month × carrier | Shipments, on-time, damage, cost per unit |
| `summary_metrics.json` | network | Assumptions, totals, scenario results, break-even |
