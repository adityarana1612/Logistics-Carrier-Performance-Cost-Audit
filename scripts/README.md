# Pipeline scripts (optional)

Every deliverable in this repository is already built and committed. **You do not need to run anything** to use the Excel workbook, the SQL script, the dashboard or the reports. These scripts are here for transparency and reproducibility.

## Rebuild order (run from the repository root)

| Step | Command | Produces | Approx. time |
|---|---|---|---|
| 1 | `python scripts/build_analysis.py` | `data/processed/*` (fact table, scorecards, scenarios, DQ report, `summary_metrics.json`) | 5 s |
| 2 | `python scripts/build_excel.py` | `excel/cost_model_excel.xlsx` (formulas, no cached values) | 15 s |
| 3 | `python scripts/cache_excel_values.py` | Evaluates all formulas, fails on any Excel error, and writes cached values into the workbook | 3 min |
| 4 | `python scripts/build_dashboard.py` | `dashboard/carrier_negotiation_dashboard.html` (embeds the fact table into `dashboard_template.html`) | 2 s |

Dependencies: Python 3.10+ and the packages in [requirements.txt](requirements.txt) (`pip install -r scripts/requirements.txt`).

## Changing an assumption
The cost-model parameters live in the `ASSUMPTIONS` dictionary at the top of `build_analysis.py`. The same values appear in SQL (`audit.audit_params`), Excel (`Cost_Model!C6:C12`) and the dashboard sliders. For a quick what-if, edit the yellow cells in Excel or move the dashboard sliders; no rebuild is needed.

## SQL
`sql/carrier_audit.sql` is independent of these scripts. Run it with `psql -d <database> -f sql/carrier_audit.sql` from the repository root (PostgreSQL 13+).
