"""
Builds dashboard/carrier_negotiation_dashboard.html: embeds the 4,500-row shipment
fact table (data/processed/shipment_fact.csv) as compact JSON into
scripts/dashboard_template.html. The output is a single self-contained HTML file
(no external libraries, fonts, CDNs or server). Already run; kept for transparency.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
fact = pd.read_csv(ROOT / "data" / "processed" / "shipment_fact.csv")
summary = json.loads((ROOT / "data" / "processed" / "summary_metrics.json").read_text())
carrier = pd.read_csv(ROOT / "data" / "raw" / "carrier.csv")

carriers = [{"id": int(r.carrier_id), "name": f"{r.carrier_name} ({r['mode']})", "mode": r["mode"],
             "rate": float(r.cost_per_kg), "quoted": int(r.avg_transit_days)} for _, r in carrier.iterrows()]
cidx = {c["id"]: i for i, c in enumerate(carriers)}
lanes = sorted(fact.lane.unique())
lidx = {l: i for i, l in enumerate(lanes)}
lane_objs = [{"name": l, "o": l.split(" > ")[0], "d": l.split(" > ")[1]} for l in lanes]


def num(v):
    f = float(v)
    return int(f) if f.is_integer() else round(f, 2)


rows = [[cidx[r.carrier_id], lidx[r.lane], int(r.year), int(r.units), num(r.weight_kg), num(r.revenue), num(r.goods_cost),
         num(r.freight_cost), int(r.quoted_transit_days), int(r.actual_transit_days), int(r.on_time_flag), int(r.damaged_flag)]
        for r in fact.itertuples(index=False)]
air_rate = float(carrier.loc[carrier.carrier_id == summary["assumptions"]["reship_carrier_id"], "cost_per_kg"].iloc[0])
data = {"carriers": carriers, "lanes": lane_objs, "years": sorted(int(y) for y in fact.year.unique()),
        "period": "Jan 2024 - Dec 2025", "assumptions": summary["assumptions"], "reship_rate": air_rate, "rows": rows}

tpl = (ROOT / "scripts" / "dashboard_template.html").read_text(encoding="utf-8")
assert "/*__DATA__*/null" in tpl
html = tpl.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
out = ROOT / "dashboard" / "carrier_negotiation_dashboard.html"
out.write_text(html, encoding="utf-8")
print("wrote", out, f"{out.stat().st_size / 1024:.0f} KB")
