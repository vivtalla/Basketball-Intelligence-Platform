#!/usr/bin/env python3
"""CLI for bulk-syncing NBA season data into PostgreSQL.

Uses the NBA CDN (cdn.nba.com) to avoid stats.nba.com rate limits and IP blocks.
Iterates all games in a season, extracts player stats from box scores, and
aggregates into season totals + per-game logs + play-by-play derived metrics.

Usage:
    python data/bulk_import.py --season 2024-25                # Full sync (players + game logs + PBP)
    python data/bulk_import.py --season 2024-25 --players-only  # Players & season stats from CDN box scores
    python data/bulk_import.py --season 2024-25 --pbp-only      # PBP + on/off + clutch + lineups (~1s/game)
    python data/bulk_import.py --season 2024-25 --game-logs-only # Per-game player stats from CDN box scores
    python data/bulk_import.py --season 2024-25 --status         # Show sync progress
    python data/bulk_import.py --season 2024-25 --force          # Re-sync even if data exists
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import engine
from db.models import Base


def _print_progress(msg: str) -> None:
    print(f"  {msg}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bulk-sync NBA season data into PostgreSQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python data/bulk_import.py --season 2024-25                  # Full sync
  python data/bulk_import.py --season 2024-25 --players-only   # Fast: 2 API calls
  python data/bulk_import.py --season 2024-25 --pbp-only       # PBP + on/off + clutch + lineups
  python data/bulk_import.py --season 2024-25 --status         # Check progress
        """,
    )
    parser.add_argument("--season", required=True, help="Season in YYYY-YY format, e.g. 2024-25")
    parser.add_argument("--players-only", action="store_true", help="Sync only players & season stats")
    parser.add_argument("--game-logs-only", action="store_true", help="Sync only per-game player stats")
    parser.add_argument("--pbp-only", action="store_true", help="Sync only play-by-play + derived metrics")
    parser.add_argument("--status", action="store_true", help="Show sync status and exit")
    parser.add_argument("--force", action="store_true", help="Re-fetch data even if already synced")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    from services.bulk_sync_service import (
        get_sync_status,
        sync_all_game_logs,
        sync_all_pbp,
        sync_all_players,
    )

    season = args.season

    if args.status:
        _show_status(season, get_sync_status)
        return

    # Determine what to sync
    do_players = args.players_only or (not args.game_logs_only and not args.pbp_only)
    do_game_logs = args.game_logs_only or (not args.players_only and not args.pbp_only)
    do_pbp = args.pbp_only or (not args.players_only and not args.game_logs_only)

    print(f"\n{'='*60}")
    print(f"  CourtVue Labs — Bulk Import")
    print(f"  Season: {season}")
    print(f"  Sync: {'players ' if do_players else ''}{'game_logs ' if do_game_logs else ''}{'pbp' if do_pbp else ''}")
    print(f"{'='*60}\n")

    start = time.time()

    if do_players:
        print("[1/3] Syncing players & season stats...")
        result = sync_all_players(season, progress_callback=_print_progress)
        print(f"  Done: {result.get('players_synced', 0)} players, {result.get('teams_synced', 0)} teams\n")

    if do_game_logs:
        print("[2/3] Syncing player game logs...")
        result = sync_all_game_logs(season, progress_callback=_print_progress)
        print(f"  Done: {result.get('game_logs_synced', 0)} game logs\n")

    if do_pbp:
        print("[3/3] Syncing play-by-play data + derived metrics...")
        result = sync_all_pbp(season, force=args.force, progress_callback=_print_progress)
        print(f"  Done: {result.get('games_processed', 0)} games, {result.get('players_updated', 0)} players updated\n")

    elapsed = time.time() - start
    mins = int(elapsed // 60)
    secs = int(elapsed % 60)
    print(f"{'='*60}")
    print(f"  Bulk import complete in {mins}m {secs}s")
    print(f"{'='*60}\n")


def _show_status(season: str, get_sync_status) -> None:
    statuses = get_sync_status(season)
    if not statuses:
        print(f"\nNo sync data found for season {season}.")
        print("Run: python data/bulk_import.py --season", season)
        return

    print(f"\nSync Status for {season}:")
    print(f"{'Type':<15} {'Status':<12} {'Records':<15} {'Started':<22} {'Completed':<22}")
    print("-" * 86)
    for s in statuses:
        records = f"{s['records_synced'] or 0}"
        if s["total_records"]:
            records += f"/{s['total_records']}"
        started = s["started_at"][:19] if s["started_at"] else "-"
        completed = s["completed_at"][:19] if s["completed_at"] else "-"
        print(f"{s['sync_type']:<15} {s['status']:<12} {records:<15} {started:<22} {completed:<22}")
        if s.get("error_message"):
            print(f"  Error: {s['error_message']}")
    print()


if __name__ == "__main__":
    main()
