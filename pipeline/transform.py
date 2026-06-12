"""
transform.py
------------
Reads raw_records.json produced by fetch.py, cleans and normalises the data,
and outputs a tidy long-format CSV ready for DuckDB / Tableau / Excel.

Usage:
    python transform.py
    python transform.py --in data/raw_records.json --out data/savings_rates_clean_long.csv

Key operations (mirrors + extends the original main.py logic):
    1. Hebrew → English label mapping (banks, plan types, age groups)
    2. Date parsing, YEAR / MONTH / YEAR_MONTH columns
    3. Numeric coercion + negative-value flag
    4. Melt from wide (3 rate columns) to long (RateType / RateValue)
    5. Derived columns: AverageRate, Δ volatility per group
"""

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

# ── configuration ─────────────────────────────────────────────────────────────
DEFAULT_IN = Path("data/raw_records.json")
DEFAULT_OUT = Path("data/savings_rates_clean_long.csv")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── mapping dictionaries (from original main.py, extended) ───────────────────
BANK_EN = {
    "אוצר החייל": "Otsar Ha-Hayal",
    "דיסקונט": "Discount",
    "הבינלאומי": "International Bank",
    "הפועלים": "Hapoalim",
    "יהב": "Yahav",
    "לאומי": "Leumi",
    "מזרחי טפחות": "Mizrahi-Tefahot",
    "מסד": "Massad",
    "מרכנתיל דיסקונט": "Mercantile Discount",
}

SAVINGSPLAN_EN = {
    "הפקדה ללא תחנות יציאה": "Fixed Deposit (No Early Withdrawal)",
    "הפקדה עם אפשרות לתחנות יציאה כל 5 שנים": "Deposit with 5-Year Exit Option",
    "צבירת ריבית על סכום חד פעמי": "One-Time Deposit with Interest Accumulation",
}

SAVINGSPROGRAMBYAGE_EN = {
    "עד 18": "Under 18",
    "מעל 18": "Above 18",
}

RATE_TYPE_MAP = {
    "FIXEDWITHOUTLINKAGEVAL": "Fixed (No Linkage)",
    "FIXEDLINKEDCONSUMERPRICEINDVAL": "Fixed (CPI-Linked)",
    "VARIABLESPREAD": "Variable (Prime Spread)",
}

VALUE_COLS = list(RATE_TYPE_MAP.keys())

ID_COLS = [
    "BANK_EN",
    "SAVINGSPLAN_EN",
    "SAVINGSPROGRAMBYAGE_EN",
    "SAVINGSPERIOD",
    "INTERESTSDATE",
    "YEAR",
    "MONTH",
    "YEAR_MONTH",
]


# ── helpers ───────────────────────────────────────────────────────────────────
def _map_col(df: pd.DataFrame, src: str, mapping: dict, dst: str) -> pd.DataFrame:
    """Safe column mapping with unmapped-value logging."""
    if src not in df.columns:
        log.warning("Column '%s' not found — skipping mapping.", src)
        df[dst] = None
        return df
    unmapped = df[~df[src].isin(mapping) & df[src].notna()][src].unique()
    if len(unmapped):
        log.warning("Unmapped values in '%s': %s", src, list(unmapped))
    df[dst] = df[src].map(mapping)
    return df


def _to_numeric(series: pd.Series) -> pd.Series:
    """Strip stray characters and coerce to float."""
    return (
        series.astype(str)
        .str.replace(",", ".", regex=False)
        .str.replace(r"[^0-9.\-]", "", regex=True)
        .replace("", pd.NA)
        .pipe(pd.to_numeric, errors="coerce")
    )


# ── main transform pipeline ───────────────────────────────────────────────────
def transform(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    log.info("Raw shape: %s", df.shape)

    if df.empty:
        log.warning("Empty input — returning empty DataFrame.")
        return pd.DataFrame()

    # 1. Hebrew → English
    df = _map_col(df, "BANK", BANK_EN, "BANK_EN")
    df = _map_col(df, "SAVINGSPLAN", SAVINGSPLAN_EN, "SAVINGSPLAN_EN")
    df = _map_col(
        df, "SAVINGSPROGRAMBYAGE", SAVINGSPROGRAMBYAGE_EN, "SAVINGSPROGRAMBYAGE_EN"
    )

    # 2. Numeric coercion for rate columns
    for col in VALUE_COLS:
        if col in df.columns:
            df[col] = _to_numeric(df[col])

    # 3. Date parsing
    df["INTERESTSDATE"] = pd.to_datetime(
        df["INTERESTSDATE"], format="%d/%m/%Y", errors="coerce"
    )
    df["YEAR"] = df["INTERESTSDATE"].dt.year.astype("Int64")
    df["MONTH"] = df["INTERESTSDATE"].dt.month.astype("Int64")
    df["YEAR_MONTH"] = df["INTERESTSDATE"].dt.to_period("M").astype(str)

    # 4. Melt wide → long
    df_long = df.melt(
        id_vars=[c for c in ID_COLS if c in df.columns],
        value_vars=[c for c in VALUE_COLS if c in df.columns],
        var_name="RateType",
        value_name="RateValue",
    ).dropna(subset=["RateValue"])

    df_long["RateType"] = df_long["RateType"].map(RATE_TYPE_MAP)

    # 5. Flag negative values (nominal loss after inflation — useful for Tableau annotation)
    df_long["IsNegative"] = (df_long["RateValue"] < 0).astype(int)

    # 6. Derived aggregation columns (per bank × plan × rate type)
    grp = df_long.groupby(["BANK_EN", "SAVINGSPLAN_EN", "RateType"])["RateValue"]
    df_long["AvgRate_ByGroup"] = (
        df_long.groupby(["BANK_EN", "SAVINGSPLAN_EN", "RateType"])["RateValue"]
        .transform("mean")
        .round(4)
    )

    df_long["Delta_ByGroup"] = (grp.transform("max") - grp.transform("min")).round(4)

    log.info("Clean long shape: %s", df_long.shape)
    log.info("Banks: %s", sorted(df_long["BANK_EN"].dropna().unique()))
    log.info(
        "Date range: %s → %s",
        df_long["INTERESTSDATE"].min().date(),
        df_long["INTERESTSDATE"].max().date(),
    )

    return df_long


# ── entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transform raw savings data to clean long CSV"
    )
    parser.add_argument("--in", dest="src", type=Path, default=DEFAULT_IN)
    parser.add_argument("--out", dest="dst", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    with open(args.src, encoding="utf-8") as f:
        records = json.load(f)
    log.info("Loaded %d records from %s", len(records), args.src)

    df_long = transform(records)

    args.dst.parent.mkdir(parents=True, exist_ok=True)
    df_long.to_csv(args.dst, index=False, float_format="%.4f", encoding="utf-8")
    log.info("Saved → %s", args.dst)


if __name__ == "__main__":
    main()
