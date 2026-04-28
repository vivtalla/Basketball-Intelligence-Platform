"""Comprehensive 2025-26 playoff stat backfill.

Pulls every playoff stat table the platform needs to drive the MVP composite,
the Regular/Playoffs leaderboard toggle, the postseason heatmap, and the
opponent lineup matchup matrix:

  1. SeasonStat (is_playoff=True) via sync_official_season_stats
  2. TeamSplitStat / TeamShootingSplitStat (is_playoff=True)
  3. GameLog (season_type=Playoffs) via the seed_playoff_games script
  4. PlayerGameLog (season_type=Playoffs) via box scores for each playoff game
  5. PlayerPlayTypeStat (season_type=Playoffs) via Synergy
  6. PlayerHustleStat (season_type=Playoffs) via league-hustle endpoint
  7. PlayerTrackingStat (season_type=Playoffs) per-player tracking dashboards

Idempotent — safe to re-run. Skips PlayerGameLog rows that already exist for
(player_id, game_id, season_type=Playoffs).

Run with:
    cd backend && PYTHONPATH=. ./venv/bin/python scripts/sync_playoff_full.py [SEASON]

Defaults to season=2025-26.
"""
from __future__ import annotations

import sys
import time
from typing import List, Optional, Set

from sqlalchemy.orm import Session

from db.database import SessionLocal
from db.models import GameLog, PlayerGameLog, Player, SeasonStat, Team
from data.nba_client import get_game_box_score_detailed
from services.sync_service import (
    sync_official_season_stats,
    sync_official_team_general_splits,
    sync_official_team_shooting_splits,
)
from services.gravity_sync_service import (
    sync_player_play_type_stats,
    sync_player_hustle_stats,
    sync_player_tracking_stats,
)
from services.playoff_bracket_service import build_or_refresh_bracket
from scripts.seed_playoff_games import seed_playoff_games


def _persist_player_game_log_from_box(
    db: Session,
    *,
    player_id: int,
    game_id: str,
    season: str,
    box_player: dict,
    home_tid: Optional[int],
    home_won: Optional[bool],
    matchup_home: Optional[str],
    matchup_away: Optional[str],
    game_date,
) -> bool:
    """Insert a PlayerGameLog row if missing. Returns True if inserted."""
    existing = (
        db.query(PlayerGameLog)
        .filter_by(player_id=player_id, game_id=game_id, season_type="Playoffs")
        .first()
    )
    if existing is not None:
        return False

    # Ensure the player exists; if not, skip rather than create stub rows.
    player = db.query(Player).filter_by(id=player_id).first()
    if player is None:
        return False

    is_home = box_player.get("team_id") == home_tid
    matchup = matchup_home if is_home else matchup_away
    if home_won is None:
        wl = None
    else:
        won = home_won if is_home else not home_won
        wl = "W" if won else "L"

    fga = box_player.get("fga") or 0
    fg3a = box_player.get("fg3a") or 0
    fta = box_player.get("fta") or 0

    db.add(PlayerGameLog(
        player_id=player_id,
        game_id=game_id,
        season=season,
        season_type="Playoffs",
        game_date=game_date,
        matchup=matchup,
        wl=wl,
        min=box_player.get("min"),
        pts=box_player.get("pts"),
        reb=box_player.get("reb"),
        ast=box_player.get("ast"),
        stl=box_player.get("stl"),
        blk=box_player.get("blk"),
        tov=box_player.get("tov"),
        fgm=box_player.get("fgm"),
        fga=fga,
        fg3m=box_player.get("fg3m"),
        fg3a=fg3a,
        ftm=box_player.get("ftm"),
        fta=fta,
        plus_minus=box_player.get("plus_minus"),
    ))
    return True


