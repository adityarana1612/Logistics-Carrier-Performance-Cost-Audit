/* =============================================================================
   LOGISTICS CARRIER PERFORMANCE & COST AUDIT
   -----------------------------------------------------------------------------
   Dialect      : PostgreSQL 13+ (tested on PostgreSQL 16)
   Client       : psql  (the data-load section uses psql's client-side \copy)
   Run from     : the repository root, so the relative CSV paths resolve:
                      psql -d <your_database> -f sql/carrier_audit.sql
   Source data  : Meridian Supply Chain Dataset (Kaggle, MIT licence) -
                  a SYNTHETIC dataset published for teaching/analytics practice.
                  Results describe the fictional company "Meridian Components".

   SECTIONS
     A. Database preparation  (schema, DDL, keys, load, validation, cleaning)
     B. Carrier scorecard
     C. True cost per shipment / per unit
     D. Lane analysis
     E. Carrier ranking
     F. Business recommendation support (strategy test, mode shift, sensitivity)

   COST MODEL NOTE
     The dataset contains freight cost, on-time and damage flags, but NO penalty
     or reshipment amounts. Those components are MODELLED from the parameters in
     table audit.audit_params (A.6). They match the Excel Cost_Model sheet and
     scripts/build_analysis.py, so all three deliverables reconcile.

   GRAIN / DOUBLE-COUNTING RULE
     shipment (1) -> shipment_line (many). Lines are ALWAYS aggregated to the
     shipment grain in a CTE/view BEFORE joining to shipment-level attributes,
     so shipment-level flags and penalties are never multiplied by line count.
   ============================================================================= */


/* =============================================================================
   A. DATABASE PREPARATION
   ============================================================================= */

-- A.1  Fresh schema ------------------------------------------------------------
DROP SCHEMA IF EXISTS audit CASCADE;
CREATE SCHEMA audit;
SET search_path TO audit;

-- A.2  Dimension tables ----------------------------------------------------------
CREATE TABLE carrier (
    carrier_id          INTEGER       PRIMARY KEY,
    carrier_name        VARCHAR(20)   NOT NULL UNIQUE,
    mode                VARCHAR(10)   NOT NULL,
    cost_per_kg         NUMERIC(8,3)  NOT NULL CHECK (cost_per_kg > 0),
    avg_transit_days    INTEGER       NOT NULL CHECK (avg_transit_days > 0),  -- quoted / contracted transit time
    co2_kg_per_km       NUMERIC(6,3),
    reliability_score   NUMERIC(4,2)  CHECK (reliability_score BETWEEN 0 AND 1)
);

CREATE TABLE warehouse (
    warehouse_id            INTEGER      PRIMARY KEY,
    warehouse_name          VARCHAR(20)  NOT NULL,
    region                  VARCHAR(20)  NOT NULL,
    capacity_units          INTEGER,
    operating_cost_monthly  NUMERIC(12,2),
    automation_level        VARCHAR(10)
);

CREATE TABLE customer (
    customer_id       INTEGER      PRIMARY KEY,
    customer_name     VARCHAR(20)  NOT NULL,
    industry_segment  VARCHAR(30),
    region            VARCHAR(20)  NOT NULL,
    priority_tier     VARCHAR(10),
    credit_limit      NUMERIC(14,2),
    contract_type     VARCHAR(15),
    since_year        INTEGER
);

CREATE TABLE product (
    product_id       INTEGER       PRIMARY KEY,
    product_code     VARCHAR(20)   NOT NULL UNIQUE,
    category         VARCHAR(20)   NOT NULL,
    unit_weight_kg   NUMERIC(10,3) NOT NULL CHECK (unit_weight_kg > 0),
    standard_cost    NUMERIC(10,2) NOT NULL CHECK (standard_cost >= 0),
    list_price       NUMERIC(10,2),
    abc_class        CHAR(1),
    hazardous        SMALLINT      CHECK (hazardous IN (0,1)),
    shelf_life_days  INTEGER
);

CREATE TABLE supplier (
    supplier_id         INTEGER      PRIMARY KEY,
    supplier_name       VARCHAR(30)  NOT NULL,
    country             VARCHAR(30),
    tier                VARCHAR(10),
    lead_time_days      INTEGER,
    quality_rating      NUMERIC(4,2),
    onboard_date        DATE,
    payment_terms_days  INTEGER,
    min_order_value     NUMERIC(12,2),
    is_single_source    SMALLINT     CHECK (is_single_source IN (0,1))
);

