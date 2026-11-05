"""
Builds excel/cost_model_excel.xlsx from data/raw and data/processed.

Every analytical number in the workbook is a live Excel formula (SUMIFS, COUNTIFS,
AVERAGEIFS, IFERROR, INDEX/MATCH, RANK, SUMPRODUCT) that traces back to the
Cleaned_Data sheet and the editable assumptions on the Cost_Model sheet.
Already run - the workbook is committed. Kept for transparency only.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.comments import Comment
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule, DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "excel" / "cost_model_excel.xlsx"

# ------------------------------------------------------------------ styling
FONT = "Arial"
NAVY, TEAL, GREY, LIGHT = "1F3A5F", "2A7F8E", "F2F4F7", "E8EEF5"
F_TITLE = Font(name=FONT, size=16, bold=True, color=NAVY)
F_SUB = Font(name=FONT, size=10, italic=True, color="5B6573")
F_SEC = Font(name=FONT, size=12, bold=True, color=TEAL)
F_HDR = Font(name=FONT, size=10, bold=True, color="FFFFFF")
F_BODY = Font(name=FONT, size=10)
F_BOLD = Font(name=FONT, size=10, bold=True)
F_INPUT = Font(name=FONT, size=10, color="0000FF", bold=True)
F_LINK = Font(name=FONT, size=10, color="008000")
FILL_HDR = PatternFill("solid", fgColor=NAVY)
FILL_INPUT = PatternFill("solid", fgColor="FFFF00")
FILL_TOTAL = PatternFill("solid", fgColor=LIGHT)
FILL_KPI = PatternFill("solid", fgColor=GREY)
THIN = Side(style="thin", color="C9D1DC")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
WRAP = Alignment(wrap_text=True, vertical="top")

USD = '$#,##0;($#,##0);"-"'
USD2 = '$#,##0.00;($#,##0.00);"-"'
USD4 = '$#,##0.0000;($#,##0.0000);"-"'
PCT = '0.0%;(0.0%);"-"'
PCT2 = '0.00%;(0.00%);"-"'
NUM = '#,##0;(#,##0);"-"'
NUM1 = '#,##0.0;(#,##0.0);"-"'
NUM2 = '#,##0.00;(#,##0.00);"-"'

N = 4500                      # shipments
CD_LAST = N + 1               # Cleaned_Data last data row (header in row 1)


def rng(col: str) -> str:
    """Absolute bounded range on Cleaned_Data for a column letter."""
    return f"Cleaned_Data!${col}$2:${col}${CD_LAST}"


def title(ws, text, sub=None):
    ws["B1"] = text
    ws["B1"].font = F_TITLE
    if sub:
        ws["B2"] = sub
        ws["B2"].font = F_SUB
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 2


def section(ws, cell, text):
    ws[cell] = text
    ws[cell].font = F_SEC


def header(ws, row, col, labels, height=32):
    for i, lab in enumerate(labels):
        c = ws.cell(row=row, column=col + i, value=lab)
        c.font, c.fill, c.alignment, c.border = F_HDR, FILL_HDR, CENTER, BOX
    ws.row_dimensions[row].height = height


def put(ws, row, col, value, fmt=None, font=F_BODY, fill=None, border=True):
    c = ws.cell(row=row, column=col, value=value)
    c.font = font
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = fill
    if border:
        c.border = BOX
    return c


def widths(ws, mapping):
    for k, v in mapping.items():
        ws.column_dimensions[k].width = v


# ------------------------------------------------------------------ data
raw = {p.stem: pd.read_csv(p) for p in RAW.glob("*.csv")}
fact = pd.read_csv(PROC / "shipment_fact.csv", parse_dates=["ship_date", "delivery_date"])
lanes_sorted = pd.read_csv(PROC / "lane_scorecard.csv")  # already sorted by failure cost / shipment desc
carriers = raw["carrier"].assign(carrier=lambda d: d.carrier_name + " (" + d["mode"] + ")")
CARRIERS = carriers.carrier.tolist()
LANES = lanes_sorted.lane.tolist()
YEARS = sorted(fact.year.unique().tolist())

wb = Workbook()
wb.remove(wb.active)
names = ["Raw_Data", "Cleaned_Data", "Data_Dictionary", "Carrier_Cost_Analysis", "Carrier_Performance",
         "Lane_Analysis", "Cost_Model", "Pivot_Analysis", "Executive_Summary"]
S = {n: wb.create_sheet(n) for n in names}

# ====================================================================== Raw_Data
ws = S["Raw_Data"]
ws["A1"] = "RAW DATA - exactly as downloaded from Kaggle (Meridian Supply Chain Dataset, synthetic, MIT licence). " \
           "Left: shipment (4,500 rows). Right: shipment_line (9,059 rows). Other 9 tables: data/raw/*.csv"
ws["A1"].font = F_BOLD
ws.freeze_panes = "A3"
sh = raw["shipment"]
sl = raw["shipment_line"]
for j, col in enumerate(sh.columns, start=1):
    c = ws.cell(row=2, column=j, value=col)
    c.font, c.fill, c.alignment = F_HDR, FILL_HDR, CENTER
for j, col in enumerate(sl.columns, start=len(sh.columns) + 2):
    c = ws.cell(row=2, column=j, value=col)
    c.font, c.fill, c.alignment = F_HDR, FILL_HDR, CENTER
for i, rec in enumerate(sh.itertuples(index=False), start=3):
    for j, v in enumerate(rec, start=1):
        ws.cell(row=i, column=j, value=v)
for i, rec in enumerate(sl.itertuples(index=False), start=3):
    for j, v in enumerate(rec, start=len(sh.columns) + 2):
        ws.cell(row=i, column=j, value=v)
for j in range(1, len(sh.columns) + len(sl.columns) + 2):
    ws.column_dimensions[get_column_letter(j)].width = 14
ws.column_dimensions[get_column_letter(len(sh.columns) + 1)].width = 3

# ================================================================== Cleaned_Data
ws = S["Cleaned_Data"]
CD = [  # (header, source column or formula template, number format)
    ("shipment_id", "shipment_id", "0"), ("ship_date", "ship_date", "yyyy-mm-dd"),
    ("delivery_date", "delivery_date", "yyyy-mm-dd"), ("ship_month", "ship_month", None),
    ("carrier", "carrier", None), ("mode", "mode", None), ("origin_region", "origin_region", None),
    ("dest_region", "dest_region", None), ("lane", "lane", None), ("line_count", "line_count", "0"),
    ("units", "units", NUM), ("weight_kg", "weight_kg", NUM2), ("revenue", "revenue", USD2),
    ("goods_cost", "goods_cost", USD2), ("quoted_transit_days", "quoted_transit_days", "0"),
    ("actual_transit_days", "=C{r}-B{r}", "0"), ("transit_variance_days", "=P{r}-O{r}", "0"),
    ("on_time_flag", "on_time_flag", "0"), ("late_flag", "=1-R{r}", "0"), ("damaged_flag", "damaged_flag", "0"),
    ("successful_flag", "=IF(AND(R{r}=1,T{r}=0),1,0)", "0"), ("freight_cost", "freight_cost", USD2),
    ("late_penalty_cost", "=ROUND(S{r}*M{r}*Cost_Model!$C$6,2)", USD2),
    ("damage_cost", "=ROUND(T{r}*N{r}*Cost_Model!$C$7,2)", USD2),
    ("reshipment_cost", "=ROUND(T{r}*L{r}*Cost_Model!$C$7*Cost_Model!$C$8,2)", USD2),
    ("true_cost", "=V{r}+W{r}+X{r}+Y{r}", USD2), ("year", "year", "0"),
]
COL = {h: get_column_letter(i) for i, (h, _, _) in enumerate(CD, start=1)}
assert COL["late_penalty_cost"] == "W" and COL["true_cost"] == "Z" and COL["lane"] == "I"
for j, (h, _, _) in enumerate(CD, start=1):
    c = ws.cell(row=1, column=j, value=h)
    c.font, c.fill, c.alignment = F_HDR, FILL_HDR, CENTER
for i, rec in enumerate(fact.to_dict("records"), start=2):
    for j, (h, src, fmt) in enumerate(CD, start=1):
        if src.startswith("="):
            v = src.format(r=i)
        else:
            v = rec[src]
            if isinstance(v, pd.Timestamp):
                v = v.to_pydatetime()
        c = ws.cell(row=i, column=j, value=v)
        if fmt:
            c.number_format = fmt
ws.freeze_panes = "B2"
ws.auto_filter.ref = f"A1:{get_column_letter(len(CD))}{CD_LAST}"
for j, (h, _, _) in enumerate(CD, start=1):
    ws.column_dimensions[get_column_letter(j)].width = max(11, len(h) + 2)
ws.column_dimensions["I"].width = 24
ws.column_dimensions["E"].width = 15
ws["P1"].comment = Comment("Formula: delivery_date - ship_date (calendar days)", "Audit")
ws["W1"].comment = Comment("MODELLED: late_flag x revenue x late-penalty rate (Cost_Model!C6)", "Audit")
ws["X1"].comment = Comment("MODELLED: damaged_flag x goods cost x write-off share (Cost_Model!C7)", "Audit")
ws["Y1"].comment = Comment("MODELLED: damaged_flag x weight x write-off share x Air rate/kg (Cost_Model!C7, C8)", "Audit")

# ================================================================ Data_Dictionary
ws = S["Data_Dictionary"]
title(ws, "Data Dictionary", "Cleaned_Data = one row per shipment. Line-level values are summed to shipment grain before any join.")
DD = [
    ("shipment_id", "INTEGER (PK)", "shipment.shipment_id", "Unique shipment identifier"),
    ("ship_date", "DATE", "shipment.ship_date", "Date the shipment left the warehouse"),
    ("delivery_date", "DATE", "shipment.delivery_date", "Date delivered to the customer"),
    ("ship_month", "TEXT (YYYY-MM)", "derived", "Month of ship_date"),
    ("carrier", "TEXT", "carrier.carrier_name + mode", "Carrier label, e.g. 'CARR-4 (Sea)'"),
    ("mode", "TEXT", "carrier.mode", "Road / Rail / Air / Sea"),
    ("origin_region", "TEXT", "warehouse.region", "Region of the shipping warehouse (lane origin)"),
    ("dest_region", "TEXT", "customer.region", "Region of the receiving customer (lane destination)"),
    ("lane", "TEXT", "derived", "origin_region > dest_region"),
    ("line_count", "INTEGER", "COUNT(shipment_line)", "Number of order lines in the shipment"),
    ("units", "INTEGER", "SUM(shipment_line.qty_shipped)", "Units shipped"),
    ("weight_kg", "DECIMAL", "SUM(qty_shipped x product.unit_weight_kg)", "Shipment gross weight (kg)"),
    ("revenue", "DECIMAL ($)", "SUM(shipment_line.revenue)", "Invoice value of the shipment"),
    ("goods_cost", "DECIMAL ($)", "SUM(qty_shipped x product.standard_cost)", "Standard cost of the goods shipped"),
    ("quoted_transit_days", "INTEGER", "carrier.avg_transit_days", "Contracted / quoted transit time of the carrier"),
    ("actual_transit_days", "INTEGER (formula)", "delivery_date - ship_date", "Observed transit time in days"),
    ("transit_variance_days", "INTEGER (formula)", "actual - quoted", "Positive = slower than quoted"),
    ("on_time_flag", "0/1", "shipment.on_time_flag", "Source SLA flag; metric of record for on-time performance"),
    ("late_flag", "0/1 (formula)", "1 - on_time_flag", "Late shipment indicator"),
    ("damaged_flag", "0/1", "shipment.damaged_flag", "Shipment arrived damaged"),
    ("successful_flag", "0/1 (formula)", "on_time = 1 AND damaged = 0", "'Successful on-time delivery' = on time and undamaged"),
    ("freight_cost", "DECIMAL ($)", "SUM(shipment_line.freight_cost)", "Freight billed by the carrier (actual data)"),
    ("late_penalty_cost", "DECIMAL ($) MODELLED", "late_flag x revenue x C6", "Service credit owed to the customer for a late delivery"),
    ("damage_cost", "DECIMAL ($) MODELLED", "damaged_flag x goods_cost x C7", "Write-off of damaged units at standard cost"),
    ("reshipment_cost", "DECIMAL ($) MODELLED", "damaged_flag x weight x C7 x C8", "Expedited Air re-shipment of the written-off units"),
    ("true_cost", "DECIMAL ($)", "freight + penalty + damage + reshipment", "Total cost of using the carrier for this shipment"),
    ("year", "INTEGER", "derived", "Calendar year of ship_date"),
]
header(ws, 4, 2, ["Column", "Type", "Source / Derivation", "Business definition"])
for i, row in enumerate(DD, start=5):
    for j, v in enumerate(row, start=2):
        put(ws, i, j, v).alignment = WRAP
widths(ws, {"B": 24, "C": 22, "D": 42, "E": 60})
r = len(DD) + 7
section(ws, f"B{r}", "Source tables used (Meridian Supply Chain Dataset - all 11 tables in data/raw)")
header(ws, r + 1, 2, ["Table", "Rows", "Primary key", "Role in this audit"])
TB = [("shipment", 4500, "shipment_id", "Fact header: carrier, lane, dates, on-time & damage flags"),
      ("shipment_line", 9059, "ship_line_id", "Fact lines: units, revenue, freight cost (FK shipment_id, product_id)"),
      ("carrier", 4, "carrier_id", "Rate card: mode, cost/kg, quoted transit days"),
      ("warehouse", 4, "warehouse_id", "Lane origin region"), ("customer", 30, "customer_id", "Lane destination region"),
      ("product", 40, "product_id", "Unit weight and standard cost"),
      ("supplier / purchase_order / purchase_order_line", "20 / 3,000 / 7,460", "supplier_id / po_id / po_line_id", "Inbound procurement - profiled, not used"),
      ("inventory_snapshot / production_run", "16,800 / 4,000", "snapshot_id / production_id", "Profiled, not used")]
for i, row in enumerate(TB, start=r + 2):
    for j, v in enumerate(row, start=2):
        put(ws, i, j, v).alignment = WRAP

# ========================================================== Carrier_Cost_Analysis
ws = S["Carrier_Cost_Analysis"]
title(ws, "Carrier Cost Analysis - Freight vs True Cost",
      "All values are SUMIFS/COUNTIFS over Cleaned_Data. Penalty, damage and reshipment costs are modelled (see Cost_Model).")
CCA_H = ["Carrier", "Mode", "Contract rate / kg", "Shipments", "Units", "Weight (kg)", "Revenue", "Goods value",
         "Freight cost", "Late penalty cost", "Damage cost", "Reshipment cost", "Failure cost", "TRUE COST",
         "Freight / kg", "Freight / shipment", "True cost / shipment", "Freight / unit", "TRUE COST / UNIT",
         "Freight / on-time delivery", "True cost / successful delivery", "Hidden-cost uplift %",
         "Share of network true cost", "Rank: contract rate", "Rank: true cost / unit", "Late-shipment revenue"]
header(ws, 5, 2, CCA_H, height=44)
E, R_ = rng(COL["carrier"]), "{r}"
for k, c in enumerate(CARRIERS):
    r = 6 + k
    ci = carriers.iloc[k]
    put(ws, r, 2, c, font=F_BOLD)
    put(ws, r, 3, ci["mode"])
    put(ws, r, 4, f"=INDEX(Cost_Model!$D$16:$D$19,MATCH(B{r},Cost_Model!$B$16:$B$19,0))", USD2, font=F_LINK)
    put(ws, r, 5, f"=COUNTIFS({E},$B{r})", NUM)
    for col, src, fmt in [(6, "units", NUM), (7, "weight_kg", NUM), (8, "revenue", USD), (9, "goods_cost", USD),
                          (10, "freight_cost", USD), (11, "late_penalty_cost", USD), (12, "damage_cost", USD),
                          (13, "reshipment_cost", USD)]:
        put(ws, r, col, f"=SUMIFS({rng(COL[src])},{E},$B{r})", fmt)
    put(ws, r, 14, f"=SUM(K{r}:M{r})", USD)
    put(ws, r, 15, f"=J{r}+N{r}", USD, font=F_BOLD)
    put(ws, r, 16, f"=IFERROR(J{r}/G{r},0)", USD4)
    put(ws, r, 17, f"=IFERROR(J{r}/E{r},0)", USD2)
    put(ws, r, 18, f"=IFERROR(O{r}/E{r},0)", USD2)
    put(ws, r, 19, f"=IFERROR(J{r}/F{r},0)", USD4)
    put(ws, r, 20, f"=IFERROR(O{r}/F{r},0)", USD4, font=F_BOLD)
    put(ws, r, 21, f"=IFERROR(J{r}/COUNTIFS({E},$B{r},{rng(COL['on_time_flag'])},1),0)", USD2)
    put(ws, r, 22, f"=IFERROR(O{r}/SUMIFS({rng(COL['successful_flag'])},{E},$B{r}),0)", USD2)
    put(ws, r, 23, f"=IFERROR(O{r}/J{r}-1,0)", PCT)
    put(ws, r, 24, f"=IFERROR(O{r}/$O$10,0)", PCT)
    put(ws, r, 25, f"=RANK(D{r},$D$6:$D$9,1)", "0")
    put(ws, r, 26, f"=RANK(T{r},$T$6:$T$9,1)", "0")
    put(ws, r, 27, f"=SUMIFS({rng(COL['revenue'])},{E},$B{r},{rng(COL['late_flag'])},1)", USD)
r = 10
put(ws, r, 2, "NETWORK TOTAL", font=F_BOLD, fill=FILL_TOTAL)
put(ws, r, 3, "", fill=FILL_TOTAL)
put(ws, r, 4, "", fill=FILL_TOTAL)
for col in range(5, 16):
    L = get_column_letter(col)
    put(ws, r, col, f"=SUM({L}6:{L}9)", NUM if col in (5, 6, 7) else USD, font=F_BOLD, fill=FILL_TOTAL)
for col, f_, fmt in [(16, "=IFERROR(J10/G10,0)", USD4), (17, "=IFERROR(J10/E10,0)", USD2), (18, "=IFERROR(O10/E10,0)", USD2),
                     (19, "=IFERROR(J10/F10,0)", USD4), (20, "=IFERROR(O10/F10,0)", USD4),
                     (21, f"=IFERROR(J10/SUM({rng(COL['on_time_flag'])}),0)", USD2),
                     (22, f"=IFERROR(O10/SUM({rng(COL['successful_flag'])}),0)", USD2),
                     (23, "=IFERROR(O10/J10-1,0)", PCT), (24, "=SUM(X6:X9)", PCT), (27, "=SUM(AA6:AA9)", USD)]:
    put(ws, r, col, f_, fmt, font=F_BOLD, fill=FILL_TOTAL)
put(ws, r, 25, "", fill=FILL_TOTAL)
put(ws, r, 26, "", fill=FILL_TOTAL)
widths(ws, {"B": 16, "C": 7})
for col in range(4, 28):
    ws.column_dimensions[get_column_letter(col)].width = 13.5
ws.freeze_panes = "C6"
ws.conditional_formatting.add("T6:T9", ColorScaleRule(start_type="min", start_color="63BE7B", mid_type="percentile",
                                                      mid_value=50, mid_color="FFEB84", end_type="max", end_color="F8696B"))
ws.conditional_formatting.add("W6:W9", DataBarRule(start_type="min", end_type="max", color="E07A5F"))
ws.conditional_formatting.add("Z6:Z9", CellIsRule(operator="equal", formula=["1"], fill=PatternFill("solid", fgColor="C6EFCE"),
                                                  font=Font(name=FONT, bold=True, color="006100")))
ws["B12"] = ("Reading the table: 'Hidden-cost uplift %' is how much the carrier really costs above its freight invoice once "
             "modelled late penalties, damage write-offs and Air re-shipments are added. 'Failure cost' = penalty + damage + reshipment.")
ws["B12"].font, ws["B12"].alignment = F_SUB, WRAP
ws.merge_cells("B12:P13")
ch = BarChart(); ch.type = "col"; ch.grouping = "stacked"; ch.overlap = 100
ch.title = "True cost composition by carrier ($)"; ch.y_axis.title = "USD"; ch.y_axis.numFmt = '$#,##0'
ch.add_data(Reference(ws, min_col=10, max_col=13, min_row=5, max_row=9), titles_from_data=True)
ch.set_categories(Reference(ws, min_col=2, min_row=6, max_row=9))
ch.height, ch.width = 8.5, 16
ws.add_chart(ch, "B15")
ch2 = BarChart(); ch2.type = "col"
ch2.title = "Freight / unit vs True cost / unit"; ch2.y_axis.numFmt = '$#,##0.00'
ch2.add_data(Reference(ws, min_col=19, max_col=20, min_row=5, max_row=9), titles_from_data=True)
ch2.set_categories(Reference(ws, min_col=2, min_row=6, max_row=9))
ch2.dataLabels = DataLabelList(); ch2.dataLabels.showVal = True; ch2.dataLabels.numFmt = '$0.00'
ch2.height, ch2.width = 8.5, 16
ws.add_chart(ch2, "K15")
ch3 = BarChart(); ch3.type = "bar"
ch3.title = "Hidden-cost uplift over freight invoice"; ch3.x_axis.numFmt = '0%'
ch3.add_data(Reference(ws, min_col=23, min_row=5, max_row=9), titles_from_data=True)
ch3.set_categories(Reference(ws, min_col=2, min_row=6, max_row=9))
ch3.legend = None; ch3.height, ch3.width = 8.5, 16
ws.add_chart(ch3, "T15")

# ============================================================ Carrier_Performance
ws = S["Carrier_Performance"]
title(ws, "Carrier Performance & Reliability Scorecard",
      "On-time = source on_time_flag. Successful = on time AND undamaged. Composite: 50% true cost/unit, 30% on-time %, 20% damage rate.")
CP_H = ["Carrier", "Shipments", "On-time", "Late", "Damaged", "Successful (on-time & undamaged)", "On-time %", "Late %",
        "Damage rate", "Success rate", "Quoted transit days", "Avg actual transit days", "Avg variance (days)",
        "Rank: reliability", "Rank: lowest damage", "True cost / unit", "Cost score", "Reliability score",
        "Damage score", "COMPOSITE SCORE (0-100)", "RANK: OVERALL"]
header(ws, 5, 2, CP_H, height=44)
for k, c in enumerate(CARRIERS):
    r = 6 + k
    put(ws, r, 2, c, font=F_BOLD)
    put(ws, r, 3, f"=COUNTIFS({E},$B{r})", NUM)
    put(ws, r, 4, f"=COUNTIFS({E},$B{r},{rng(COL['on_time_flag'])},1)", NUM)
    put(ws, r, 5, f"=COUNTIFS({E},$B{r},{rng(COL['late_flag'])},1)", NUM)
    put(ws, r, 6, f"=COUNTIFS({E},$B{r},{rng(COL['damaged_flag'])},1)", NUM)
    put(ws, r, 7, f"=COUNTIFS({E},$B{r},{rng(COL['successful_flag'])},1)", NUM)
    put(ws, r, 8, f"=IFERROR(D{r}/C{r},0)", PCT)
    put(ws, r, 9, f"=IFERROR(E{r}/C{r},0)", PCT)
    put(ws, r, 10, f"=IFERROR(F{r}/C{r},0)", PCT2)
    put(ws, r, 11, f"=IFERROR(G{r}/C{r},0)", PCT)
    put(ws, r, 12, f"=IFERROR(AVERAGEIFS({rng(COL['quoted_transit_days'])},{E},$B{r}),0)", NUM1)
    put(ws, r, 13, f"=IFERROR(AVERAGEIFS({rng(COL['actual_transit_days'])},{E},$B{r}),0)", NUM2)
    put(ws, r, 14, f"=M{r}-L{r}", NUM2)
    put(ws, r, 15, f"=RANK(H{r},$H$6:$H$9,0)", "0")
    put(ws, r, 16, f"=RANK(J{r},$J$6:$J$9,1)", "0")
    put(ws, r, 17, f"=INDEX(Carrier_Cost_Analysis!$T$6:$T$9,MATCH(B{r},Carrier_Cost_Analysis!$B$6:$B$9,0))", USD4, font=F_LINK)
    put(ws, r, 18, f"=IFERROR(1-(Q{r}-MIN($Q$6:$Q$9))/(MAX($Q$6:$Q$9)-MIN($Q$6:$Q$9)),1)", "0.000")
    put(ws, r, 19, f"=IFERROR((H{r}-MIN($H$6:$H$9))/(MAX($H$6:$H$9)-MIN($H$6:$H$9)),1)", "0.000")
    put(ws, r, 20, f"=IFERROR(1-(J{r}-MIN($J$6:$J$9))/(MAX($J$6:$J$9)-MIN($J$6:$J$9)),1)", "0.000")
    put(ws, r, 21, f"=100*(Cost_Model!$C$71*R{r}+Cost_Model!$C$72*S{r}+Cost_Model!$C$73*T{r})", NUM1, font=F_BOLD)
    put(ws, r, 22, f"=RANK(U{r},$U$6:$U$9,0)", "0", font=F_BOLD)
r = 10
put(ws, r, 2, "NETWORK", font=F_BOLD, fill=FILL_TOTAL)
for col in range(3, 8):
    L = get_column_letter(col)
    put(ws, r, col, f"=SUM({L}6:{L}9)", NUM, font=F_BOLD, fill=FILL_TOTAL)
for col, f_, fmt in [(8, "=IFERROR(D10/C10,0)", PCT), (9, "=IFERROR(E10/C10,0)", PCT), (10, "=IFERROR(F10/C10,0)", PCT2),
                     (11, "=IFERROR(G10/C10,0)", PCT), (12, f"=AVERAGE({rng(COL['quoted_transit_days'])})", NUM1),
                     (13, f"=AVERAGE({rng(COL['actual_transit_days'])})", NUM2), (14, "=M10-L10", NUM2)]:
    put(ws, r, col, f_, fmt, font=F_BOLD, fill=FILL_TOTAL)
widths(ws, {"B": 16})
for col in range(3, 23):
    ws.column_dimensions[get_column_letter(col)].width = 12.5
ws.freeze_panes = "C6"
ws.conditional_formatting.add("H6:H9", ColorScaleRule(start_type="min", start_color="F8696B", end_type="max", end_color="63BE7B"))
ws.conditional_formatting.add("J6:J9", ColorScaleRule(start_type="min", start_color="63BE7B", end_type="max", end_color="F8696B"))
ws.conditional_formatting.add("U6:U9", DataBarRule(start_type="num", start_value=0, end_type="num", end_value=100, color="2A7F8E"))
ws.conditional_formatting.add("V6:V9", CellIsRule(operator="equal", formula=["1"], fill=PatternFill("solid", fgColor="C6EFCE"),
                                                  font=Font(name=FONT, bold=True, color="006100")))
ws["B12"] = ("Statistical note: none of the pairwise differences in on-time % or damage rate between carriers is significant "
             "at the 5% level (two-proportion z-tests, all p > 0.2; data/processed/significance_tests.csv). Reliability is "
             "effectively equal across carriers, so cost is the deciding factor. Transit-day columns use dates that are "
             "inconsistent with the on-time flag (see limitations.md).")
ws["B12"].font, ws["B12"].alignment = F_SUB, WRAP
ws.merge_cells("B12:N14")
c1 = BarChart(); c1.type = "col"; c1.title = "On-time % vs Success rate"; c1.y_axis.numFmt = '0%'
c1.y_axis.scaling.min = 0.7; c1.y_axis.scaling.max = 0.9
c1.add_data(Reference(ws, min_col=8, min_row=5, max_row=9), titles_from_data=True)
c1.add_data(Reference(ws, min_col=11, min_row=5, max_row=9), titles_from_data=True)
c1.set_categories(Reference(ws, min_col=2, min_row=6, max_row=9)); c1.height, c1.width = 8, 14
ws.add_chart(c1, "B16")
c2 = BarChart(); c2.type = "col"; c2.title = "Damage rate by carrier"; c2.y_axis.numFmt = '0.0%'
c2.add_data(Reference(ws, min_col=10, min_row=5, max_row=9), titles_from_data=True)
c2.set_categories(Reference(ws, min_col=2, min_row=6, max_row=9)); c2.legend = None; c2.height, c2.width = 8, 14
ws.add_chart(c2, "J16")
c3 = BarChart(); c3.type = "bar"; c3.title = "Composite score (higher = better)"
c3.add_data(Reference(ws, min_col=21, min_row=5, max_row=9), titles_from_data=True)
c3.set_categories(Reference(ws, min_col=2, min_row=6, max_row=9)); c3.legend = None; c3.height, c3.width = 8, 14
ws.add_chart(c3, "R16")

# ================================================================== Lane_Analysis
ws = S["Lane_Analysis"]
title(ws, "Lane Analysis - Origin warehouse region > Destination customer region",
      "Problem rank = highest failure cost (penalty + damage + reshipment) per shipment. Transit variance = actual - quoted days.")
section(ws, "B4", "1. All carriers, by lane (20 lanes)")
LA_H = ["Lane", "Origin", "Destination", "Shipments", "Avg quoted days", "Avg actual days", "Avg variance (days)",
        "Late %", "Damage rate", "Freight / kg", "Failure cost / shipment", "True cost / shipment", "Problem rank"]
header(ws, 5, 2, LA_H, height=36)
I = rng(COL["lane"])
for k, lane in enumerate(LANES):
    r = 6 + k
    o, d = lane.split(" > ")
    put(ws, r, 2, lane, font=F_BOLD); put(ws, r, 3, o); put(ws, r, 4, d)
    put(ws, r, 5, f"=COUNTIFS({I},$B{r})", NUM)
    put(ws, r, 6, f"=IFERROR(AVERAGEIFS({rng(COL['quoted_transit_days'])},{I},$B{r}),0)", NUM2)
    put(ws, r, 7, f"=IFERROR(AVERAGEIFS({rng(COL['actual_transit_days'])},{I},$B{r}),0)", NUM2)
    put(ws, r, 8, f"=G{r}-F{r}", NUM2)
    put(ws, r, 9, f"=IFERROR(COUNTIFS({I},$B{r},{rng(COL['late_flag'])},1)/E{r},0)", PCT)
    put(ws, r, 10, f"=IFERROR(COUNTIFS({I},$B{r},{rng(COL['damaged_flag'])},1)/E{r},0)", PCT)
    put(ws, r, 11, f"=IFERROR(SUMIFS({rng(COL['freight_cost'])},{I},$B{r})/SUMIFS({rng(COL['weight_kg'])},{I},$B{r}),0)", USD4)
    put(ws, r, 12, f"=IFERROR((SUMIFS({rng(COL['late_penalty_cost'])},{I},$B{r})+SUMIFS({rng(COL['damage_cost'])},{I},$B{r})"
                   f"+SUMIFS({rng(COL['reshipment_cost'])},{I},$B{r}))/E{r},0)", USD2)
    put(ws, r, 13, f"=IFERROR(SUMIFS({rng(COL['true_cost'])},{I},$B{r})/E{r},0)", USD2)
    put(ws, r, 14, f"=RANK(L{r},$L$6:$L$25,0)", "0")
LT = 6 + len(LANES)  # 26
put(ws, LT, 2, "ALL LANES", font=F_BOLD, fill=FILL_TOTAL)
put(ws, LT, 3, "", fill=FILL_TOTAL); put(ws, LT, 4, "", fill=FILL_TOTAL)
put(ws, LT, 5, "=SUM(E6:E25)", NUM, font=F_BOLD, fill=FILL_TOTAL)
put(ws, LT, 6, f"=AVERAGE({rng(COL['quoted_transit_days'])})", NUM2, font=F_BOLD, fill=FILL_TOTAL)
put(ws, LT, 7, f"=AVERAGE({rng(COL['actual_transit_days'])})", NUM2, font=F_BOLD, fill=FILL_TOTAL)
put(ws, LT, 8, f"=G{LT}-F{LT}", NUM2, font=F_BOLD, fill=FILL_TOTAL)
put(ws, LT, 9, f"=AVERAGE({rng(COL['late_flag'])})", PCT, font=F_BOLD, fill=FILL_TOTAL)
put(ws, LT, 10, f"=AVERAGE({rng(COL['damaged_flag'])})", PCT, font=F_BOLD, fill=FILL_TOTAL)
put(ws, LT, 11, f"=SUM({rng(COL['freight_cost'])})/SUM({rng(COL['weight_kg'])})", USD4, font=F_BOLD, fill=FILL_TOTAL)
put(ws, LT, 12, f"=(SUM({rng(COL['late_penalty_cost'])})+SUM({rng(COL['damage_cost'])})+SUM({rng(COL['reshipment_cost'])}))/E{LT}",
    USD2, font=F_BOLD, fill=FILL_TOTAL)
put(ws, LT, 13, f"=SUM({rng(COL['true_cost'])})/E{LT}", USD2, font=F_BOLD, fill=FILL_TOTAL)
put(ws, LT, 14, "", fill=FILL_TOTAL)
ws.conditional_formatting.add("L6:L25", ColorScaleRule(start_type="min", start_color="FFFFFF", end_type="max", end_color="F8696B"))
ws.conditional_formatting.add("I6:I25", ColorScaleRule(start_type="min", start_color="FFFFFF", end_type="max", end_color="F4B183"))
ws.conditional_formatting.add("N6:N25", CellIsRule(operator="lessThanOrEqual", formula=["3"],
                                                   fill=PatternFill("solid", fgColor="F8CBAD"), font=Font(name=FONT, bold=True)))

# Table 2 - cheapest carrier by lane (drives the strategy test)
T2 = 30
section(ws, f"B{T2 - 1}", "2. Cheapest contract carrier by lane - selects the 3 'most problematic' lanes for the strategy test")
put(ws, T2 - 1, 9, "Carrier:", font=F_BOLD, border=False)
put(ws, T2 - 1, 10, "=Cost_Model!$C$22", font=F_LINK, border=False)
header(ws, T2, 2, ["Lane", "Shipments", "Late %", "Damage rate", "Freight / kg", "Failure cost / shipment",
                   "Eligible (>= min shipments)", "Problem rank (eligible)"], height=36)
for k, lane in enumerate(LANES):
    r = T2 + 1 + k
    put(ws, r, 2, lane, font=F_BOLD)
    put(ws, r, 3, f"=COUNTIFS({E},$J${T2 - 1},{I},$B{r})", NUM)
    put(ws, r, 4, f"=IFERROR(COUNTIFS({E},$J${T2 - 1},{I},$B{r},{rng(COL['late_flag'])},1)/C{r},0)", PCT)
    put(ws, r, 5, f"=IFERROR(COUNTIFS({E},$J${T2 - 1},{I},$B{r},{rng(COL['damaged_flag'])},1)/C{r},0)", PCT)
    put(ws, r, 6, f"=IFERROR(SUMIFS({rng(COL['freight_cost'])},{E},$J${T2 - 1},{I},$B{r})/SUMIFS({rng(COL['weight_kg'])},{E},$J${T2 - 1},{I},$B{r}),0)", USD4)
    put(ws, r, 7, f"=IFERROR((SUMIFS({rng(COL['late_penalty_cost'])},{E},$J${T2 - 1},{I},$B{r})"
                  f"+SUMIFS({rng(COL['damage_cost'])},{E},$J${T2 - 1},{I},$B{r})"
                  f"+SUMIFS({rng(COL['reshipment_cost'])},{E},$J${T2 - 1},{I},$B{r}))/C{r},0)", USD2)
    put(ws, r, 8, f'=IF(C{r}>=Cost_Model!$C$11,"Yes","No")')
    put(ws, r, 9, f'=IF(H{r}="Yes",COUNTIFS($H${T2 + 1}:$H${T2 + 20},"Yes",$G${T2 + 1}:$G${T2 + 20},">"&G{r})+1,"n/a")', "0")
ws.conditional_formatting.add(f"I{T2 + 1}:I{T2 + 20}", CellIsRule(operator="lessThanOrEqual", formula=["3"],
                              fill=PatternFill("solid", fgColor="F8CBAD"), font=Font(name=FONT, bold=True)))
ws.conditional_formatting.add(f"G{T2 + 1}:G{T2 + 20}", ColorScaleRule(start_type="min", start_color="FFFFFF", end_type="max", end_color="F8696B"))
widths(ws, {"B": 24, "C": 12, "D": 12})
for col in range(5, 15):
    ws.column_dimensions[get_column_letter(col)].width = 13
ws.freeze_panes = "C6"
lc = BarChart(); lc.type = "bar"; lc.title = "Failure cost per shipment by lane (all carriers)"
lc.add_data(Reference(ws, min_col=12, min_row=5, max_row=25), titles_from_data=True)
lc.set_categories(Reference(ws, min_col=2, min_row=6, max_row=25)); lc.legend = None
lc.x_axis.scaling.orientation = "maxMin"; lc.y_axis.numFmt = '$#,##0'; lc.height, lc.width = 12, 16
ws.add_chart(lc, "P5")
lc2 = BarChart(); lc2.type = "col"; lc2.title = "Quoted vs actual transit days by lane"
lc2.add_data(Reference(ws, min_col=6, max_col=7, min_row=5, max_row=25), titles_from_data=True)
lc2.set_categories(Reference(ws, min_col=2, min_row=6, max_row=25)); lc2.height, lc2.width = 10, 24
ws.add_chart(lc2, "P30")

# ===================================================================== Cost_Model
ws = S["Cost_Model"]
title(ws, "Cost Model, Strategy Test & Sensitivity",
      "Blue-on-yellow cells are inputs - change them and every sheet recalculates. All other cells are formulas.")
section(ws, "B4", "1. Assumptions (the dataset has no penalty or reshipment fields - these costs are modelled)")
header(ws, 5, 2, ["Parameter", "Value", "Unit", "Rationale / source"])
ASM = [
    (6, "Late-delivery penalty rate", 0.02, "% of shipment revenue", PCT,
     "Service credit per late shipment. Typical B2B OTIF credits are 1-5% of invoice; 2% is a mid-low assumption. Tested 0-15% in section 5."),
    (7, "Damage write-off share", 0.25, "% of units in a damaged shipment", PCT,
     "Share of a damaged shipment's units written off at standard cost (partial damage, not total loss)."),
    (8, "Expedited reshipment rate", "=INDEX($D$16:$D$19,MATCH(\"CARR-3 (Air)\",$B$16:$B$19,0))", "$ per kg", USD2,
     "Written-off units are re-sent by Air; uses CARR-3 contract rate from carrier.csv (actual data)."),
    (9, "Volume shift share", 0.20, "% of lane volume", PCT, "Proposed strategy: shift 20% of volume."),
    (10, "Number of problem lanes", 3, "lanes", "0", "Proposed strategy: 3 most problematic lanes (table in section 3 has 3 rows)."),
    (11, "Minimum shipments per carrier-lane", 30, "shipments", "0", "Excludes thin carrier-lane samples from the problem-lane ranking."),
    (12, "Target landed-cost reduction", 0.12, "% of network true cost", PCT, "Hypothesis to test - NOT an established result."),
]
for r, lab, val, unit, fmt, why in ASM:
    put(ws, r, 2, lab, font=F_BOLD)
    is_input = not (isinstance(val, str) and val.startswith("="))
    put(ws, r, 3, val, fmt, font=F_INPUT if is_input else F_BODY, fill=FILL_INPUT if is_input else None)
    put(ws, r, 4, unit)
    put(ws, r, 5, why).alignment = WRAP
    ws.row_dimensions[r].height = 30

section(ws, "B14", "2. Carrier rate card (source: carrier.csv)")
header(ws, 15, 2, ["Carrier", "Mode", "Contract rate / kg", "Quoted transit days", "Rate rank (1 = cheapest)"])
for k, ci in carriers.iterrows():
    r = 16 + k
    put(ws, r, 2, ci.carrier, font=F_BOLD); put(ws, r, 3, ci["mode"])
    put(ws, r, 4, float(ci.cost_per_kg), USD2); put(ws, r, 5, int(ci.avg_transit_days), "0")
    put(ws, r, 6, f"=RANK(D{r},$D$16:$D$19,1)", "0")

section(ws, "B21", "3. Strategy test - shift volume from the cheapest to the 2nd-cheapest carrier on the most problematic lanes")
put(ws, 22, 2, "From carrier (cheapest contract rate)", font=F_BOLD)
put(ws, 22, 3, "=INDEX($B$16:$B$19,MATCH(1,$F$16:$F$19,0))", font=F_BOLD)
put(ws, 23, 2, "To carrier (2nd-cheapest contract rate)", font=F_BOLD)
put(ws, 23, 3, "=INDEX($B$16:$B$19,MATCH(2,$F$16:$F$19,0))", font=F_BOLD)
ws["E22"] = ("Method: the moved volume (shift share x the from-carrier's kg, revenue and goods value on the lane) is costed at "
             "expected values for BOTH carriers: lane freight/kg, lane late % x penalty rate x revenue, lane damage rate x "
             "write-off share x (goods value + kg x Air rate). Like-for-like, no double counting.")
ws["E22"].font, ws["E22"].alignment = F_SUB, WRAP
ws.merge_cells("E22:N23")
ws.row_dimensions[22].height = 30; ws.row_dimensions[23].height = 30
SH = ["#", "Lane", "From: shipments", "From: kg", "From: revenue", "From: goods value", "From: freight/kg", "From: late %",
      "From: damage rate", "To: shipments", "To: freight/kg", "To: late %", "To: damage rate", "Moved kg", "Moved revenue",
      "Moved goods value", "Baseline cost (from carrier)", "Scenario cost (to carrier)", "Change in true cost"]
header(ws, 25, 2, SH, height=44)
FROMC, TOC = "$C$22", "$C$23"
LA_LANE, LA_RANK = f"Lane_Analysis!$B${T2 + 1}:$B${T2 + 20}", f"Lane_Analysis!$I${T2 + 1}:$I${T2 + 20}"
for k in range(3):
    r = 26 + k
    put(ws, r, 2, k + 1, "0")
    put(ws, r, 3, f"=INDEX({LA_LANE},MATCH(B{r},{LA_RANK},0))", font=F_BOLD)

    def cs(col, who, r=r):
        return f"SUMIFS({rng(COL[col])},{E},{who},{I},$C{r})"

    def cc(who, extra="", r=r):
        return f"COUNTIFS({E},{who},{I},$C{r}{extra})"
    put(ws, r, 4, f"={cc(FROMC)}", NUM)
    put(ws, r, 5, f"={cs('weight_kg', FROMC)}", NUM)
    put(ws, r, 6, f"={cs('revenue', FROMC)}", USD)
    put(ws, r, 7, f"={cs('goods_cost', FROMC)}", USD)
    put(ws, r, 8, f"=IFERROR({cs('freight_cost', FROMC)}/E{r},0)", USD4)
    put(ws, r, 9, f"=IFERROR({cc(FROMC, ',' + rng(COL['late_flag']) + ',1')}/D{r},0)", PCT)
    put(ws, r, 10, f"=IFERROR({cc(FROMC, ',' + rng(COL['damaged_flag']) + ',1')}/D{r},0)", PCT)
    put(ws, r, 11, f"={cc(TOC)}", NUM)
    put(ws, r, 12, f"=IFERROR({cs('freight_cost', TOC)}/{cs('weight_kg', TOC)},0)", USD4)
    put(ws, r, 13, f"=IFERROR({cc(TOC, ',' + rng(COL['late_flag']) + ',1')}/K{r},0)", PCT)
    put(ws, r, 14, f"=IFERROR({cc(TOC, ',' + rng(COL['damaged_flag']) + ',1')}/K{r},0)", PCT)
    put(ws, r, 15, f"=E{r}*$C$9", NUM)
    put(ws, r, 16, f"=F{r}*$C$9", USD)
    put(ws, r, 17, f"=G{r}*$C$9", USD)
    put(ws, r, 18, f"=O{r}*H{r}+P{r}*I{r}*$C$6+Q{r}*J{r}*$C$7+O{r}*J{r}*$C$7*$C$8", USD)
    put(ws, r, 19, f"=O{r}*L{r}+P{r}*M{r}*$C$6+Q{r}*N{r}*$C$7+O{r}*N{r}*$C$7*$C$8", USD)
    put(ws, r, 20, f"=S{r}-R{r}", USD, font=F_BOLD)
put(ws, 29, 2, "", fill=FILL_TOTAL); put(ws, 29, 3, "TOTAL", font=F_BOLD, fill=FILL_TOTAL)
for col in range(4, 21):
    L = get_column_letter(col)
    if col in (4, 5, 6, 7, 11, 15, 16, 17, 18, 19, 20):
        put(ws, 29, col, f"=SUM({L}26:{L}28)", NUM if col in (4, 5, 11, 15) else USD, font=F_BOLD, fill=FILL_TOTAL)
    else:
        put(ws, 29, col, "", fill=FILL_TOTAL)
ws.conditional_formatting.add("T26:T29", CellIsRule(operator="greaterThan", formula=["0"], font=Font(name=FONT, bold=True, color="C00000")))
ws.conditional_formatting.add("T26:T29", CellIsRule(operator="lessThan", formula=["0"], font=Font(name=FONT, bold=True, color="006100")))

RES = [(31, "Network true cost (all shipments)", f"=SUM({rng(COL['true_cost'])})", USD),
       (32, "Projected change in true cost (negative = saving)", "=T29", USD),
       (33, "Projected change as % of network true cost", "=IFERROR(C32/C31,0)", '0.000%'),
       (34, "True cost on the 3 problem lanes (all carriers)", f"=SUMPRODUCT(SUMIFS({rng(COL['true_cost'])},{I},C26:C28))", USD),
       (35, "Projected change as % of problem-lane true cost", "=IFERROR(C32/C34,0)", '0.000%'),
       (36, "Change required to hit the target", "=-C12*C31", USD),
       (37, "VERDICT", '=IF(C32<=C36,"Target met","Target NOT supported - projected change is "&TEXT(C33,"0.000%")&" vs target -"&TEXT(C12,"0%"))', None)]
for r, lab, f_, fmt in RES:
    put(ws, r, 2, lab, font=F_BOLD)
    put(ws, r, 3, f_, fmt, font=F_BOLD if r in (32, 37) else F_BODY)
ws.merge_cells("C37:J37")
ws["C37"].fill = PatternFill("solid", fgColor="FCE4D6")

section(ws, "B40", "4. Alternative lever - shift Air (CARR-3) weight network-wide to Rail (CARR-2)")
CCA = "Carrier_Cost_Analysis"


def cca(col_letter, carrier_cell):
    return f"INDEX({CCA}!${col_letter}$6:${col_letter}$9,MATCH({carrier_cell},{CCA}!$B$6:$B$9,0))"


def cp(col_letter, carrier_cell):
    return f"INDEX(Carrier_Performance!${col_letter}$6:${col_letter}$9,MATCH({carrier_cell},Carrier_Performance!$B$6:$B$9,0))"


MS = [(41, "Shift FROM", "CARR-3 (Air)", None, True), (42, "Shift TO", "CARR-2 (Rail)", None, True),
      (43, "FROM carrier weight (kg)", f"={cca('G', '$C$41')}", NUM, False),
      (44, "FROM carrier revenue per kg", f"={cca('H', '$C$41')}/C43", USD2, False),
      (45, "FROM carrier goods value per kg", f"={cca('I', '$C$41')}/C43", USD2, False),
      (46, "Expected true cost / kg if carried by FROM",
       f"={cca('P', '$C$41')}+{cp('I', '$C$41')}*$C$6*C44+{cp('J', '$C$41')}*$C$7*(C45+$C$8)", USD4, False),
      (47, "Expected true cost / kg if carried by TO",
       f"={cca('P', '$C$42')}+{cp('I', '$C$42')}*$C$6*C44+{cp('J', '$C$42')}*$C$7*(C45+$C$8)", USD4, False),
      (48, "Saving per kg shifted", "=C46-C47", USD4, False),
      (49, "Share of FROM weight needed to hit the target", "=IFERROR(C12*C31/(C48*C43),0)", PCT, False)]
for r, lab, v, fmt, inp in MS:
    put(ws, r, 2, lab, font=F_BOLD)
    put(ws, r, 3, v, fmt, font=F_INPUT if inp else F_BODY, fill=FILL_INPUT if inp else None)
ws["E41"] = ("Air carries ~25% of weight but ~76% of freight spend with no measurable reliability advantage. Shipment urgency "
             "is not recorded in the data, so the shiftable share must be validated with the business before contracting.")
ws["E41"].font, ws["E41"].alignment = F_SUB, WRAP
ws.merge_cells("E41:N43")
header(ws, 51, 2, ["Share of FROM weight shifted", "Weight shifted (kg)", "Projected saving", "% of network true cost"])
for k, s in enumerate([0.05, 0.10, 0.15, 0.20, 0.25, 0.30]):
    r = 52 + k
    put(ws, r, 2, s, PCT, font=F_INPUT, fill=FILL_INPUT)
    put(ws, r, 3, f"=B{r}*$C$43", NUM)
    put(ws, r, 4, f"=C{r}*$C$48", USD)
    put(ws, r, 5, f"=IFERROR(D{r}/$C$31,0)", PCT)
ws.conditional_formatting.add("E52:E57", CellIsRule(operator="greaterThanOrEqual", formula=["$C$12"],
                                                    fill=PatternFill("solid", fgColor="C6EFCE"), font=Font(name=FONT, bold=True, color="006100")))

section(ws, "B59", "5. Penalty sensitivity - true cost per unit at different late-penalty rates")
header(ws, 60, 2, ["Late-penalty rate"] + CARRIERS + ["Cheapest by true cost"])
for k, rate in enumerate([0.0, 0.01, 0.02, 0.03, 0.05, 0.10, 0.15, 0.25]):
    r = 61 + k
    put(ws, r, 2, rate, PCT, font=F_INPUT, fill=FILL_INPUT)
    for j, c in enumerate(CARRIERS):
        cr = f"{CCA}!${get_column_letter(2)}${6 + j}"
        rr = 6 + j
        put(ws, r, 3 + j, f"=({CCA}!$J${rr}+{CCA}!$L${rr}+{CCA}!$M${rr}+$B{r}*{CCA}!$AA${rr})/{CCA}!$F${rr}", USD4)
    put(ws, r, 7, f"=INDEX($C$60:$F$60,MATCH(MIN(C{r}:F{r}),C{r}:F{r},0))")
ws.conditional_formatting.add("C61:F68", ColorScaleRule(start_type="min", start_color="63BE7B", mid_type="percentile",
                                                        mid_value=50, mid_color="FFEB84", end_type="max", end_color="F8696B"))
# composite weights + break-even
section(ws, "B70", "6. Ranking weights & break-even")
put(ws, 71, 2, "Composite weight: true cost / unit", font=F_BOLD); put(ws, 71, 3, 0.5, PCT, font=F_INPUT, fill=FILL_INPUT)
put(ws, 72, 2, "Composite weight: on-time %", font=F_BOLD); put(ws, 72, 3, 0.3, PCT, font=F_INPUT, fill=FILL_INPUT)
put(ws, 73, 2, "Composite weight: damage rate", font=F_BOLD); put(ws, 73, 3, 0.2, PCT, font=F_INPUT, fill=FILL_INPUT)
FR = f"MATCH($C$22,{CCA}!$B$6:$B$9,0)"
TR = f"MATCH($C$23,{CCA}!$B$6:$B$9,0)"


def per_unit_fixed(m):
    return (f"(INDEX({CCA}!$J$6:$J$9,{m})+INDEX({CCA}!$L$6:$L$9,{m})+INDEX({CCA}!$M$6:$M$9,{m}))/INDEX({CCA}!$F$6:$F$9,{m})")


def late_rev_unit(m):
    return f"INDEX({CCA}!$AA$6:$AA$9,{m})/INDEX({CCA}!$F$6:$F$9,{m})"


put(ws, 75, 2, "Break-even late-penalty rate (cheapest = 2nd-cheapest on true cost / unit)", font=F_BOLD)
put(ws, 75, 3, f"=IFERROR(({per_unit_fixed(TR)}-{per_unit_fixed(FR)})/({late_rev_unit(FR)}-{late_rev_unit(TR)}),0)", PCT, font=F_BOLD)
ws["E75"] = "Penalties would need to exceed this share of revenue per late shipment before the cheapest carrier stops being the cheapest on a true-cost basis."
ws["E75"].font, ws["E75"].alignment = F_SUB, WRAP
ws.merge_cells("E75:N76")
widths(ws, {"B": 44, "C": 24, "D": 20, "E": 15})
for col in range(6, 21):
    ws.column_dimensions[get_column_letter(col)].width = 13.5
ws.column_dimensions["E"].width = 15

# ================================================================== Pivot_Analysis
ws = S["Pivot_Analysis"]
title(ws, "Pivot Analysis - Carrier x Lane and Carrier x Year",
      "Pivot-style cross-tabs built with SUMIFS / COUNTIFS (always in sync with Cleaned_Data; no PivotTable refresh needed).")
section(ws, "B4", "A. True cost per shipment ($) - carrier x lane")
header(ws, 5, 2, ["Lane"] + CARRIERS + ["All carriers"])
section(ws, "I4", "B. On-time % - carrier x lane")
header(ws, 5, 9, ["Lane"] + CARRIERS + ["All carriers"])
for k, lane in enumerate(LANES):
    r = 6 + k
    put(ws, r, 2, lane, font=F_BOLD); put(ws, r, 9, lane, font=F_BOLD)
    for j in range(4):
        cl = get_column_letter(3 + j)
        hdr = f"{cl}$5"
        put(ws, r, 3 + j, f"=IFERROR(SUMIFS({rng(COL['true_cost'])},{E},{hdr},{I},$B{r})/COUNTIFS({E},{hdr},{I},$B{r}),0)", USD)
        cl2 = get_column_letter(10 + j)
        put(ws, r, 10 + j, f"=IFERROR(COUNTIFS({E},{cl2}$5,{I},$I{r},{rng(COL['on_time_flag'])},1)/COUNTIFS({E},{cl2}$5,{I},$I{r}),0)", PCT)
    put(ws, r, 7, f"=IFERROR(SUMIFS({rng(COL['true_cost'])},{I},$B{r})/COUNTIFS({I},$B{r}),0)", USD, font=F_BOLD)
    put(ws, r, 14, f"=IFERROR(COUNTIFS({I},$I{r},{rng(COL['on_time_flag'])},1)/COUNTIFS({I},$I{r}),0)", PCT, font=F_BOLD)
put(ws, 26, 2, "All lanes", font=F_BOLD, fill=FILL_TOTAL); put(ws, 26, 9, "All lanes", font=F_BOLD, fill=FILL_TOTAL)
for j in range(4):
    cl = get_column_letter(3 + j); cl2 = get_column_letter(10 + j)
    put(ws, 26, 3 + j, f"=IFERROR(SUMIFS({rng(COL['true_cost'])},{E},{cl}$5)/COUNTIFS({E},{cl}$5),0)", USD, font=F_BOLD, fill=FILL_TOTAL)
    put(ws, 26, 10 + j, f"=IFERROR(COUNTIFS({E},{cl2}$5,{rng(COL['on_time_flag'])},1)/COUNTIFS({E},{cl2}$5),0)", PCT, font=F_BOLD, fill=FILL_TOTAL)
put(ws, 26, 7, f"=SUM({rng(COL['true_cost'])})/COUNT({rng(COL['true_cost'])})", USD, font=F_BOLD, fill=FILL_TOTAL)
put(ws, 26, 14, f"=AVERAGE({rng(COL['on_time_flag'])})", PCT, font=F_BOLD, fill=FILL_TOTAL)
ws.conditional_formatting.add("C6:F25", ColorScaleRule(start_type="min", start_color="63BE7B", mid_type="percentile", mid_value=50,
                                                       mid_color="FFEB84", end_type="max", end_color="F8696B"))
ws.conditional_formatting.add("J6:M25", ColorScaleRule(start_type="min", start_color="F8696B", mid_type="percentile", mid_value=50,
                                                       mid_color="FFEB84", end_type="max", end_color="63BE7B"))
section(ws, "B29", "C. Carrier x year")
YH = ["Carrier"] + [f"Shipments {y}" for y in YEARS] + [f"Freight {y}" for y in YEARS] + [f"True cost {y}" for y in YEARS] \
     + [f"On-time % {y}" for y in YEARS]
header(ws, 30, 2, YH, height=36)
YR = rng(COL["year"])
for k, c in enumerate(CARRIERS + ["All carriers"]):
    r = 31 + k
    put(ws, r, 2, c, font=F_BOLD, fill=FILL_TOTAL if k == 4 else None)
    cond = f",{E},$B{r}" if k < 4 else ""
    for j, y in enumerate(YEARS):
        put(ws, r, 3 + j, f"=COUNTIFS({YR},{y}{cond})", NUM, fill=FILL_TOTAL if k == 4 else None)
        put(ws, r, 5 + j, f"=SUMIFS({rng(COL['freight_cost'])},{YR},{y}{cond})", USD, fill=FILL_TOTAL if k == 4 else None)
        put(ws, r, 7 + j, f"=SUMIFS({rng(COL['true_cost'])},{YR},{y}{cond})", USD, fill=FILL_TOTAL if k == 4 else None)
        put(ws, r, 9 + j, f"=IFERROR(COUNTIFS({YR},{y}{cond},{rng(COL['on_time_flag'])},1)/{get_column_letter(3 + j)}{r},0)", PCT,
            fill=FILL_TOTAL if k == 4 else None)
section(ws, "B38", "D. Shipments - origin x destination")
dests = sorted(fact.dest_region.unique()); origins = sorted(fact.origin_region.unique())
header(ws, 39, 2, ["Origin \\ Destination"] + dests + ["Total"])
for k, o in enumerate(origins):
    r = 40 + k
    put(ws, r, 2, o, font=F_BOLD)
    for j, d in enumerate(dests):
        put(ws, r, 3 + j, f"=COUNTIFS({rng(COL['origin_region'])},$B{r},{rng(COL['dest_region'])},{get_column_letter(3 + j)}$39)", NUM)
    put(ws, r, 3 + len(dests), f"=SUM(C{r}:{get_column_letter(2 + len(dests))}{r})", NUM, font=F_BOLD)
ws.conditional_formatting.add(f"C40:{get_column_letter(2 + len(dests))}{39 + len(origins)}",
                              ColorScaleRule(start_type="min", start_color="FFFFFF", end_type="max", end_color="5B9BD5"))
widths(ws, {"B": 24, "I": 24, "H": 3})
for col in list(range(3, 8)) + list(range(10, 15)):
    ws.column_dimensions[get_column_letter(col)].width = 14

# =============================================================== Executive_Summary
ws = S["Executive_Summary"]
title(ws, "Executive Summary - Logistics Carrier Performance & Cost Audit",
      "Meridian Supply Chain Dataset (Kaggle, SYNTHETIC teaching data), 4,500 shipments, Jan 2024 - Dec 2025. All figures are live links.")
KPI = [("Total shipments", "=Carrier_Performance!C10", NUM), ("Total freight cost", "=Carrier_Cost_Analysis!J10", USD),
       ("Total true cost", "=Carrier_Cost_Analysis!O10", USD), ("On-time delivery %", "=Carrier_Performance!H10", PCT),
       ("Damage rate", "=Carrier_Performance!J10", PCT2), ("True cost / successful delivery", "=Carrier_Cost_Analysis!V10", USD2)]
for k, (lab, f_, fmt) in enumerate(KPI):
    col = 2 + 2 * k
    ws.merge_cells(start_row=4, start_column=col, end_row=4, end_column=col + 1)
    ws.merge_cells(start_row=5, start_column=col, end_row=5, end_column=col + 1)
    c = ws.cell(row=4, column=col, value=lab); c.font = Font(name=FONT, size=9, bold=True, color="5B6573")
    c.alignment = CENTER; c.fill = FILL_KPI
    ws.cell(row=4, column=col + 1).fill = FILL_KPI
    v = ws.cell(row=5, column=col, value=f_); v.font = Font(name=FONT, size=16, bold=True, color=NAVY)
    v.number_format = fmt; v.alignment = CENTER; v.fill = FILL_KPI
    ws.cell(row=5, column=col + 1).fill = FILL_KPI
ws.row_dimensions[4].height = 22; ws.row_dimensions[5].height = 34
section(ws, "B7", "Carrier snapshot")
header(ws, 8, 2, ["Carrier", "Contract rate / kg", "Rate rank", "Freight cost", "True cost", "True cost / unit",
                  "True-cost rank", "On-time %", "Damage rate", "Hidden-cost uplift", "Composite score", "Overall rank"], height=36)
for k, c in enumerate(CARRIERS):
    r = 9 + k; s = 6 + k
    put(ws, r, 2, c, font=F_BOLD)
    for col, ref, fmt in [(3, f"Carrier_Cost_Analysis!D{s}", USD2), (4, f"Carrier_Cost_Analysis!Y{s}", "0"),
                          (5, f"Carrier_Cost_Analysis!J{s}", USD), (6, f"Carrier_Cost_Analysis!O{s}", USD),
                          (7, f"Carrier_Cost_Analysis!T{s}", USD2), (8, f"Carrier_Cost_Analysis!Z{s}", "0"),
                          (9, f"Carrier_Performance!H{s}", PCT), (10, f"Carrier_Performance!J{s}", PCT2),
                          (11, f"Carrier_Cost_Analysis!W{s}", PCT), (12, f"Carrier_Performance!U{s}", NUM1),
                          (13, f"Carrier_Performance!V{s}", "0")]:
        put(ws, r, col, "=" + ref, fmt, font=F_LINK)
ws.conditional_formatting.add("G9:G12", ColorScaleRule(start_type="min", start_color="63BE7B", end_type="max", end_color="F8696B"))
ws.conditional_formatting.add("K9:K12", DataBarRule(start_type="min", end_type="max", color="E07A5F"))
section(ws, "B14", "Strategy test: shift 20% of cheapest carrier's volume to 2nd-cheapest on the 3 most problematic lanes")
STR = [("From -> To", '=Cost_Model!C22&"  ->  "&Cost_Model!C23', None),
       ("Lanes tested", '=Cost_Model!C26&"; "&Cost_Model!C27&"; "&Cost_Model!C28', None),
       ("Projected change in true cost", "=Cost_Model!C32", USD), ("As % of network true cost", "=Cost_Model!C33", "0.000%"),
       ("12% target equivalent", "=Cost_Model!C36", USD), ("Verdict", "=Cost_Model!C37", None),
       ("Alternative: Air->Rail share needed for 12%", "=Cost_Model!C49", PCT),
       ("Break-even penalty rate (cheapest stops being cheapest)", "=Cost_Model!C75", PCT)]
for k, (lab, f_, fmt) in enumerate(STR):
    r = 15 + k
    put(ws, r, 2, lab, font=F_BOLD)
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
    put(ws, r, 5, f_, fmt, font=F_LINK)
    ws.merge_cells(start_row=r, start_column=5, end_row=r, end_column=13)
section(ws, "B24", "Key findings (numbers reference the cells above)")
FIND = [
    '="1. The cheapest contract carrier, "&Cost_Model!C22&", is ALSO the cheapest on true cost ("&TEXT(Carrier_Cost_Analysis!T9,"$0.00")&"/unit vs "&TEXT(Carrier_Cost_Analysis!T7,"$0.00")&" for "&Cost_Model!C23&") - the hypothesis that it is secretly the most expensive is not supported."',
    '="2. Its hidden costs are real: modelled failure costs ("&TEXT(Carrier_Cost_Analysis!N9,"$#,##0")&") exceed its freight bill ("&TEXT(Carrier_Cost_Analysis!J9,"$#,##0")&"), a "&TEXT(Carrier_Cost_Analysis!W9,"0%")&" uplift - a strong lever for SLA/claims negotiation."',
    '="3. Reliability differences between carriers are small (on-time "&TEXT(MIN(Carrier_Performance!H6:H9),"0.0%")&" to "&TEXT(MAX(Carrier_Performance!H6:H9),"0.0%")&") and not statistically significant."',
    '="4. The proposed 20% shift on 3 lanes changes true cost by "&TEXT(Cost_Model!C32,"$#,##0")&" ("&TEXT(Cost_Model!C33,"0.000%")&") - far from the 12% target."',
    '="5. Air ("&Carrier_Cost_Analysis!B8&") absorbs "&TEXT(Carrier_Cost_Analysis!X8,"0%")&" of network true cost with no reliability advantage; moving ~"&TEXT(Cost_Model!C49,"0%")&" of Air weight to Rail would deliver the 12% target."',
]
for k, f_ in enumerate(FIND):
    r = 25 + k
    c = ws.cell(row=r, column=2, value=f_); c.font = F_BODY; c.alignment = Alignment(wrap_text=True, vertical="center")
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=13)
    ws.row_dimensions[r].height = 30
widths(ws, {"B": 18})
for col in range(3, 14):
    ws.column_dimensions[get_column_letter(col)].width = 13.5
ec = BarChart(); ec.type = "col"; ec.title = "Freight / unit vs True cost / unit by carrier"; ec.y_axis.numFmt = '$#,##0'
ec.add_data(Reference(S["Carrier_Cost_Analysis"], min_col=19, max_col=20, min_row=5, max_row=9), titles_from_data=True)
ec.set_categories(Reference(S["Carrier_Cost_Analysis"], min_col=2, min_row=6, max_row=9)); ec.height, ec.width = 8, 15
ws.add_chart(ec, "B31")
ec2 = BarChart(); ec2.type = "col"; ec2.title = "On-time % by carrier"; ec2.y_axis.numFmt = '0%'
ec2.y_axis.scaling.min = 0.8; ec2.y_axis.scaling.max = 0.9
ec2.add_data(Reference(S["Carrier_Performance"], min_col=8, min_row=5, max_row=9), titles_from_data=True)
ec2.set_categories(Reference(S["Carrier_Performance"], min_col=2, min_row=6, max_row=9)); ec2.legend = None
ec2.height, ec2.width = 8, 13
ws.add_chart(ec2, "I31")

# ------------------------------------------------------------------ finish
for n, w in S.items():
    w.sheet_properties.tabColor = {"Raw_Data": "9AA5B1", "Cleaned_Data": "9AA5B1", "Data_Dictionary": "9AA5B1",
                                   "Cost_Model": "E0A458", "Executive_Summary": "2A7F8E"}.get(n, NAVY)
    if n not in ("Raw_Data", "Cleaned_Data"):
        for row in w.iter_rows():
            for c in row:
                if c.font is not None and c.font.name != FONT:
                    c.font = Font(name=FONT, size=c.font.size, bold=c.font.bold, italic=c.font.italic, color=c.font.color)
for n in ("Raw_Data", "Cleaned_Data"):
    for row in S[n].iter_rows(min_row=3 if n == "Raw_Data" else 2):
        for c in row:
            c.font = F_BODY
wb.active = names.index("Executive_Summary")
wb.calculation.fullCalcOnLoad = True
OUT.parent.mkdir(parents=True, exist_ok=True)
wb.save(OUT)
print("saved", OUT)
