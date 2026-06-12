"""
validate.py
-----------
Data quality checks on the clean long CSV.
Runs as a standalone script — exits with code 1 if any check fails,
which causes the GitHub Actions job to fail and prevents bad data
from being committed to the repo.

Usage:
    python pipeline/validate.py
    python pipeline/validate.py --csv data/savings_rates_clean_long.csv
"""

import argparse
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

DEFAULT_CSV = Path("data/savings_rates_clean_long.csv")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── expected values ───────────────────────────────────────────────────────────
EXPECTED_BANKS = {
    "Discount",
    "Hapoalim",
    "International Bank",
    "Leumi",
    "Massad",
    "Mercantile Discount",
    "Mizrahi-Tefahot",
    "Otsar Ha-Hayal",
    "Yahav",
}
EXPECTED_RATE_TYPES = {
    "Fixed (No Linkage)",
    "Fixed (CPI-Linked)",
    "Variable (Prime Spread)",
}
EXPECTED_AGE_GROUPS = {"Under 18", "Above 18"}
RATE_MIN, RATE_MAX = -10.0, 30.0  # plausible range for Israeli savings rates


# ── check framework ───────────────────────────────────────────────────────────
@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str


@dataclass
class ValidationReport:
    results: list[CheckResult] = field(default_factory=list)

    def add(
        self, name: str, condition: bool, fail_msg: str, pass_msg: str = "OK"
    ) -> None:
        passed = bool(condition)
        msg = pass_msg if passed else fail_msg
        self.results.append(CheckResult(name, passed, msg))
        icon = "✓" if passed else "✗"
        level = log.info if passed else log.error
        level("%s  %-45s  %s", icon, name, msg)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def n_failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)


# ── individual checks ─────────────────────────────────────────────────────────
def run_checks(df: pd.DataFrame) -> ValidationReport:
    report = ValidationReport()

    # ── structural checks ─────────────────────────────────────────────────────
    report.add(
        "CSV is not empty",
        len(df) > 0,
        f"DataFrame has 0 rows",
        f"{len(df):,} rows loaded",
    )

    required_cols = {
        "BANK_EN",
        "SAVINGSPLAN_EN",
        "SAVINGSPROGRAMBYAGE_EN",
        "INTERESTSDATE",
        "YEAR",
        "YEAR_MONTH",
        "RateType",
        "RateValue",
    }
    missing = required_cols - set(df.columns)
    report.add(
        "All required columns present",
        len(missing) == 0,
        f"Missing columns: {missing}",
    )

    # ── completeness checks ───────────────────────────────────────────────────
    null_rate_pct = df["RateValue"].isna().mean() * 100
    report.add(
        "RateValue null rate < 5%",
        null_rate_pct < 5,
        f"RateValue is {null_rate_pct:.1f}% null",
        f"RateValue null rate: {null_rate_pct:.1f}%",
    )

    for col in ["BANK_EN", "SAVINGSPLAN_EN", "RateType"]:
        if col not in df.columns:
            continue
        null_pct = df[col].isna().mean() * 100
        report.add(
            f"No unmapped values in {col}",
            null_pct == 0,
            f"{null_pct:.1f}% of {col} could not be mapped (Hebrew still present?)",
            f"{col}: all values mapped",
        )

    # ── domain checks ─────────────────────────────────────────────────────────
    if "BANK_EN" in df.columns:
        found_banks = set(df["BANK_EN"].dropna().unique())
        missing_banks = EXPECTED_BANKS - found_banks
        report.add(
            "All 9 expected banks present",
            len(missing_banks) == 0,
            f"Missing banks: {missing_banks}",
            f"Banks found: {len(found_banks)}",
        )

    if "RateType" in df.columns:
        found_types = set(df["RateType"].dropna().unique())
        missing_types = EXPECTED_RATE_TYPES - found_types
        report.add(
            "All 3 rate types present",
            len(missing_types) == 0,
            f"Missing rate types: {missing_types}",
        )

    if "SAVINGSPROGRAMBYAGE_EN" in df.columns:
        found_ages = set(df["SAVINGSPROGRAMBYAGE_EN"].dropna().unique())
        missing_ages = EXPECTED_AGE_GROUPS - found_ages
        report.add(
            "Both age groups present (Under 18, Above 18)",
            len(missing_ages) == 0,
            f"Missing age groups: {missing_ages}",
        )

    # ── range checks ──────────────────────────────────────────────────────────
    if "RateValue" in df.columns:
        rates = df["RateValue"].dropna()
        out_of_range = ((rates < RATE_MIN) | (rates > RATE_MAX)).sum()
        report.add(
            f"RateValue within [{RATE_MIN}%, {RATE_MAX}%]",
            out_of_range == 0,
            f"{out_of_range} values outside plausible range",
            f"min={rates.min():.4f}  max={rates.max():.4f}",
        )

    # ── date checks ───────────────────────────────────────────────────────────
    if "INTERESTSDATE" in df.columns:
        dates = pd.to_datetime(df["INTERESTSDATE"], errors="coerce")
        future_dates = (dates > pd.Timestamp.today()).sum()
        report.add(
            "No future dates in INTERESTSDATE",
            future_dates == 0,
            f"{future_dates} rows have future dates",
        )

        earliest = dates.min()
        report.add(
            "Date range starts before 2026",
            pd.notna(earliest) and earliest.year < 2026,
            f"Earliest date is {earliest} — dataset may be truncated",
            f"Earliest date: {earliest.date() if pd.notna(earliest) else 'n/a'}",
        )

    return report


# ── entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Validate clean savings CSV")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    args = parser.parse_args()

    if not args.csv.exists():
        log.error("CSV not found: %s — run transform.py first", args.csv)
        sys.exit(1)

    df = pd.read_csv(args.csv, parse_dates=["INTERESTSDATE"])
    log.info("Loaded %d rows from %s", len(df), args.csv)
    log.info("── Running data quality checks ──────────────────────────────")

    report = run_checks(df)

    log.info("─────────────────────────────────────────────────────────────")
    if report.passed:
        log.info("All checks passed ✓")
    else:
        log.error("%d check(s) FAILED — fix data before committing", report.n_failed)
        sys.exit(1)


if __name__ == "__main__":
    main()
