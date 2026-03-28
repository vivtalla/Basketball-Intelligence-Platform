#!/usr/bin/env python3
"""CLI wrapper for syncing play-by-play derived stats."""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.pbp_sync_service import sync_pbp_for_player, sync_pbp_for_season


def main() -> None:
    parser = argparse.ArgumentParser(description="Import NBA play-by-play data")
    parser.add_argument("--season", required=True, help="Season in YYYY-YY format, e.g. 2024-25")
    parser.add_argument("--player-id", type=int, help="Optional player ID for a player-scoped sync")
    parser.add_argument("--force-refresh", action="store_true", help="Re-fetch raw play-by-play for matching games")
    args = parser.parse_args()

    if args.player_id:
        summary = sync_pbp_for_player(args.player_id, args.season, force_refresh=args.force_refresh)
    else:
        summary = sync_pbp_for_season(args.season, force_refresh=args.force_refresh)

    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
