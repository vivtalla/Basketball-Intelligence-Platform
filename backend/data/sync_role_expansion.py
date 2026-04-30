#!/usr/bin/env python3
"""Sprint 79 Stream A2 — nightly materialization of role_expansion_observations.

Wired into ``daily_sync.sh`` after ``season_stats`` materialization completes.
Idempotent: per-pair upsert on ``(player_id, from_season, to_season)``.

Usage:
    python data/sync_role_expansion.py
    python data/sync_role_expansion.py --min-usg-delta 0.04   # tighter threshold
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.role_expansion_materialization_service import (
    MIN_GP,
    MIN_USG_DELTA,
    materialize_role_expansion,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("sync_role_expansion")


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize role_expansion_observations")
    parser.add_argument(
        "--min-usg-delta",
        type=float,
        default=MIN_USG_DELTA,
        help="Minimum usage growth (default: 0.03)",
    )
    parser.add_argument(
        "--min-gp",
        type=int,
        default=MIN_GP,
        help="Minimum GP for both pre and post seasons (default: 40)",
    )
    args = parser.parse_args()

    summary = materialize_role_expansion(
        min_usg_delta=args.min_usg_delta,
        min_gp=args.min_gp,
    )
    log.info("sync_role_expansion complete: %s", summary)


if __name__ == "__main__":
    main()
