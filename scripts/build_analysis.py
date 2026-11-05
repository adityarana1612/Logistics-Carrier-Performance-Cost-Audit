"""
Logistics Carrier Performance & Cost Audit - analysis pipeline
==============================================================

Reads the raw Meridian Supply Chain CSVs (data/raw), validates and cleans them,
builds a shipment-level fact table and writes every analytical output used by
the Excel workbook, the dashboard and the written reports (data/processed).

This script has already been run; its outputs are committed in data/processed.
It is kept in the repository for transparency and reproducibility only.

Cost-model assumptions (the dataset has NO penalty / reshipment columns, so
these costs are MODELLED, not observed). Change them here, in the Excel
Cost_Model sheet, or in the SQL parameter CTE - all three use the same values.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

# ---------------------------------------------------------------- assumptions
ASSUMPTIONS = {
    "late_penalty_rate": 0.02,     # service credit = 2% of shipment revenue per late shipment
    "damage_writeoff_share": 0.25, # 25% of units in a damaged shipment are written off
    "reship_carrier_id": 3,        # damaged units are re-sent by Air (CARR-3) ...
    "shift_share": 0.20,           # strategy: shift 20% of volume ...
    "from_carrier_rank": 1,        # ... from the cheapest carrier (by contracted rate/kg)
    "to_carrier_rank": 2,          # ... to the second-cheapest carrier
    "n_problem_lanes": 3,          # ... on the 3 most problematic lanes
    "min_lane_shipments": 30,      # minimum sample for a carrier-lane cell to be ranked
    "target_reduction": 0.12,      # hypothesis to test: 12% reduction in landed cost
}


def load() -> dict[str, pd.DataFrame]:
    return {p.stem: pd.read_csv(p) for p in sorted(RAW.glob("*.csv"))}


# ------------------------------------------------------------ data quality
def quality_checks(t: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []

    def add(table, check, n, action):
        rows.append({"table": table, "check": check, "records_affected": int(n), "action": action})

    pks = {"carrier": "carrier_id", "customer": "customer_id", "warehouse": "warehouse_id",
           "product": "product_id", "supplier": "supplier_id", "shipment": "shipment_id",
           "shipment_line": "ship_line_id", "purchase_order": "po_id",
           "purchase_order_line": "po_line_id", "inventory_snapshot": "snapshot_id",
           "production_run": "production_id"}
    for name, df in t.items():
        add(name, "row count", len(df), "profiled")
        add(name, "null values (all columns)", df.isna().sum().sum(),
            "none required" if df.isna().sum().sum() == 0 else "see note")
        add(name, "fully duplicated rows", df.duplicated().sum(), "none required")
        add(name, f"duplicate primary key ({pks[name]})", df[pks[name]].duplicated().sum(), "none required")

    s, sl = t["shipment"], t["shipment_line"]
    fk = [("shipment", "carrier_id", t["carrier"].carrier_id),
          ("shipment", "warehouse_id", t["warehouse"].warehouse_id),
          ("shipment", "customer_id", t["customer"].customer_id)]
    for tab, col, ref in fk:
        add(tab, f"orphan foreign key {col}", (~t[tab][col].isin(ref)).sum(), "none required")
    add("shipment_line", "orphan foreign key shipment_id", (~sl.shipment_id.isin(s.shipment_id)).sum(), "none required")
    add("shipment_line", "orphan foreign key product_id", (~sl.product_id.isin(t["product"].product_id)).sum(), "none required")
    add("shipment", "shipments without any line", (~s.shipment_id.isin(sl.shipment_id)).sum(), "none required")

    sd = pd.to_datetime(s.ship_date, errors="coerce")
    dd = pd.to_datetime(s.delivery_date, errors="coerce")
    add("shipment", "unparseable ship_date / delivery_date", sd.isna().sum() + dd.isna().sum(), "none required")
    add("shipment", "delivery_date before ship_date", (dd < sd).sum(), "none required")
    add("shipment", "on_time_flag / damaged_flag outside {0,1}",
        (~s.on_time_flag.isin([0, 1])).sum() + (~s.damaged_flag.isin([0, 1])).sum(), "none required")
    rep = sl.duplicated(["shipment_id", "product_id"], keep=False)
    add("shipment_line", "same product on >1 line of a shipment (split lines)", rep.sum(),
        "kept - quantities differ and unit prices match list price; no exact duplicates; rolled up at shipment grain")
    add("shipment_line", "exact duplicate lines (all columns except ship_line_id)",
        sl.duplicated(["shipment_id", "product_id", "qty_shipped", "revenue", "freight_cost"]).sum(), "none required")
    add("shipment_line", "qty_shipped <= 0", (sl.qty_shipped <= 0).sum(), "none required")
    add("shipment_line", "negative revenue or freight_cost", ((sl.revenue < 0) | (sl.freight_cost < 0)).sum(), "none required")
    add("purchase_order", "null actual_delivery_date",
        t["purchase_order"].actual_delivery_date.isna().sum(),
        "kept - open/cancelled POs; table is out of scope for the carrier audit")

    # flag consistency: on_time_flag vs dates
    m = s.merge(t["carrier"], on="carrier_id")
    tt = (dd - sd).dt.days
    date_late = tt > m.avg_transit_days
    disagree = (date_late.astype(int) != (1 - m.on_time_flag)).sum()
    add("shipment", "on_time_flag disagrees with (delivery_date - ship_date) vs carrier quoted days", disagree,
        "documented; on_time_flag kept as SLA metric of record, date variance reported separately")
    return pd.DataFrame(rows)


# --------------------------------------------------------- shipment fact table
def build_fact(t: dict[str, pd.DataFrame]) -> pd.DataFrame:
    a = ASSUMPTIONS
    sl = t["shipment_line"].merge(t["product"][["product_id", "unit_weight_kg", "standard_cost"]], on="product_id")
    sl["weight_kg"] = sl.qty_shipped * sl.unit_weight_kg
    sl["goods_cost"] = sl.qty_shipped * sl.standard_cost
    # 1) aggregate lines to shipment grain FIRST -> no one-to-many double counting later
    lines = sl.groupby("shipment_id", as_index=False).agg(
        line_count=("ship_line_id", "count"), units=("qty_shipped", "sum"),
        weight_kg=("weight_kg", "sum"), revenue=("revenue", "sum"),
        goods_cost=("goods_cost", "sum"), freight_cost=("freight_cost", "sum"))

    s = t["shipment"].copy()
    s["ship_date"] = pd.to_datetime(s.ship_date)
    s["delivery_date"] = pd.to_datetime(s.delivery_date)
    c = t["carrier"].rename(columns={"avg_transit_days": "quoted_transit_days"})
    w = t["warehouse"][["warehouse_id", "warehouse_name", "region"]].rename(columns={"region": "origin_region"})
    cu = t["customer"][["customer_id", "customer_name", "region"]].rename(columns={"region": "dest_region"})
    f = (s.merge(lines, on="shipment_id").merge(c, on="carrier_id").merge(w, on="warehouse_id").merge(cu, on="customer_id"))
    f["carrier"] = f.carrier_name + " (" + f["mode"] + ")"
    f["lane"] = f.origin_region + " > " + f.dest_region
    f["actual_transit_days"] = (f.delivery_date - f.ship_date).dt.days
    f["transit_variance_days"] = f.actual_transit_days - f.quoted_transit_days
    f["late_flag"] = 1 - f.on_time_flag
    f["successful_flag"] = ((f.on_time_flag == 1) & (f.damaged_flag == 0)).astype(int)

    air_rate = float(t["carrier"].set_index("carrier_id").loc[a["reship_carrier_id"], "cost_per_kg"])
    # money rounded half-up to cents, matching PostgreSQL ROUND() and Excel ROUND()
    f["revenue"] = round_half_up(f.revenue)
    f["goods_cost"] = round_half_up(f.goods_cost)
    f["weight_kg"] = round_half_up(f.weight_kg)
    f["freight_cost"] = round_half_up(f.freight_cost)
    f["late_penalty_cost"] = exact_cost(f.late_flag, f.revenue, a["late_penalty_rate"])
    f["damage_cost"] = exact_cost(f.damaged_flag, f.goods_cost, a["damage_writeoff_share"])
    f["reshipment_cost"] = exact_cost(f.damaged_flag, f.weight_kg, a["damage_writeoff_share"], air_rate)
    f["true_cost"] = f.freight_cost + f.late_penalty_cost + f.damage_cost + f.reshipment_cost
    f["year"] = f.ship_date.dt.year
    f["ship_month"] = f.ship_date.dt.strftime("%Y-%m")
    cols = ["shipment_id", "ship_date", "delivery_date", "ship_month", "year", "carrier_id", "carrier", "carrier_name", "mode",
            "cost_per_kg", "warehouse_id", "warehouse_name", "origin_region", "customer_id", "customer_name", "dest_region",
            "lane", "line_count", "units", "weight_kg", "revenue", "goods_cost", "quoted_transit_days",
            "actual_transit_days", "transit_variance_days", "on_time_flag", "late_flag", "damaged_flag", "successful_flag",
            "freight_cost", "late_penalty_cost", "damage_cost", "reshipment_cost", "true_cost"]
    f = f[cols].sort_values("shipment_id").reset_index(drop=True)
    f["true_cost"] = round_half_up(f.true_cost)
    return f


def exact_cost(flag, base, *factors):
    """flag * base * factors, in exact decimal arithmetic, rounded half-up to cents."""
    from decimal import Decimal, ROUND_HALF_UP
    k = Decimal(1)
    for x in factors:
        k *= Decimal(repr(float(x)))
    return pd.Series([float((Decimal(int(fl)) * Decimal(repr(float(b))) * k).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
                      for fl, b in zip(flag, base)], index=base.index)


def round_half_up(x, nd=2):
    from decimal import Decimal, ROUND_HALF_UP
    q = Decimal(1).scaleb(-nd)
    return x.apply(lambda v: float(Decimal(repr(float(v))).quantize(q, rounding=ROUND_HALF_UP)))


# --------------------------------------------------------------- scorecards
def score(g: pd.core.groupby.DataFrameGroupBy) -> pd.DataFrame:
    d = g.agg(shipments=("shipment_id", "count"), units=("units", "sum"), weight_kg=("weight_kg", "sum"),
              revenue=("revenue", "sum"), goods_cost_total=("goods_cost", "sum"), on_time=("on_time_flag", "sum"), late=("late_flag", "sum"),
              damaged=("damaged_flag", "sum"), successful=("successful_flag", "sum"),
              quoted_transit_days=("quoted_transit_days", "mean"), avg_actual_transit_days=("actual_transit_days", "mean"),
              avg_transit_variance_days=("transit_variance_days", "mean"), sd_transit_days=("actual_transit_days", "std"),
              freight_cost=("freight_cost", "sum"), late_penalty_cost=("late_penalty_cost", "sum"),
              damage_cost=("damage_cost", "sum"), reshipment_cost=("reshipment_cost", "sum"), true_cost=("true_cost", "sum"))
    d["on_time_pct"] = d.on_time / d.shipments
    d["late_pct"] = d.late / d.shipments
    d["damage_rate"] = d.damaged / d.shipments
    d["success_rate"] = d.successful / d.shipments
    d["failure_cost"] = d.late_penalty_cost + d.damage_cost + d.reshipment_cost
    d["freight_per_kg"] = d.freight_cost / d.weight_kg
    d["freight_per_shipment"] = d.freight_cost / d.shipments
    d["true_cost_per_shipment"] = d.true_cost / d.shipments
    d["true_cost_per_unit"] = d.true_cost / d.units
    d["freight_per_unit"] = d.freight_cost / d.units
    d["true_cost_per_kg"] = d.true_cost / d.weight_kg
    d["freight_per_on_time_delivery"] = d.freight_cost / d.on_time
    d["true_cost_per_successful_delivery"] = d.true_cost / d.successful
    d["failure_cost_per_shipment"] = d.failure_cost / d.shipments
    d["true_cost_uplift_pct"] = d.true_cost / d.freight_cost - 1
    d["true_cost_pct_of_revenue"] = d.true_cost / d.revenue
    return d


def carrier_scorecard(f: pd.DataFrame) -> pd.DataFrame:
    d = score(f.groupby(["carrier_id", "carrier", "mode", "cost_per_kg"])).reset_index()
    d["rank_contract_rate"] = d.cost_per_kg.rank(method="min").astype(int)
    d["rank_true_cost_per_unit"] = d.true_cost_per_unit.rank(method="min").astype(int)
    d["rank_reliability"] = d.on_time_pct.rank(ascending=False, method="min").astype(int)
    d["rank_damage"] = d.damage_rate.rank(method="min").astype(int)
    # Composite: 50% true cost/unit, 30% on-time, 20% damage (min-max normalised, higher = better)
    def mm(x, invert):
        r = (x - x.min()) / (x.max() - x.min()) if x.max() != x.min() else x * 0 + 1
        return 1 - r if invert else r
    d["composite_score"] = (0.5 * mm(d.true_cost_per_unit, True) + 0.3 * mm(d.on_time_pct, False)
                            + 0.2 * mm(d.damage_rate, True)) * 100
    d["rank_overall"] = d.composite_score.rank(ascending=False, method="min").astype(int)
    return d.sort_values("carrier_id").reset_index(drop=True)


def lane_scorecard(f: pd.DataFrame) -> pd.DataFrame:
    d = score(f.groupby(["lane", "origin_region", "dest_region"])).reset_index()
    cv = f.groupby("lane").apply(lambda x: (x.freight_cost / x.weight_kg).std() / (x.freight_cost / x.weight_kg).mean(),
                                 include_groups=False)
    d["freight_per_kg_cv"] = d.lane.map(cv)
    d["rank_failure_cost"] = d.failure_cost_per_shipment.rank(ascending=False, method="min").astype(int)
    return d.sort_values("failure_cost_per_shipment", ascending=False).reset_index(drop=True)


def carrier_lane(f: pd.DataFrame) -> pd.DataFrame:
    return score(f.groupby(["carrier_id", "carrier", "lane", "origin_region", "dest_region"])).reset_index()


# ------------------------------------------------------------ strategy test
def scenario(f: pd.DataFrame, cs: pd.DataFrame, cl: pd.DataFrame, t) -> tuple[pd.DataFrame, dict]:
    a = ASSUMPTIONS
    air_rate = float(t["carrier"].set_index("carrier_id").loc[a["reship_carrier_id"], "cost_per_kg"])
    frm = int(cs.loc[cs.rank_contract_rate == a["from_carrier_rank"], "carrier_id"].iloc[0])
    to = int(cs.loc[cs.rank_contract_rate == a["to_carrier_rank"], "carrier_id"].iloc[0])
    src = cl[(cl.carrier_id == frm) & (cl.shipments >= a["min_lane_shipments"])]
    lanes = src.sort_values("failure_cost_per_shipment", ascending=False).head(a["n_problem_lanes"]).lane.tolist()
    rows = []
    for lane in lanes:
        A = cl[(cl.carrier_id == frm) & (cl.lane == lane)].iloc[0]
        B = cl[(cl.carrier_id == to) & (cl.lane == lane)].iloc[0]
        sh = a["shift_share"]
        kg, rev = A.weight_kg * sh, A.revenue * sh
        goods = f[(f.carrier_id == frm) & (f.lane == lane)].goods_cost.sum() * sh

        def expected(r):  # expected true cost of the moved volume if carried by carrier-lane r
            fr = kg * r.freight_per_kg
            lp = rev * r.late_pct * a["late_penalty_rate"]
            dm = goods * r.damage_rate * a["damage_writeoff_share"]
            rs = kg * r.damage_rate * a["damage_writeoff_share"] * air_rate
            return fr, lp, dm, rs
        base, new = expected(A), expected(B)
        rows.append({"lane": lane, "from_carrier": A.carrier, "to_carrier": B.carrier,
                     "from_lane_shipments": int(A.shipments), "to_lane_shipments": int(B.shipments),
                     "moved_shipments_equiv": A.shipments * sh, "moved_weight_kg": kg, "moved_revenue": rev,
                     "moved_goods_cost": goods,
                     "from_freight_per_kg": A.freight_per_kg, "to_freight_per_kg": B.freight_per_kg,
                     "from_late_pct": A.late_pct, "to_late_pct": B.late_pct,
                     "from_damage_rate": A.damage_rate, "to_damage_rate": B.damage_rate,
                     "baseline_freight": base[0], "baseline_penalty": base[1], "baseline_damage": base[2], "baseline_reship": base[3],
                     "baseline_true_cost": sum(base),
                     "scenario_freight": new[0], "scenario_penalty": new[1], "scenario_damage": new[2], "scenario_reship": new[3],
                     "scenario_true_cost": sum(new)})
    sc = pd.DataFrame(rows)
    sc["delta_true_cost"] = sc.scenario_true_cost - sc.baseline_true_cost
    total = f.true_cost.sum()
    lane_total = f[f.lane.isin(lanes)].true_cost.sum()
    delta = sc.delta_true_cost.sum()
    summary = {"from_carrier_id": frm, "to_carrier_id": to, "lanes": lanes,
               "network_true_cost": total, "problem_lanes_true_cost": lane_total,
               "moved_volume_baseline_cost": sc.baseline_true_cost.sum(),
               "net_change": delta, "pct_change_network": delta / total,
               "pct_change_problem_lanes": delta / lane_total,
               "pct_change_moved_volume": delta / sc.baseline_true_cost.sum(),
               "target_reduction_value": total * a["target_reduction"]}
    return sc, summary


def sensitivity(f: pd.DataFrame, cs: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    """True cost/unit by carrier for a range of late-penalty rates + break-even rate
    at which the cheapest carrier's true cost/unit equals the 2nd cheapest."""
    a = ASSUMPTIONS
    rates = [0.0, 0.01, 0.02, 0.03, 0.05, 0.075, 0.10, 0.15]
    rows = []
    g = f.groupby("carrier")
    fixed = g.apply(lambda x: (x.freight_cost + x.damage_cost + x.reshipment_cost).sum(), include_groups=False)
    late_rev = g.apply(lambda x: (x.late_flag * x.revenue).sum(), include_groups=False)
    units = g.units.sum()
    for r in rates:
        for c in fixed.index:
            rows.append({"late_penalty_rate": r, "carrier": c, "true_cost_per_unit": (fixed[c] + r * late_rev[c]) / units[c]})
    c1 = cs.loc[cs.rank_contract_rate == a["from_carrier_rank"], "carrier"].iloc[0]
    c2 = cs.loc[cs.rank_contract_rate == a["to_carrier_rank"], "carrier"].iloc[0]
    # fixed1/u1 + r*lr1/u1 = fixed2/u2 + r*lr2/u2
    num = fixed[c2] / units[c2] - fixed[c1] / units[c1]
    den = late_rev[c1] / units[c1] - late_rev[c2] / units[c2]
    be = num / den if den > 0 else float("nan")
    return pd.DataFrame(rows), be


