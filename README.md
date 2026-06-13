# Israeli Savings Plans — Rate Analysis Pipeline

Automated ETL pipeline that fetches interest rate data for Israeli children's savings plans from the government open data API, transforms it into a clean analytical dataset, and delivers insights through SQL, Excel, and Tableau Public.

Data updates weekly via GitHub Actions — no manual steps required.

## Dashboard

[View on Tableau Public](https://public.tableau.com/views/IsraeliSavingsPlansDashboard/Dashboard1-MarketOverview)

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

## Key findings

- **Mizrahi-Tefahot** leads today with 4.45% Fixed (No Linkage); **Leumi** leads historically (avg 3.94%)
- **Yahav** is a consistent underperformer across almost all metrics
- Variable (Prime Spread) rates are effectively frozen — banks compete on Fixed rates, not Variable spreads
- The market is in a slow downward trend: Fixed (No Linkage) dropped ~4% over 14 months
- Most savings plans are age-segregated — Under 18 and Above 18 products rarely overlap
- **Discount** and **Mercantile Discount** are the most stable banks for Fixed (No Linkage)

Full analysis: [analysis/insights.md](analysis/insights.md)

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
      └──▶ Tableau Public dashboard  (manually refreshed from local CSV)

GitHub Actions runs the full pipeline every Sunday and commits the refreshed CSV.
```

---

## Stack

| Layer | Tools |
|---|---|
| Ingestion | Python · requests · pagination + retry logic |
| Transformation | pandas · data cleaning · Hebrew→English mapping · long format |
| Storage | DuckDB · analytical views (`vw_best_rates`, `vw_volatility`) |
| SQL analysis | DuckDB SQL · window functions · CTEs · `QUALIFY` · `NTILE` |
| Reporting | Excel (openpyxl) · 6 sheets (Contents + 5 analytical) for stakeholders |
| Visualisation | Tableau Public · LOD expressions · calculated fields |
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
│   └── savings_analysis.xlsx          # Stakeholder report (6 sheets)
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
uv run python -c "
import duckdb
con = duckdb.connect('data/savings.duckdb')
sql = open('analysis/queries.sql').read()
for i, q in enumerate([s.strip() for s in sql.split(';') if s.strip()], 1):
    try:
        print(f'\n── Q{i} ──')
        print(con.execute(q).df().to_string(index=False))
    except Exception as e:
        print(f'Q{i} skipped: {e}')
"

# Tests and validation
uv run pytest tests/ -v
uv run python pipeline/validate.py
```

---

## Known Limitations & Next Steps

- **Variable (Prime Spread)** represents the spread to Israel's Prime Rate (~4.5%), not standalone yield. Actual return = Prime Rate + Spread. A future version will join this dataset with Bank of Israel rate history to compute true yields.
- Data available from May 2025 only (API limitation — earlier history not exposed via public endpoint).
- Tableau dashboard refreshed manually; automatic refresh requires Tableau Cloud.
- Q4 gap analysis (Under 18 vs Above 18) limited by age-segregated product structure in source data.

---

## Data source

[Israeli Ministry of Finance — Children's Savings Plans Interest Rates](https://data.gov.il/dataset/savingsplaninterest)  
Public API · 9 banks · 3 plan types · 3 rate types · updated regularly
