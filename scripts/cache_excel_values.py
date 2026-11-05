"""
Evaluates every formula in excel/cost_model_excel.xlsx with the open-source
`formulas` engine, fails if any formula returns an Excel error, and writes the
computed results into the file as cached values.

Why: openpyxl saves formulas without results, so viewers that do not run a
calculation engine (file previewers, pandas, some web viewers) would show empty
cells. The formulas themselves are untouched and Excel still performs a full
recalculation when the workbook is opened (fullCalcOnLoad=1).

Already run - the committed workbook contains cached values. Kept for transparency.
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import formulas

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "excel" / "cost_model_excel.xlsx"


def evaluate(path: Path) -> dict[tuple[str, str], object]:
    model = formulas.ExcelModel().loads(str(path)).finish()
    sol = model.calculate()
    out = {}
    for k, v in sol.items():
        m = re.match(r"'\[.*?\](.*?)'!([A-Z]+\d+)$", k)
        if not m:
            continue
        val = getattr(v, "value", None)
        while hasattr(val, "tolist"):
            val = val.tolist()
        while isinstance(val, list):
            val = val[0] if val else None
        out[(m.group(1).upper(), m.group(2))] = val
    return out


def main():
    vals = evaluate(XLSX)
    z = zipfile.ZipFile(XLSX)
    wb = z.read("xl/workbook.xml").decode()
    rels = z.read("xl/_rels/workbook.xml.rels").decode()
    rid_target = dict(re.findall(r'Id="(rId\d+)" Target="/?(?:xl/)?([^"]+)"', rels)) or \
        {a: b for b, a in re.findall(r'Target="/?(?:xl/)?([^"]+)"[^>]*Id="(rId\d+)"', rels)}
    sheet_file = {}
    for name, rid in re.findall(r'<sheet name="([^"]+)"[^>]*r:id="(rId\d+)"', wb):
        sheet_file["xl/" + rid_target[rid].lstrip("/")] = name.upper()

    pat = re.compile(r'<c r="([A-Z]+\d+)"((?: [a-z]+="[^"]*")*)><f>(.*?)</f><v ?/>(?:</v>)?</c>', re.S)
    errors, n = [], 0

    def repl(m, sheet):
        nonlocal n
        cell, attrs, f = m.group(1), m.group(2), m.group(3)
        v = vals.get((sheet, cell))
        attrs = re.sub(r' t="[^"]*"', "", attrs)
        n += 1
        s = str(v)
        if v is None:
            return f'<c r="{cell}"{attrs}><f>{f}</f></c>'
        if s.startswith("#") or type(v).__name__.endswith("Error"):
            errors.append((sheet, cell, s))
            return m.group(0)
        if isinstance(v, bool):
            return f'<c r="{cell}"{attrs} t="b"><f>{f}</f><v>{int(v)}</v></c>'
        if isinstance(v, (int, float)):
            return f'<c r="{cell}"{attrs}><f>{f}</f><v>{repr(float(v))}</v></c>'
        return f'<c r="{cell}"{attrs} t="str"><f>{f}</f><v>{escape(s)}</v></c>'

    tmp = XLSX.with_suffix(".tmp.xlsx")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
        for item in z.infolist():
            data = z.read(item.filename)
            if item.filename in sheet_file:
                sheet = sheet_file[item.filename]
                data = pat.sub(lambda m: repl(m, sheet), data.decode()).encode()
            out.writestr(item, data)
    z.close()
    if errors:
        tmp.unlink()
        sys.exit(f"{len(errors)} formula errors, workbook NOT updated: {errors[:10]}")
    tmp.replace(XLSX)
    print(f"cached values written for {n} formula cells; 0 errors")


if __name__ == "__main__":
    main()