-- A.3  Transaction tables ---------------------------------------------------------
CREATE TABLE shipment (
    shipment_id    INTEGER   PRIMARY KEY,
    ship_date      DATE      NOT NULL,
    warehouse_id   INTEGER   NOT NULL REFERENCES warehouse (warehouse_id),
    customer_id    INTEGER   NOT NULL REFERENCES customer  (customer_id),
    carrier_id     INTEGER   NOT NULL REFERENCES carrier   (carrier_id),
    delivery_date  DATE,
    on_time_flag   SMALLINT  NOT NULL CHECK (on_time_flag IN (0,1)),
    damaged_flag   SMALLINT  NOT NULL CHECK (damaged_flag IN (0,1))
);

CREATE TABLE shipment_line (
    ship_line_id  INTEGER        PRIMARY KEY,
    shipment_id   INTEGER        NOT NULL REFERENCES shipment (shipment_id),
    product_id    INTEGER        NOT NULL REFERENCES product  (product_id),
    qty_shipped   INTEGER        NOT NULL,
    revenue       NUMERIC(14,2)  NOT NULL,
    freight_cost  NUMERIC(14,2)  NOT NULL
);

CREATE TABLE purchase_order (
    po_id                 INTEGER      PRIMARY KEY,
    order_date            DATE         NOT NULL,
    supplier_id           INTEGER      NOT NULL REFERENCES supplier (supplier_id),
    promised_date         DATE,
    actual_delivery_date  DATE,                     -- NULL for open / cancelled POs (193 rows)
    status                VARCHAR(20),
    expedited             SMALLINT     CHECK (expedited IN (0,1))
);

CREATE TABLE purchase_order_line (
    po_line_id    INTEGER        PRIMARY KEY,
    po_id         INTEGER        NOT NULL REFERENCES purchase_order (po_id),
    product_id    INTEGER        NOT NULL REFERENCES product (product_id),
    qty_ordered   INTEGER,
    qty_received  INTEGER,
    qty_rejected  INTEGER,
    unit_cost     NUMERIC(10,2)
);

CREATE TABLE inventory_snapshot (
    snapshot_id       INTEGER  PRIMARY KEY,
    snapshot_date     DATE     NOT NULL,
    warehouse_id      INTEGER  NOT NULL REFERENCES warehouse (warehouse_id),
    product_id        INTEGER  NOT NULL REFERENCES product (product_id),
    units_on_hand     INTEGER,
    reorder_point     INTEGER,
    units_reserved    INTEGER,
    units_in_transit  INTEGER
);

CREATE TABLE production_run (
    production_id   INTEGER  PRIMARY KEY,
    run_date        DATE     NOT NULL,
    plant_id        INTEGER,
    product_id      INTEGER  NOT NULL REFERENCES product (product_id),
    units_produced  INTEGER,
    defect_count    INTEGER,
    downtime_min    INTEGER,
    labor_hours     NUMERIC(8,2),
    shift           VARCHAR(10)
);

-- Helpful indexes for the analytical joins
CREATE INDEX ix_shipment_carrier   ON shipment (carrier_id);
CREATE INDEX ix_shipment_lane      ON shipment (warehouse_id, customer_id);
CREATE INDEX ix_shipline_shipment  ON shipment_line (shipment_id);

-- A.4  Load the raw CSVs (client-side, relative to the repository root) ---------
--      Parents are loaded before children so the foreign keys are enforced on load.
\copy carrier             FROM 'data/raw/carrier.csv'             WITH (FORMAT csv, HEADER true)
\copy warehouse           FROM 'data/raw/warehouse.csv'           WITH (FORMAT csv, HEADER true)
\copy customer            FROM 'data/raw/customer.csv'            WITH (FORMAT csv, HEADER true)
\copy product             FROM 'data/raw/product.csv'             WITH (FORMAT csv, HEADER true)
\copy supplier            FROM 'data/raw/supplier.csv'            WITH (FORMAT csv, HEADER true)
\copy shipment            FROM 'data/raw/shipment.csv'            WITH (FORMAT csv, HEADER true)
\copy shipment_line       FROM 'data/raw/shipment_line.csv'       WITH (FORMAT csv, HEADER true)
\copy purchase_order      FROM 'data/raw/purchase_order.csv'      WITH (FORMAT csv, HEADER true)
\copy purchase_order_line FROM 'data/raw/purchase_order_line.csv' WITH (FORMAT csv, HEADER true)
\copy inventory_snapshot  FROM 'data/raw/inventory_snapshot.csv'  WITH (FORMAT csv, HEADER true)
\copy production_run      FROM 'data/raw/production_run.csv'      WITH (FORMAT csv, HEADER true)

-- A.5  Data validation ------------------------------------------------------------