def mode_shift_scenario(cs: pd.DataFrame, t) -> tuple[pd.DataFrame, float]:
    """Alternative lever: move a share of Air (CARR-3) weight network-wide to Rail (CARR-2),
    priced at each carrier's observed network-level rates (expected-value method, as above)."""
    a = ASSUMPTIONS
    air_rate = float(t["carrier"].set_index("carrier_id").loc[a["reship_carrier_id"], "cost_per_kg"])
    A = cs[cs.carrier_id == 3].iloc[0]
    B = cs[cs.carrier_id == 2].iloc[0]
    total = cs.true_cost.sum()

    def cost_per_kg(r, rev_per_kg, goods_per_kg):
        return (r.freight_per_kg + r.late_pct * a["late_penalty_rate"] * rev_per_kg
                + r.damage_rate * a["damage_writeoff_share"] * (goods_per_kg + air_rate))
    rev_per_kg = A.revenue / A.weight_kg
    goods_per_kg = A.goods_cost_total / A.weight_kg
    saving_per_kg = cost_per_kg(A, rev_per_kg, goods_per_kg) - cost_per_kg(B, rev_per_kg, goods_per_kg)
    rows = []
    for s in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]:
        sav = saving_per_kg * A.weight_kg * s
        rows.append({"share_of_air_weight_shifted": s, "weight_kg_shifted": A.weight_kg * s,
                     "saving": sav, "pct_of_network_true_cost": sav / total})
    required = a["target_reduction"] * total / (saving_per_kg * A.weight_kg)
    return pd.DataFrame(rows), required


