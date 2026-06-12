"""
fetch.py
--------
Fetches raw savings plan data from the Israeli government open data API
(data.gov.il) with pagination support and saves it as raw JSON.

Usage:
    python fetch.py
    python fetch.py --out data/raw_records.json

Output:
    data/raw_records.json  — list of raw record dicts from the API
"""

import argparse
import json
import logging
import time
from pathlib import Path

import requests

# ── configuration ────────────────────────────────────────────────────────────
API_URL = "https://data.gov.il/api/3/action/datastore_search"
RESOURCE_ID = "a737b311-c6d8-4084-9ac9-c40d0fd01125"
PAGE_SIZE = 10_000  # max rows per request the API comfortably handles
TIMEOUT = 20  # seconds per request
RETRY_WAIT = 5  # seconds between retries
MAX_RETRIES = 3
DEFAULT_OUT = Path("data/raw_records.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── helpers ───────────────────────────────────────────────────────────────────
def _get_page(offset: int, limit: int) -> list[dict]:
    """Fetch one page of records; retries on transient errors."""
    params = {
        "resource_id": RESOURCE_ID,
        "limit": limit,
        "offset": offset,
    }
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(API_URL, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            payload = resp.json()
            if not payload.get("success"):
                raise ValueError(f"API returned success=false: {payload}")
            return payload["result"]["records"]
        except requests.exceptions.RequestException as exc:
            log.warning("Attempt %d/%d failed: %s", attempt, MAX_RETRIES, exc)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_WAIT)
    raise RuntimeError(f"All {MAX_RETRIES} attempts failed for offset={offset}")


def fetch_all() -> list[dict]:
    """Paginate through the entire dataset and return all records."""
    # First call: also grab total count so we can log progress
    first_params = {
        "resource_id": RESOURCE_ID,
        "limit": 1,
        "offset": 0,
        "include_total": True,
    }
    resp = requests.get(API_URL, params=first_params, timeout=TIMEOUT)
    resp.raise_for_status()
    total = resp.json()["result"].get("total", "?")
    log.info("Total records reported by API: %s", total)

    records: list[dict] = []
    offset = 0

    while True:
        page = _get_page(offset, PAGE_SIZE)
        if not page:
            break
        records.extend(page)
        log.info("Fetched %d records so far (offset=%d)…", len(records), offset)
        if len(page) < PAGE_SIZE:
            break  # last page
        offset += PAGE_SIZE

    log.info("Done. Total records fetched: %d", len(records))
    return records


# ── main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch savings plan data from data.gov.il"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output JSON path (default: {DEFAULT_OUT})",
    )
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)

    records = fetch_all()

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    log.info("Saved %d records → %s", len(records), args.out)


if __name__ == "__main__":
    main()