-- A.5.1 Row counts per table (expected total: 44,917 data rows across 11 tables)
SELECT 'carrier' AS table_name, COUNT(*) AS row_count FROM carrier
UNION ALL SELECT 'warehouse',           COUNT(*) FROM warehouse
UNION ALL SELECT 'customer',            COUNT(*) FROM customer
UNION ALL SELECT 'product',             COUNT(*) FROM product
UNION ALL SELECT 'supplier',            COUNT(*) FROM supplier
UNION ALL SELECT 'shipment',            COUNT(*) FROM shipment
UNION ALL SELECT 'shipment_line',       COUNT(*) FROM shipment_line
UNION ALL SELECT 'purchase_order',      COUNT(*) FROM purchase_order
UNION ALL SELECT 'purchase_order_line', COUNT(*) FROM purchase_order_line
UNION ALL SELECT 'inventory_snapshot',  COUNT(*) FROM inventory_snapshot
UNION ALL SELECT 'production_run',      COUNT(*) FROM production_run
ORDER BY table_name;

-- A.5.2 Data-quality checks on the tables used by the audit (0 = clean)
SELECT 'shipments without lines'                AS check_name,
       COUNT(*)                                 AS records_affected
FROM   shipment s
WHERE  NOT EXISTS (SELECT 1 FROM shipment_line l WHERE l.shipment_id = s.shipment_id)
UNION ALL
SELECT 'delivery_date before ship_date',  COUNT(*) FROM shipment WHERE delivery_date < ship_date
UNION ALL
SELECT 'missing delivery_date',           COUNT(*) FROM shipment WHERE delivery_date IS NULL
UNION ALL
SELECT 'non-positive qty_shipped',        COUNT(*) FROM shipment_line WHERE qty_shipped <= 0
UNION ALL
SELECT 'negative revenue / freight_cost', COUNT(*) FROM shipment_line WHERE revenue < 0 OR freight_cost < 0
UNION ALL
SELECT 'duplicate shipment lines (same shipment + product)', COUNT(*)
FROM  (SELECT shipment_id, product_id FROM shipment_line
       GROUP BY shipment_id, product_id HAVING COUNT(*) > 1) d
UNION ALL
SELECT 'POs with NULL actual_delivery_date (out of scope)', COUNT(*)
FROM   purchase_order WHERE actual_delivery_date IS NULL;

-- A.5.3 Consistency check: does on_time_flag agree with the dates?
--       Date-based "late" = actual transit days (delivery - ship) > quoted days.
--       FINDING: ~49% disagree, i.e. the flag was generated independently of the
--       dates. on_time_flag is kept as the SLA metric of record (see limitations.md).
SELECT c.carrier_name,
       c.avg_transit_days                                              AS quoted_days,
       COUNT(*)                                                        AS shipments,
       SUM(CASE WHEN (s.delivery_date - s.ship_date) > c.avg_transit_days THEN 1 ELSE 0 END) AS late_by_dates,
       SUM(1 - s.on_time_flag)                                         AS late_by_flag,
       SUM(CASE WHEN ((s.delivery_date - s.ship_date) > c.avg_transit_days)::int <> (1 - s.on_time_flag)
                THEN 1 ELSE 0 END)                                     AS disagreements
FROM   shipment s
JOIN   carrier  c ON c.carrier_id = s.carrier_id
GROUP  BY c.carrier_name, c.avg_transit_days
ORDER  BY c.carrier_name;

-- A.6  Cost-model parameters (single-row table; edit here to run sensitivities) --
CREATE TABLE audit_params (
    late_penalty_rate      NUMERIC(6,4) NOT NULL,  -- service credit as share of shipment revenue, per late shipment
    damage_writeoff_share  NUMERIC(6,4) NOT NULL,  -- share of units in a damaged shipment written off at standard cost
    reship_carrier_id      INTEGER      NOT NULL REFERENCES carrier (carrier_id), -- written-off units re-sent by this carrier (Air)
    shift_share            NUMERIC(6,4) NOT NULL,  -- strategy: share of volume shifted
    n_problem_lanes        INTEGER      NOT NULL,  -- strategy: number of lanes
    min_lane_shipments     INTEGER      NOT NULL,  -- minimum sample for a carrier-lane cell to be ranked
    target_reduction       NUMERIC(6,4) NOT NULL   -- hypothesis under test
);
INSERT INTO audit_params VALUES (0.02, 0.25, 3, 0.20, 3, 30, 0.12);

-- A.7  Cleaning layer -------------------------------------------------------------
--      The source passed every structural check, so cleaning is defensive: trim
--      text, keep only rows with valid dates / flags, and derive analysis fields.

-- A.7.1 Line totals rolled up to shipment grain (prevents one-to-many inflation)
CREATE VIEW v_shipment_lines AS
SELECT l.shipment_id,
       COUNT(*)                                   AS line_count,
       SUM(l.qty_shipped)                         AS units,
       SUM(l.qty_shipped * p.unit_weight_kg)      AS weight_kg,
       SUM(l.revenue)                             AS revenue,
       SUM(l.qty_shipped * p.standard_cost)       AS goods_cost,
       SUM(l.freight_cost)                        AS freight_cost
