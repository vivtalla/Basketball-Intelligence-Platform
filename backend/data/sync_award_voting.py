#!/usr/bin/env python3
"""Sprint 79 Stream A1 — load historical MVP voting from the seed CSV.

One-time backfill (or re-run when the CSV is updated). Not wired into
``daily_sync.sh`` — voting outcomes are annual, not nightly.

Usage:
    python data/sync_award_voting.py
    python data/sync_award_voting.py --source seed_csv
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal
from services.award_voting_ingestion_service import sync_award_voting

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("sync_award_voting")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load historical award voting from seed CSV")
    parser.add_argument(
        "--source",
        default="seed_csv",
        choices=["seed_csv"],  # future: "basketball_reference" scrape
    )
    parser.add_argument("--seed-path", default=None, help="Override path to seed CSV")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = sync_award_voting(db, source=args.source, seed_path=args.seed_path)
        log.info("award voting sync complete: %s", result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