def two_prop_z(x1, n1, x2, n2):
    import math
    p = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    z = (x1 / n1 - x2 / n2) / se
    return z, math.erfc(abs(z) / math.sqrt(2))


def significance(cs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    ids = cs.carrier.tolist()
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = cs.iloc[i], cs.iloc[j]
            for metric, col in [("on_time_pct", "on_time"), ("damage_rate", "damaged")]:
                z, p = two_prop_z(a[col], a.shipments, b[col], b.shipments)
                rows.append({"metric": metric, "carrier_a": a.carrier, "carrier_b": b.carrier,
                             "rate_a": a[col] / a.shipments, "rate_b": b[col] / b.shipments,
                             "z_stat": z, "p_value": p, "significant_at_5pct": p < 0.05})
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t = load()
    dq = quality_checks(t)
    f = build_fact(t)
    cs = carrier_scorecard(f)
    ls = lane_scorecard(f)
    cl = carrier_lane(f)
    sc, summ = scenario(f, cs, cl, t)
    sens, be = sensitivity(f, cs)
    ms, ms_required = mode_shift_scenario(cs, t)
    sig = significance(cs)
    ms.to_csv(OUT / "mode_shift_scenario.csv", index=False)
    sig.to_csv(OUT / "significance_tests.csv", index=False)
    monthly = score(f.groupby(["ship_month", "carrier"])).reset_index()[
        ["ship_month", "carrier", "shipments", "on_time_pct", "damage_rate", "true_cost_per_unit", "freight_per_unit"]]

    dq.to_csv(OUT / "data_quality_report.csv", index=False)
    f.assign(ship_date=f.ship_date.dt.date, delivery_date=f.delivery_date.dt.date).to_csv(OUT / "shipment_fact.csv", index=False)
    cs.to_csv(OUT / "carrier_scorecard.csv", index=False)
    ls.to_csv(OUT / "lane_scorecard.csv", index=False)
    cl.to_csv(OUT / "carrier_lane_scorecard.csv", index=False)
    sc.to_csv(OUT / "reallocation_scenario.csv", index=False)
    sens.to_csv(OUT / "penalty_sensitivity.csv", index=False)
    monthly.to_csv(OUT / "monthly_carrier_trend.csv", index=False)

    tot = {"shipments": int(len(f)), "units": int(f.units.sum()), "freight_cost": f.freight_cost.sum(),
           "true_cost": f.true_cost.sum(), "late_penalty_cost": f.late_penalty_cost.sum(),
           "damage_cost": f.damage_cost.sum(), "reshipment_cost": f.reshipment_cost.sum(),
           "on_time_pct": f.on_time_flag.mean(), "late_pct": f.late_flag.mean(), "damage_rate": f.damaged_flag.mean(),
           "successful": int(f.successful_flag.sum()),
           "true_cost_per_successful_delivery": f.true_cost.sum() / f.successful_flag.sum(),
           "freight_per_on_time_delivery": f.freight_cost.sum() / f.on_time_flag.sum(),
           "revenue": f.revenue.sum(), "weight_kg": f.weight_kg.sum(),
           "date_min": str(f.ship_date.min().date()), "date_max": str(f.ship_date.max().date())}
    summary = {"assumptions": ASSUMPTIONS, "totals": tot, "scenario": summ, "break_even_penalty_rate": be,
               "mode_shift_required_share_for_target": ms_required,
               "mode_shift": ms.to_dict(orient="records")}
    print(sig.to_string())
    (OUT / "summary_metrics.json").write_text(json.dumps(summary, indent=2, default=float))
    print(json.dumps(summary, indent=2, default=float))
    with pd.option_context("display.width", 250, "display.max_columns", 50):
        print(cs[["carrier", "shipments", "on_time_pct", "damage_rate", "freight_per_kg", "freight_cost", "failure_cost",
                  "true_cost", "true_cost_per_unit", "true_cost_per_successful_delivery", "true_cost_uplift_pct",
                  "composite_score", "rank_overall"]].to_string())
        print(ls[["lane", "shipments", "late_pct", "damage_rate", "failure_cost_per_shipment", "avg_transit_variance_days",
                  "freight_per_kg_cv"]].head(8).to_string())
        print(sc.T.to_string())


if __name__ == "__main__":
    main()