FROM   shipment_line l
JOIN   product       p ON p.product_id = l.product_id
WHERE  l.qty_shipped > 0
  AND  l.revenue      >= 0
  AND  l.freight_cost >= 0
GROUP  BY l.shipment_id;

-- A.7.2 Clean, enriched shipment fact table: one row per shipment, all cost components
CREATE VIEW v_shipment_fact AS
SELECT s.shipment_id,
       s.ship_date,
       s.delivery_date,
       TO_CHAR(s.ship_date, 'YYYY-MM')                          AS ship_month,
       c.carrier_id,
       TRIM(c.carrier_name) || ' (' || TRIM(c.mode) || ')'      AS carrier,
       c.mode,
       c.cost_per_kg                                            AS contract_rate_per_kg,
       TRIM(w.region)                                           AS origin_region,
       TRIM(cu.region)                                          AS dest_region,
       TRIM(w.region) || ' > ' || TRIM(cu.region)               AS lane,
       sl.units,
       sl.weight_kg,
       sl.revenue,
       sl.goods_cost,
       c.avg_transit_days                                       AS quoted_transit_days,
       (s.delivery_date - s.ship_date)                          AS actual_transit_days,   -- PostgreSQL DATE - DATE = integer days
       (s.delivery_date - s.ship_date) - c.avg_transit_days     AS transit_variance_days,
       s.on_time_flag,
       1 - s.on_time_flag                                       AS late_flag,
       s.damaged_flag,
       CASE WHEN s.on_time_flag = 1 AND s.damaged_flag = 0 THEN 1 ELSE 0 END AS successful_flag,
       sl.freight_cost,
       -- modelled cost components (each computed ONCE per shipment - no double counting):
       ROUND((1 - s.on_time_flag) * sl.revenue * prm.late_penalty_rate, 2)               AS late_penalty_cost,
       ROUND(s.damaged_flag * sl.goods_cost * prm.damage_writeoff_share, 2)              AS damage_cost,
       ROUND(s.damaged_flag * sl.weight_kg * prm.damage_writeoff_share * rc.cost_per_kg, 2) AS reshipment_cost
FROM   shipment          s
JOIN   v_shipment_lines  sl  ON sl.shipment_id  = s.shipment_id
JOIN   carrier           c   ON c.carrier_id    = s.carrier_id
JOIN   warehouse         w   ON w.warehouse_id  = s.warehouse_id
JOIN   customer          cu  ON cu.customer_id  = s.customer_id
CROSS  JOIN audit_params prm
JOIN   carrier           rc  ON rc.carrier_id   = prm.reship_carrier_id
WHERE  s.delivery_date IS NOT NULL
  AND  s.delivery_date >= s.ship_date;

-- A.7.3 Add the True Cost column on top (kept separate for readability)
CREATE VIEW v_shipment_true_cost AS
SELECT f.*,
       f.freight_cost + f.late_penalty_cost + f.damage_cost + f.reshipment_cost AS true_cost
FROM   v_shipment_fact f;

-- A.7.4 Reconciliation: line-level freight must equal fact-table freight (expect diff = 0)
SELECT (SELECT SUM(freight_cost) FROM shipment_line)        AS freight_in_lines,
       (SELECT SUM(freight_cost) FROM v_shipment_true_cost) AS freight_in_fact,
       (SELECT COUNT(*)          FROM v_shipment_true_cost) AS fact_rows;


/* =============================================================================
   B. CARRIER SCORECARD
   ============================================================================= */
CREATE VIEW v_carrier_scorecard AS
SELECT carrier_id,
       carrier,
       mode,
       contract_rate_per_kg,
       COUNT(*)                                                    AS shipments,
       SUM(on_time_flag)                                           AS on_time_shipments,
       SUM(late_flag)                                              AS late_shipments,
       SUM(damaged_flag)                                           AS damaged_shipments,
       SUM(successful_flag)                                        AS successful_shipments,
       ROUND(100.0 * AVG(on_time_flag), 2)                         AS on_time_pct,
       ROUND(100.0 * AVG(late_flag), 2)                            AS late_pct,
       ROUND(100.0 * AVG(damaged_flag), 2)                         AS damage_rate_pct,
       ROUND(AVG(quoted_transit_days), 2)                          AS quoted_transit_days,
       ROUND(AVG(actual_transit_days), 2)                          AS avg_actual_transit_days,
       ROUND(SUM(freight_cost), 2)                                 AS total_freight_cost,
       ROUND(SUM(late_penalty_cost), 2)                            AS total_penalty_cost,
       ROUND(SUM(freight_cost) / NULLIF(SUM(weight_kg), 0), 4)     AS freight_per_kg,
       ROUND(SUM(freight_cost) / NULLIF(SUM(on_time_flag), 0), 2)  AS freight_per_on_time_delivery,
       ROUND(SUM(true_cost)    / NULLIF(SUM(successful_flag), 0), 2) AS true_cost_per_successful_delivery
