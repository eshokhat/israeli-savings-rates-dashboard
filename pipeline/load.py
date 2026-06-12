"""
load.py
-------
Loads the clean long-format CSV into a DuckDB database.
Designed to be idempotent: running it again on updated data replaces
the existing table without manual cleanup.

Usage:
    python load.py
    python load.py --csv data/savings_rates_clean_long.csv --db data/savings.duckdb

Schema created:
    savings_rates  — main fact table (all rows from the long CSV)
    vw_best_rates  — view: best rate per bank × plan type × age group (today)
    vw_volatility  — view: Δ (max–min) per bank × rate type
"""

import argparse
import logging
from pathlib import Path

import duckdb
import pandas as pd

# ── configuration ─────────────────────────────────────────────────────────────
DEFAULT_CSV = Path("data/savings_rates_clean_long.csv")
DEFAULT_DB = Path("data/savings.duckdb")
TABLE_NAME = "savings_rates"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── DDL helpers ───────────────────────────────────────────────────────────────
CREATE_VIEWS = """
-- Best rate per bank × plan × age group (most recent date)
CREATE OR REPLACE VIEW vw_best_rates AS
WITH latest AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY BANK_EN, SAVINGSPLAN_EN, SAVINGSPROGRAMBYAGE_EN, RateType
               ORDER BY INTERESTSDATE DESC
           ) AS rn
    FROM savings_rates
    WHERE RateValue IS NOT NULL
)
SELECT
    BANK_EN,
    SAVINGSPLAN_EN,
    SAVINGSPROGRAMBYAGE_EN,
    RateType,
    RateValue            AS LatestRate,
    INTERESTSDATE        AS AsOfDate
FROM latest
WHERE rn = 1;

-- Volatility: Δ (max–min) per bank × rate type across full history
CREATE OR REPLACE VIEW vw_volatility AS
SELECT
    BANK_EN,
    RateType,
    ROUND(MAX(RateValue) - MIN(RateValue), 4)  AS Delta,
    ROUND(AVG(RateValue), 4)                   AS AvgRate,
    ROUND(MIN(RateValue), 4)                   AS MinRate,
    ROUND(MAX(RateValue), 4)                   AS MaxRate,
    COUNT(*)                                   AS Observations
FROM savings_rates
WHERE RateValue IS NOT NULL
GROUP BY BANK_EN, RateType
ORDER BY Delta DESC;
"""


# ── main ─────────────────────────────────────────────────────────────────────
def load(csv_path: Path, db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)

    log.info("Reading CSV: %s", csv_path)
    df = pd.read_csv(csv_path, parse_dates=["INTERESTSDATE"])
    log.info("Rows to load: %d", len(df))

    con = duckdb.connect(str(db_path))

    # Replace table on every run — idempotent, safe for GitHub Actions
    log.info("Writing table '%s' to %s …", TABLE_NAME, db_path)
    con.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
    con.execute(f"CREATE TABLE {TABLE_NAME} AS SELECT * FROM df")

    row_count = con.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
    log.info("Table '%s' loaded: %d rows", TABLE_NAME, row_count)

    # Create analytical views
    con.execute(CREATE_VIEWS)
    log.info("Views created: vw_best_rates, vw_volatility")

    # Quick sanity-check output
    log.info("── Top 5 best rates right now ──")
    result = con.execute("""
        SELECT BANK_EN, SAVINGSPLAN_EN, SAVINGSPROGRAMBYAGE_EN,
               RateType, LatestRate, AsOfDate
        FROM vw_best_rates
        ORDER BY LatestRate DESC
        LIMIT 5
    """).df()
    print(result.to_string(index=False))

    con.close()
    log.info("Done. Database: %s", db_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Load clean CSV into DuckDB")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()

    load(args.csv, args.db)


if __name__ == "__main__":
    main()
