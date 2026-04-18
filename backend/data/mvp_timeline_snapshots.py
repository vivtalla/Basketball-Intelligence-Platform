#!/usr/bin/env python3
"""Materialize persisted MVP race timeline snapshots."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.nba_client import _active_nba_season
from db.database import SessionLocal
from services.mvp_timeline_service import materialize_mvp_timeline_snapshots


def _parse_date(raw: str | None):
    if not raw:
        return None
    return datetime.strptime(raw, "%Y-%m-%d").date()


def main() -> None:
    parser = argparse.ArgumentParser(description="Persist daily MVP race snapshots")
    parser.add_argument("--season", default=None, help="Season in YYYY-YY format, e.g. 2025-26")
    parser.add_argument("--date", default=None, help="Snapshot date in YYYY-MM-DD format")
    parser.add_argument("--top", type=int, default=15, help="Number of candidates per profile")
    parser.add_argument("--min-gp", type=int, default=20, help="Minimum games played")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        season = args.season or _active_nba_season()
        snapshot_date = _parse_date(args.date)
        snapshots = materialize_mvp_timeline_snapshots(
            db,
            season=season,
            snapshot_date=snapshot_date,
            top=args.top,
            min_gp=args.min_gp,
        )
        print(
            {
                "status": "ok",
                "season": season,
                "snapshot_date": (snapshot_date or snapshots[0].snapshot_date).isoformat() if snapshots else None,
                "profiles": [snapshot.profile for snapshot in snapshots],
                "snapshots": len(snapshots),
            }
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