FROM   v_shipment_true_cost
GROUP  BY carrier_id, carrier, mode, contract_rate_per_kg;

SELECT * FROM v_carrier_scorecard ORDER BY carrier_id;


/* =============================================================================
   C. TRUE COST PER SHIPMENT AND PER UNIT
      True Cost = Freight + Late Penalties + Damage Write-off + Expedited Reshipment
   ============================================================================= */
CREATE VIEW v_carrier_true_cost AS
SELECT carrier_id,
       carrier,
       COUNT(*)                                              AS shipments,
       SUM(units)                                            AS units,
       ROUND(SUM(freight_cost), 2)                           AS freight_cost,
       ROUND(SUM(late_penalty_cost), 2)                      AS late_penalty_cost,
       ROUND(SUM(damage_cost), 2)                            AS damage_cost,
       ROUND(SUM(reshipment_cost), 2)                        AS reshipment_cost,
       ROUND(SUM(late_penalty_cost + damage_cost + reshipment_cost), 2) AS failure_cost,
       ROUND(SUM(true_cost), 2)                              AS true_cost,
       ROUND(SUM(freight_cost) / COUNT(*), 2)                AS freight_per_shipment,
       ROUND(SUM(true_cost)    / COUNT(*), 2)                AS true_cost_per_shipment,
       ROUND(SUM(freight_cost) / SUM(units), 4)              AS freight_per_unit,
       ROUND(SUM(true_cost)    / SUM(units), 4)              AS true_cost_per_unit,
       ROUND(100.0 * (SUM(true_cost) / SUM(freight_cost) - 1), 1) AS hidden_cost_uplift_pct,
       ROUND(100.0 * SUM(true_cost) / SUM(SUM(true_cost)) OVER (), 1) AS share_of_network_true_cost_pct
FROM   v_shipment_true_cost
GROUP  BY carrier_id, carrier;

SELECT * FROM v_carrier_true_cost ORDER BY true_cost_per_unit;

-- C.2  Network totals (KPI header)
SELECT COUNT(*)                                     AS total_shipments,
       SUM(units)                                   AS total_units,
       ROUND(SUM(freight_cost), 2)                  AS total_freight_cost,
       ROUND(SUM(true_cost), 2)                     AS total_true_cost,
       ROUND(100.0 * AVG(on_time_flag), 2)          AS on_time_pct,
       ROUND(100.0 * AVG(damaged_flag), 2)          AS damage_rate_pct,
       ROUND(SUM(true_cost) / SUM(successful_flag), 2) AS true_cost_per_successful_delivery
FROM   v_shipment_true_cost;


/* =============================================================================
   D. LANE ANALYSIS  (lane = origin warehouse region > destination customer region)
   ============================================================================= */

-- D.1  Lane scorecard across all carriers
CREATE VIEW v_lane_scorecard AS
SELECT lane,
       origin_region,
       dest_region,
       COUNT(*)                                                    AS shipments,
       ROUND(AVG(quoted_transit_days), 2)                          AS avg_quoted_days,
       ROUND(AVG(actual_transit_days), 2)                          AS avg_actual_days,
       ROUND(AVG(transit_variance_days), 2)                        AS avg_transit_variance_days,
       ROUND(AVG(GREATEST(transit_variance_days, 0)), 2)           AS avg_delay_days,          -- early arrivals count as 0
       ROUND(100.0 * AVG(late_flag), 2)                            AS late_pct,
       ROUND(100.0 * AVG(damaged_flag), 2)                         AS damage_rate_pct,
       ROUND(SUM(freight_cost) / SUM(weight_kg), 4)                AS freight_per_kg,
       ROUND((STDDEV_SAMP(freight_cost / weight_kg) / AVG(freight_cost / weight_kg))::numeric, 3) AS freight_per_kg_cv,
       ROUND(SUM(late_penalty_cost + damage_cost + reshipment_cost) / COUNT(*), 2) AS failure_cost_per_shipment,
       ROUND(SUM(true_cost) / COUNT(*), 2)                         AS true_cost_per_shipment
FROM   v_shipment_true_cost
GROUP  BY lane, origin_region, dest_region;

-- D.2  Most problematic lanes = highest failure cost per shipment
SELECT RANK() OVER (ORDER BY failure_cost_per_shipment DESC) AS problem_rank, *
FROM   v_lane_scorecard
ORDER  BY problem_rank
LIMIT  10;

