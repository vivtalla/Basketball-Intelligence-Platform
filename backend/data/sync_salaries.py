#!/usr/bin/env python3
"""CLI to populate ``player_contracts`` from a salary source.

Usage::

    python data/sync_salaries.py --source seed_csv

Today only ``seed_csv`` is implemented — it loads
``data/seed/contracts_2025_26.csv``. A future ``--source spotrac`` branch
can slot in without changing call sites: the orchestrator just passes
``source`` through to ``services.salary_ingestion_service.sync_salary_data``.
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
        default="seed_csv",
        choices=["seed_csv"],
        help="Salary source. Today only 'seed_csv' is supported.",
    )
    parser.add_argument(
        "--seed-path",
        default=None,
        help="Optional override for the seed CSV path.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = sync_salary_data(db, source=args.source, seed_path=args.seed_path)
    finally:
        db.close()

    log.info(
        "salary sync complete: source=%s upserted=%s skipped=%s last_synced_at=%s",
        result.get("source"),
        result.get("rows_upserted"),
        result.get("rows_skipped"),
        result.get("last_synced_at"),
    )


if __name__ == "__main__":
    main()
