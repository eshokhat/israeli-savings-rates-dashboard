"""
tests/test_transform.py
-----------------------
Smoke tests for the transform pipeline.
Tests run on a small synthetic fixture — no API calls, no files on disk.

Run:
    uv run pytest tests/ -v
"""

# Import the transform function directly — no side effects
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "pipeline"))
from transform import BANK_EN, SAVINGSPLAN_EN, SAVINGSPROGRAMBYAGE_EN, transform


# ── fixtures ──────────────────────────────────────────────────────────────────
def _make_records(n: int = 6) -> list[dict]:
    """Minimal synthetic records that mirror the real API response shape."""
    banks = list(BANK_EN.keys())
    plans = list(SAVINGSPLAN_EN.keys())
    ages = list(SAVINGSPROGRAMBYAGE_EN.keys())
    records = []
    for i in range(n):
        records.append(
            {
                "_id": i + 1,
                "INTERESTSDATE": "01/01/2024",
                "BANK": banks[i % len(banks)],
                "SAVINGSPLAN": plans[i % len(plans)],
                "SAVINGSPROGRAMBYAGE": ages[i % len(ages)],
                "SAVINGSPERIOD": "5 years",
                "AGE": "0-18" if i % 2 == 0 else "18+",
                "FIXEDWITHOUTLINKAGEVAL": str(round(2.5 + i * 0.1, 2)),
                "FIXEDLINKEDCONSUMERPRICEINDVAL": str(round(1.2 + i * 0.05, 2)),
                "VARIABLESPREAD": str(round(-0.5 + i * 0.3, 2)),
            }
        )
    return records


@pytest.fixture
def clean_df() -> pd.DataFrame:
    return transform(_make_records(6))


# ── structural tests ──────────────────────────────────────────────────────────
class TestOutputShape:
    def test_not_empty(self, clean_df):
        assert len(clean_df) > 0

    def test_required_columns_present(self, clean_df):
        required = {
            "BANK_EN",
            "SAVINGSPLAN_EN",
            "SAVINGSPROGRAMBYAGE_EN",
            "INTERESTSDATE",
            "YEAR",
            "MONTH",
            "YEAR_MONTH",
            "RateType",
            "RateValue",
            "IsNegative",
            "AvgRate_ByGroup",
            "Delta_ByGroup",
        }
        missing = required - set(clean_df.columns)
        assert missing == set(), f"Missing columns: {missing}"

    def test_row_count_is_three_times_input(self, clean_df):
        # melt produces 3 rows per input record (one per rate type)
        assert len(clean_df) == 6 * 3


# ── mapping tests ─────────────────────────────────────────────────────────────
class TestMappings:
    def test_no_null_bank_en(self, clean_df):
        assert clean_df["BANK_EN"].notna().all(), "Some BANK_EN values failed to map"

    def test_no_null_plan_en(self, clean_df):
        assert clean_df["SAVINGSPLAN_EN"].notna().all()

    def test_no_null_age_en(self, clean_df):
        assert clean_df["SAVINGSPROGRAMBYAGE_EN"].notna().all()

    def test_rate_type_values(self, clean_df):
        expected = {
            "Fixed (No Linkage)",
            "Fixed (CPI-Linked)",
            "Variable (Prime Spread)",
        }
        assert set(clean_df["RateType"].unique()) == expected


# ── date tests ────────────────────────────────────────────────────────────────
class TestDates:
    def test_interestsdate_is_datetime(self, clean_df):
        assert pd.api.types.is_datetime64_any_dtype(clean_df["INTERESTSDATE"])

    def test_year_column_correct(self, clean_df):
        assert (clean_df["YEAR"] == 2024).all()

    def test_month_column_correct(self, clean_df):
        assert (clean_df["MONTH"] == 1).all()

    def test_year_month_format(self, clean_df):
        assert clean_df["YEAR_MONTH"].str.match(r"^\d{4}-\d{2}$").all()


# ── numeric tests ─────────────────────────────────────────────────────────────
class TestRateValues:
    def test_rate_value_is_numeric(self, clean_df):
        assert pd.api.types.is_float_dtype(clean_df["RateValue"])

    def test_no_null_rate_values(self, clean_df):
        # synthetic data has no nulls — all values should survive
        assert clean_df["RateValue"].notna().all()

    def test_is_negative_flag(self, clean_df):
        neg_mask = clean_df["RateValue"] < 0
        assert (clean_df.loc[neg_mask, "IsNegative"] == 1).all()
        assert (clean_df.loc[~neg_mask, "IsNegative"] == 0).all()

    def test_avg_rate_by_group_is_float(self, clean_df):
        assert pd.api.types.is_float_dtype(clean_df["AvgRate_ByGroup"])

    def test_delta_non_negative(self, clean_df):
        assert (clean_df["Delta_ByGroup"] >= 0).all()


# ── edge cases ────────────────────────────────────────────────────────────────
class TestEdgeCases:
    def test_empty_input_returns_empty_df(self):
        result = transform([])
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_null_rate_values_are_dropped(self):
        records = _make_records(2)
        records[0]["FIXEDWITHOUTLINKAGEVAL"] = None
        records[1]["FIXEDLINKEDCONSUMERPRICEINDVAL"] = ""
        result = transform(records)
        # null/empty values should be dropped by dropna in melt
        assert result["RateValue"].notna().all()

    def test_unknown_bank_maps_to_null(self):
        records = _make_records(1)
        records[0]["BANK"] = "בנק לא קיים"  # unknown Hebrew bank name
        result = transform(records)
        # unknown bank → BANK_EN should be NaN (unmapped)
        assert result["BANK_EN"].isna().any()