-- D.3  Highest transit-time variance lanes (absolute deviation from quoted days)
SELECT lane,
       ROUND(AVG(ABS(transit_variance_days)), 2) AS avg_abs_variance_days,
       ROUND(STDDEV_SAMP(actual_transit_days), 2) AS sd_actual_days,
       COUNT(*)                                  AS shipments
FROM   v_shipment_true_cost
GROUP  BY lane
ORDER  BY avg_abs_variance_days DESC
LIMIT  10;

-- D.4  Carrier x lane comparison (basis for the reallocation test)
CREATE VIEW v_carrier_lane AS
SELECT carrier_id,
       carrier,
       lane,
       COUNT(*)                          AS shipments,
       SUM(weight_kg)                    AS weight_kg,
       SUM(revenue)                      AS revenue,
       SUM(goods_cost)                   AS goods_cost,
       SUM(freight_cost) / SUM(weight_kg) AS freight_per_kg,
       AVG(late_flag::numeric)           AS late_rate,
       AVG(damaged_flag::numeric)        AS damage_rate,
       SUM(late_penalty_cost + damage_cost + reshipment_cost) / COUNT(*) AS failure_cost_per_shipment,
       SUM(true_cost)                    AS true_cost
FROM   v_shipment_true_cost
GROUP  BY carrier_id, carrier, lane;

SELECT carrier, lane, shipments,
       ROUND(freight_per_kg, 4)              AS freight_per_kg,
       ROUND(100 * late_rate, 1)             AS late_pct,
       ROUND(100 * damage_rate, 1)           AS damage_pct,
       ROUND(failure_cost_per_shipment, 2)   AS failure_cost_per_shipment
FROM   v_carrier_lane
ORDER  BY lane, carrier;


/* =============================================================================
   E. CARRIER RANKING
   ============================================================================= */
-- Composite score (0-100): 50% true cost/unit, 30% on-time %, 20% damage rate,
-- each min-max normalised across carriers so that higher = better.
WITH base AS (
    SELECT carrier,
           SUM(true_cost) / SUM(units)        AS true_cost_per_unit,
           AVG(on_time_flag::numeric)         AS on_time_rate,
           AVG(damaged_flag::numeric)         AS damage_rate
    FROM   v_shipment_true_cost
    GROUP  BY carrier
), norm AS (
    SELECT b.*,
           1 - (true_cost_per_unit - MIN(true_cost_per_unit) OVER ()) / NULLIF(MAX(true_cost_per_unit) OVER () - MIN(true_cost_per_unit) OVER (), 0) AS cost_score,
               (on_time_rate       - MIN(on_time_rate)       OVER ()) / NULLIF(MAX(on_time_rate)       OVER () - MIN(on_time_rate)       OVER (), 0) AS reliability_score,
           1 - (damage_rate        - MIN(damage_rate)        OVER ()) / NULLIF(MAX(damage_rate)        OVER () - MIN(damage_rate)        OVER (), 0) AS damage_score
    FROM   base b
)
SELECT carrier,
       ROUND(true_cost_per_unit, 4)                                AS true_cost_per_unit,
       ROUND(100 * on_time_rate, 2)                                AS on_time_pct,
       ROUND(100 * damage_rate, 2)                                 AS damage_rate_pct,
       RANK() OVER (ORDER BY true_cost_per_unit ASC)               AS rank_lowest_true_cost,
       RANK() OVER (ORDER BY on_time_rate DESC)                    AS rank_reliability,
       RANK() OVER (ORDER BY damage_rate ASC)                      AS rank_lowest_damage,
       ROUND(100 * (0.5 * cost_score + 0.3 * reliability_score + 0.2 * damage_score), 1) AS composite_score,
       RANK() OVER (ORDER BY 0.5 * cost_score + 0.3 * reliability_score + 0.2 * damage_score DESC) AS rank_overall
FROM   norm
ORDER  BY rank_overall;


/* =============================================================================
   F. BUSINESS RECOMMENDATION SUPPORT
   ============================================================================= */

-- F.1  Is the cheapest carrier really the cheapest? Contract rate rank vs true-cost rank
SELECT t.carrier,
       c.cost_per_kg                                             AS contract_rate_per_kg,
       RANK() OVER (ORDER BY c.cost_per_kg)                      AS rank_by_contract_rate,
       t.true_cost_per_unit,
       RANK() OVER (ORDER BY t.true_cost_per_unit)               AS rank_by_true_cost,
       t.hidden_cost_uplift_pct
FROM   v_carrier_true_cost t
JOIN   carrier c ON c.carrier_id = t.carrier_id
ORDER  BY rank_by_contract_rate;

