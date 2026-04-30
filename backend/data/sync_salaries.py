#!/usr/bin/env python3
"""CLI to populate ``player_contracts`` from a salary source.

Usage::

    python data/sync_salaries.py --source spotrac --season 2025-26
    python data/sync_salaries.py --source seed_csv

``--source spotrac`` (default) attempts a live scrape of all 30 team cap
pages and falls back to the seed CSV on any failure (network, anti-bot,
parse error). ``--source seed_csv`` skips the scrape entirely and reads
``data/seed/contracts_2025_26.csv`` directly — useful for offline runs.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal
from services.salary_ingestion_service import sync_salary_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("sync_salaries")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync player contracts into the warehouse.")
    parser.add_argument(
        "--source",
        default="spotrac",
        choices=["spotrac", "seed_csv"],
        help="Salary source. 'spotrac' (default) falls back to seed_csv on failure.",
    )
    parser.add_argument(
        "--season",
        default="2025-26",
        help="Season to scrape (only used when --source=spotrac).",
    )
    parser.add_argument(
        "--seed-path",
        default=None,
        help="Optional override for the seed CSV path.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = sync_salary_data(
            db,
            source=args.source,
            seed_path=args.seed_path,
            season=args.season,
        )
    finally:
        db.close()

    log.info(
        "salary sync complete: source=%s upserted=%s skipped=%s fallback=%s last_synced_at=%s",
        result.get("source"),
        result.get("rows_upserted"),
        result.get("rows_skipped"),
        result.get("fallback_used"),
        result.get("last_synced_at"),
    )


if __name__ == "__main__":
    main()
