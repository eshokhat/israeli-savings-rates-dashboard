# Israeli Savings Plans — Rate Analysis Pipeline

Automated ETL pipeline that fetches interest rate data for Israeli children's savings plans from the government open data API, transforms it into a clean analytical dataset, and delivers insights through SQL, Excel, and Tableau Public.

Data updates weekly via GitHub Actions — no manual steps required.

---

## Business questions answered

1. Which bank offers the highest and lowest rate today — by plan type and age group?
2. How do average rates compare across banks and savings plans?
3. How is the rate distributed across banks — median, percentiles, standard deviation?
4. Do children's programs (Under 18) offer better rates than adult programs?
5. How have rates trended month-over-month across rate types?
6. Which banks are most volatile — and which are most stable over time?
7. What is the single best deal available right now by plan and age group?

---

## Architecture

```
data.gov.il API
      │
      ▼
pipeline/fetch.py          → data/raw_records.json
      │
      ▼
pipeline/transform.py      → data/savings_rates_clean_long.csv
      │
      ├──▶ pipeline/load.py          → data/savings.duckdb
      │          │
      │          ├──▶ analysis/queries.sql     (SQL analytical layer)
      │          └──▶ pipeline/export_excel.py → excel/savings_analysis.xlsx
      │
      └──▶ Tableau Public dashboard  (reads CSV via raw GitHub URL)

GitHub Actions runs the full pipeline every Sunday and commits the refreshed CSV.
```

---

## Stack

| Layer | Tools |
|---|---|
| Ingestion | Python · requests · pagination + retry logic |
| Transformation | pandas · data cleaning · Hebrew→English mapping · long format |
| Storage | DuckDB · analytical views (`vw_best_rates`, `vw_volatility`) |
| SQL analysis | DuckDB SQL · window functions · CTEs · `QUALIFY` |
| Reporting | Excel (openpyxl) · 6 sheets (Contents + 5 analytical) for stakeholders |
| Visualisation | Tableau Public |
| Automation | GitHub Actions · weekly schedule · auto-commit |
| Testing | pytest · 19 unit tests · data quality checks (validate.py) |

---

## Repository structure

```
├── pipeline/
│   ├── fetch.py            # API ingestion with pagination and retry
│   ├── transform.py        # ETL: clean, normalise, melt to long format
│   ├── load.py             # Load CSV into DuckDB, create analytical views
│   ├── validate.py         # 11 data quality checks, exits 1 on failure
│   └── export_excel.py     # Export SQL results to formatted Excel report
├── analysis/
│   ├── queries.sql         # 7 analytical queries (window fn, CTE, QUALIFY, NTILE)
│   └── insights.md         # Key findings from the data
├── tests/
│   └── test_transform.py   # 19 pytest unit tests for the transform layer
├── data/
│   └── savings_rates_clean_long.csv   # Clean dataset (auto-updated weekly)
├── excel/
│   └── savings_analysis.xlsx          # Stakeholder report (5 sheets)
└── .github/workflows/
    └── update_data.yml     # Weekly CI/CD pipeline
```

---

## Run locally

```bash
# Install dependencies
uv sync

# Full pipeline
uv run python pipeline/fetch.py
uv run python pipeline/transform.py
uv run python pipeline/load.py

# Analytics
uv run python pipeline/export_excel.py
duckdb data/savings.duckdb < analysis/queries.sql

# Tests and validation
uv run pytest tests/ -v
uv run python pipeline/validate.py
```

---

## Data source

[Israeli Ministry of Finance — Children's Savings Plans Interest Rates](https://data.gov.il/dataset/savingsplaninterest)  
Public API · 9 banks · 3 plan types · 3 rate types · data from 2017 up to date