-- F.2  Proposed strategy test:
--      shift 20% of the cheapest carrier's volume to the 2nd-cheapest carrier on the
--      3 lanes where the cheapest carrier has the highest failure cost per shipment.
--      Moved volume is costed at expected values (lane-level freight/kg, late rate,
--      damage rate) for BOTH carriers so the comparison is like-for-like.
WITH prm AS (
    SELECT p.*, rc.cost_per_kg AS reship_rate
    FROM   audit_params p JOIN carrier rc ON rc.carrier_id = p.reship_carrier_id
), ranked_carriers AS (
    SELECT carrier_id, RANK() OVER (ORDER BY cost_per_kg) AS rate_rank FROM carrier
), from_c AS (SELECT carrier_id FROM ranked_carriers WHERE rate_rank = 1),
   to_c   AS (SELECT carrier_id FROM ranked_carriers WHERE rate_rank = 2),
problem_lanes AS (
    SELECT cl.lane
    FROM   v_carrier_lane cl, prm
    WHERE  cl.carrier_id = (SELECT carrier_id FROM from_c)
      AND  cl.shipments >= prm.min_lane_shipments
    ORDER  BY cl.failure_cost_per_shipment DESC
    LIMIT  (SELECT n_problem_lanes FROM prm)
), moved AS (
    SELECT a.lane,
           a.carrier AS from_carrier, b.carrier AS to_carrier,
           a.weight_kg  * prm.shift_share AS kg,
           a.revenue    * prm.shift_share AS rev,
           a.goods_cost * prm.shift_share AS goods,
           a.freight_per_kg AS a_fpk, a.late_rate AS a_late, a.damage_rate AS a_dmg,
           b.freight_per_kg AS b_fpk, b.late_rate AS b_late, b.damage_rate AS b_dmg,
           prm.*
    FROM   problem_lanes pl
    JOIN   v_carrier_lane a ON a.lane = pl.lane AND a.carrier_id = (SELECT carrier_id FROM from_c)
    JOIN   v_carrier_lane b ON b.lane = pl.lane AND b.carrier_id = (SELECT carrier_id FROM to_c)
    CROSS  JOIN prm
), costed AS (
    SELECT lane, from_carrier, to_carrier, kg,
           kg*a_fpk + rev*a_late*late_penalty_rate + goods*a_dmg*damage_writeoff_share + kg*a_dmg*damage_writeoff_share*reship_rate AS baseline_cost,
           kg*b_fpk + rev*b_late*late_penalty_rate + goods*b_dmg*damage_writeoff_share + kg*b_dmg*damage_writeoff_share*reship_rate AS scenario_cost
    FROM   moved
)
SELECT lane, from_carrier, to_carrier,
       ROUND(kg, 0)                               AS moved_weight_kg,
       ROUND(baseline_cost, 2)                    AS baseline_cost,
       ROUND(scenario_cost, 2)                    AS scenario_cost,
       ROUND(scenario_cost - baseline_cost, 2)    AS change_in_true_cost
FROM   costed
UNION ALL
SELECT 'TOTAL', NULL, NULL,
       ROUND(SUM(kg), 0), ROUND(SUM(baseline_cost), 2), ROUND(SUM(scenario_cost), 2),
       ROUND(SUM(scenario_cost - baseline_cost), 2)
FROM   costed;

-- F.3  Strategy result vs the 12% target (negative change = saving)
WITH prm AS (SELECT p.*, rc.cost_per_kg AS reship_rate FROM audit_params p JOIN carrier rc ON rc.carrier_id = p.reship_carrier_id),
lanes AS (
    SELECT lane FROM v_carrier_lane, prm
    WHERE  carrier_id = (SELECT carrier_id FROM carrier ORDER BY cost_per_kg LIMIT 1)
      AND  shipments >= prm.min_lane_shipments
    ORDER  BY failure_cost_per_shipment DESC LIMIT (SELECT n_problem_lanes FROM prm)
), d AS (
    SELECT SUM( (a.weight_kg*prm.shift_share) * (b.freight_per_kg - a.freight_per_kg)
              + (a.revenue  *prm.shift_share) * (b.late_rate - a.late_rate) * prm.late_penalty_rate
              + (a.goods_cost*prm.shift_share)* (b.damage_rate - a.damage_rate) * prm.damage_writeoff_share
              + (a.weight_kg*prm.shift_share) * (b.damage_rate - a.damage_rate) * prm.damage_writeoff_share * prm.reship_rate) AS delta
    FROM   lanes l
    JOIN   v_carrier_lane a ON a.lane = l.lane AND a.carrier_id = (SELECT carrier_id FROM carrier ORDER BY cost_per_kg LIMIT 1)
    JOIN   v_carrier_lane b ON b.lane = l.lane AND b.carrier_id = (SELECT carrier_id FROM carrier ORDER BY cost_per_kg LIMIT 1 OFFSET 1)
    CROSS  JOIN prm
)
SELECT ROUND(d.delta, 2)                                      AS projected_change_in_true_cost,
       ROUND(100 * d.delta / t.total, 4)                      AS pct_change_network_true_cost,
       ROUND(-prm.target_reduction * t.total, 2)              AS target_change_12pct,
       CASE WHEN d.delta <= -prm.target_reduction * t.total
            THEN 'Target met' ELSE 'Target NOT supported by data' END AS verdict