def sync_playoff_player_game_logs(db: Session, season: str) -> dict:
    """Pull box scores for every playoff GameLog and persist PlayerGameLog rows."""
    games = (
        db.query(GameLog)
        .filter(GameLog.season == season, GameLog.season_type == "Playoffs")
        .order_by(GameLog.game_date.asc())
        .all()
    )
    if not games:
        return {"status": "ok", "games": 0, "logs_inserted": 0, "logs_skipped": 0}

    logs_inserted = 0
    logs_skipped = 0
    games_failed: List[str] = []

    for g in games:
        try:
            box = get_game_box_score_detailed(g.game_id)
        except Exception as exc:
            print(f"  box score failed for {g.game_id}: {exc}")
            games_failed.append(g.game_id)
            continue
        if not box or not box.get("players"):
            continue

        home_tid = box.get("home_team_id")
        home_won = box.get("home_won")
        # get_game_box_score_detailed always includes matchup strings.
        matchup_home = box.get("matchup_home")
        matchup_away = box.get("matchup_away")

        for p in box.get("players", []):
            pid = p.get("player_id")
            if not pid:
                continue
            inserted = _persist_player_game_log_from_box(
                db,
                player_id=pid,
                game_id=g.game_id,
                season=season,
                box_player=p,
                home_tid=home_tid,
                home_won=home_won,
                matchup_home=matchup_home,
                matchup_away=matchup_away,
                game_date=g.game_date,
            )
            if inserted:
                logs_inserted += 1
            else:
                logs_skipped += 1

        db.commit()

    return {
        "status": "ok",
        "games": len(games),
        "logs_inserted": logs_inserted,
        "logs_skipped": logs_skipped,
        "games_failed": games_failed,
    }


def collect_playoff_player_ids(db: Session, season: str) -> List[int]:
    """All player_ids that have a 2025-26 playoff SeasonStat row (gating set)."""
    rows = (
        db.query(SeasonStat.player_id)
        .filter(SeasonStat.season == season, SeasonStat.is_playoff == True)  # noqa: E712
        .distinct()
        .all()
    )
    return [r[0] for r in rows]


def sync_playoff_full(season: str, fast: bool = False) -> None:
    db: Session = SessionLocal()
    try:
        print(f"=== Sprint 73 playoff full sync — season {season} ===")

        # 1. SeasonStat playoff rows (idempotent)
        print("[1/7] sync_official_season_stats (Playoffs) ...")
        r = sync_official_season_stats(db, season=season, is_playoff=True)
        print(f"   {r}")

        # 2. Team splits
        print("[2/7] sync_official_team_general_splits (Playoffs) ...")
        r = sync_official_team_general_splits(db, season=season, is_playoff=True)
        print(f"   {r}")
        print("[3/7] sync_official_team_shooting_splits (Playoffs) ...")
        r = sync_official_team_shooting_splits(db, season=season, is_playoff=True)
        print(f"   {r}")

        # 3. GameLog (via seed_playoff_games script)
        print("[4/7] seed_playoff_games (GameLogs + bracket) ...")
        n_games = seed_playoff_games(season)
        print(f"   {n_games} games persisted")

        # 4. PlayerGameLog from box scores
        print("[5/7] sync_playoff_player_game_logs ...")
        r = sync_playoff_player_game_logs(db, season=season)
        print(f"   {r}")

        # 5. Synergy play-type
        print("[6/7] sync_player_play_type_stats (Playoffs) ...")
        for grouping in ("offensive", "defensive"):
            try:
                r = sync_player_play_type_stats(db, season=season, season_type="Playoffs", type_grouping=grouping)
                print(f"   {grouping}: {r}")
            except TypeError:
                # Fall back to default-grouping signature.
                r = sync_player_play_type_stats(db, season=season, season_type="Playoffs")
                print(f"   {r}")
                break
            except Exception as exc:
                print(f"   {grouping} failed: {exc}")

        # 6. Hustle
        print("[7a/7] sync_player_hustle_stats (Playoffs) ...")
        try:
            r = sync_player_hustle_stats(db, season=season, season_type="Playoffs")
            print(f"   {r}")
        except Exception as exc:
            print(f"   hustle failed: {exc}")

        # 7. Tracking — per player, expensive, only for players with a playoff
        # SeasonStat row (~220 players × 0.6s rate limit ~= 2 minutes).
        # Skipped in fast mode (post-game cron path) since tracking aggregates
        # don't change meaningfully game-to-game.
        if fast:
            print("[7b/7] sync_player_tracking_stats SKIPPED (fast mode)")
        else:
            print("[7b/7] sync_player_tracking_stats (Playoffs) ...")
            player_ids = collect_playoff_player_ids(db, season)
            print(f"   {len(player_ids)} playoff players")
            try:
                r = sync_player_tracking_stats(db, player_ids=player_ids, season=season, season_type="Playoffs")
                print(f"   {r}")
            except Exception as exc:
                print(f"   tracking failed: {exc}")

        # 8. Refresh bracket once more in case any series advanced.
        print("[8/8] build_or_refresh_bracket ...")
        n = build_or_refresh_bracket(db, season)
        print(f"   {n} series refreshed")

        print("=== done ===")
    finally:
        db.close()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a]
    fast = "--fast" in args
    args = [a for a in args if not a.startswith("--")]
    season = args[0] if args else "2025-26"
    sync_playoff_full(season, fast=fast)