FROM   d,
       (SELECT SUM(true_cost) AS total FROM v_shipment_true_cost) t,
       audit_params prm;

-- F.4  Alternative lever: shift a share of Air (CARR-3) weight network-wide to Rail (CARR-2)
WITH prm AS (SELECT p.*, rc.cost_per_kg AS reship_rate FROM audit_params p JOIN carrier rc ON rc.carrier_id = p.reship_carrier_id),
c AS (
    SELECT carrier_id,
           SUM(weight_kg) AS kg, SUM(revenue) AS rev, SUM(goods_cost) AS goods,
           SUM(freight_cost)/SUM(weight_kg) AS fpk,
           AVG(late_flag::numeric) AS late_rate, AVG(damaged_flag::numeric) AS dmg_rate
    FROM   v_shipment_true_cost GROUP BY carrier_id
), saving AS (
    SELECT air.kg AS air_kg,
           -- expected true cost per kg of Air freight under each carrier
             (air.fpk  + air.late_rate  * prm.late_penalty_rate * air.rev/air.kg + air.dmg_rate  * prm.damage_writeoff_share * (air.goods/air.kg + prm.reship_rate))
           - (rail.fpk + rail.late_rate * prm.late_penalty_rate * air.rev/air.kg + rail.dmg_rate * prm.damage_writeoff_share * (air.goods/air.kg + prm.reship_rate))
             AS saving_per_kg
    FROM   c air, c rail, prm
    WHERE  air.carrier_id = 3 AND rail.carrier_id = 2
), total AS (SELECT SUM(true_cost) AS t FROM v_shipment_true_cost)
SELECT ROUND(sh, 2)                                         AS share_of_air_weight_shifted,
       ROUND(sh * air_kg * saving_per_kg, 2)                AS projected_saving,
       ROUND(100 * sh * air_kg * saving_per_kg / total.t, 2) AS pct_of_network_true_cost
FROM   saving, total, (VALUES (0.05), (0.10), (0.15), (0.20), (0.25), (0.30)) v(sh)
ORDER  BY sh;

-- F.5  Penalty sensitivity: late-penalty rate at which the cheapest carrier's
--      true cost per unit would equal the second-cheapest carrier's (break-even).
WITH prm AS (SELECT * FROM audit_params),
c AS (
    SELECT carrier_id,
           SUM(freight_cost + damage_cost + reshipment_cost) / SUM(units) AS fixed_per_unit,
           SUM(late_flag * revenue) / SUM(units)                         AS late_rev_per_unit
    FROM   v_shipment_true_cost GROUP BY carrier_id
), r AS (SELECT carrier_id, RANK() OVER (ORDER BY cost_per_kg) AS rk FROM carrier)
SELECT ROUND(100 * (c2.fixed_per_unit - c1.fixed_per_unit)
                 / NULLIF(c1.late_rev_per_unit - c2.late_rev_per_unit, 0), 2) AS break_even_penalty_rate_pct,
       ROUND(100 * prm.late_penalty_rate, 2)                                  AS current_assumption_pct
FROM   c c1
JOIN   r r1 ON r1.carrier_id = c1.carrier_id AND r1.rk = 1
JOIN   c c2 ON TRUE
JOIN   r r2 ON r2.carrier_id = c2.carrier_id AND r2.rk = 2
CROSS  JOIN prm;

-- F.6  Spend concentration: share of freight spend vs share of volume by carrier
SELECT carrier,
       ROUND(100.0 * SUM(freight_cost) / SUM(SUM(freight_cost)) OVER (), 1) AS pct_of_freight_spend,
       ROUND(100.0 * SUM(weight_kg)    / SUM(SUM(weight_kg))    OVER (), 1) AS pct_of_weight,
       ROUND(100.0 * COUNT(*)          / SUM(COUNT(*))          OVER (), 1) AS pct_of_shipments,
       ROUND(100.0 * AVG(on_time_flag), 2)                                   AS on_time_pct
FROM   v_shipment_true_cost
GROUP  BY carrier
ORDER  BY pct_of_freight_spend DESC;

/* ============================== END OF SCRIPT ============================== */
