"""Bulk sync service: pre-populate PostgreSQL with full-season data in minimal API calls.

Uses the NBA CDN (cdn.nba.com) instead of stats.nba.com to avoid IP blocks and timeouts.
Iterates all games in a season, extracts per-player stats from box scores, and aggregates
into season totals. Also delegates to pbp_sync_service for play-by-play derived metrics.
"""

from __future__ import annotations

import logging
import re
import time
from collections import defaultdict
from datetime import date as date_type
from datetime import datetime
from typing import Callable, Optional

from sqlalchemy.orm import Session

from data.nba_client import (
    get_game_box_score_detailed,
    get_season_game_ids,
    get_shot_chart_data,
    _cache_ttl_for_season,
)
from db.database import SessionLocal
from db.models import Player, PlayerGameLog, PlayerShotChart, SeasonStat, SyncStatus, Team
from services.advanced_metrics import enrich_season_with_advanced
from services.pbp_sync_service import sync_pbp_for_season
from services.player_identity_service import sync_player_aliases

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _retry(fn, *args, **kwargs):
    """Retry a function up to MAX_RETRIES times with exponential backoff."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception:
            if attempt == MAX_RETRIES:
                raise
            logger.warning(f"Attempt {attempt}/{MAX_RETRIES} failed, retrying in {attempt * 3}s...")
            time.sleep(attempt * 3)


def _get_or_update_sync_status(
    db: Session, sync_type: str, season: str
) -> SyncStatus:
    row = db.query(SyncStatus).filter_by(sync_type=sync_type, season=season).first()
    if not row:
        row = SyncStatus(sync_type=sync_type, season=season, status="pending")
        db.add(row)
        db.flush()
    return row


def _mark_running(db: Session, sync_type: str, season: str, total: int | None = None) -> SyncStatus:
    row = _get_or_update_sync_status(db, sync_type, season)
    row.status = "running"
    row.started_at = datetime.utcnow()
    row.records_synced = 0
    row.total_records = total
    row.error_message = None
    db.commit()
    return row


def _mark_complete(db: Session, row: SyncStatus, count: int) -> None:
    row.status = "complete"
    row.records_synced = count
    row.completed_at = datetime.utcnow()
    db.commit()


def _mark_failed(db: Session, row: SyncStatus, error: str) -> None:
    row.status = "failed"
    row.error_message = error[:500]
    row.completed_at = datetime.utcnow()
    db.commit()


# Stat fields to accumulate across games
_ACCUMULATE_FIELDS = [
    "pts", "reb", "ast", "stl", "blk", "tov",
    "fgm", "fga", "fg3m", "fg3a", "ftm", "fta",
    "oreb", "dreb", "pf",
]


def sync_all_players(
    season: str,
    progress_callback: Callable[[str], None] | None = None,
) -> dict:
    """Sync all players and season stats by aggregating CDN box scores.

    Iterates all completed games in the season, fetches detailed box scores
    from the CDN, and aggregates per-player stats into season totals.
    No stats.nba.com calls needed — only CDN.
    """
    db = SessionLocal()
    try:
        # Get all game IDs for the season
        if progress_callback:
            progress_callback("Fetching season schedule from CDN...")
        game_ids = _retry(get_season_game_ids, season)
        total_games = len(game_ids)

        if not game_ids:
            if progress_callback:
                progress_callback(f"No games found for season {season}")
            return {"status": "skipped", "reason": "no games found"}

        status = _mark_running(db, "players", season, total=total_games)
        db.commit()

        if progress_callback:
            progress_callback(f"Processing {total_games} games from CDN box scores...")

        # Accumulate per-player stats across all games
        player_accum: dict[int, dict] = defaultdict(lambda: {
            "gp": 0, "gs": 0, "min_total": 0.0,
            **{f: 0 for f in _ACCUMULATE_FIELDS},
            "team_id": None, "team_abbreviation": "", "player_name": "",
        })
        teams_seen: dict[int, dict] = {}
        games_processed = 0
        games_failed = 0

        for i, game_id in enumerate(game_ids):
            try:
                box = _retry(get_game_box_score_detailed, game_id, timeout=30)

                # Track teams
                for side in ["home", "away"]:
                    tid = box.get(f"{side}_team_id")
                    if tid and tid not in teams_seen:
                        teams_seen[tid] = {
                            "abbreviation": box.get(f"{side}_team_abbreviation", ""),
                            "name": box.get(f"{side}_team_name", ""),
                        }

                # Accumulate per-player stats
                home_tid = box.get("home_team_id")
                for p in box.get("players", []):
                    pid = p.get("player_id")
                    if not pid:
                        continue

                    acc = player_accum[pid]
                    acc["player_name"] = p.get("player_name", "") or acc["player_name"]
                    acc["team_id"] = p.get("team_id") or acc["team_id"]
                    acc["team_abbreviation"] = p.get("team_abbreviation", "") or acc["team_abbreviation"]

                    if p.get("min", 0) > 0:
                        acc["gp"] += 1
                    if p.get("start_position"):
                        acc["gs"] += 1
                    acc["min_total"] += p.get("min", 0)

                    for f in _ACCUMULATE_FIELDS:
                        acc[f] += p.get(f, 0) or 0

                games_processed += 1

                if (i + 1) % 50 == 0:
                    status.records_synced = games_processed
                    db.commit()
                    if progress_callback:
                        progress_callback(f"  Games: {i + 1}/{total_games} ({len(player_accum)} players found)")

            except Exception as e:
                games_failed += 1
                logger.warning(f"Failed box score for game {game_id}: {e}")
                continue

        if progress_callback:
            progress_callback(f"Upserting {len(player_accum)} players into database...")

        # Upsert teams
        for team_id, info in teams_seen.items():
            team = db.query(Team).filter_by(id=team_id).first()
            if not team:
                team = Team(id=team_id, abbreviation=info["abbreviation"], name=info["name"])
                db.add(team)
            else:
                if info["abbreviation"]:
                    team.abbreviation = info["abbreviation"]
                if info["name"]:
                    team.name = info["name"]
        db.flush()

        # Upsert players and season stats
        players_synced = 0
        for player_id, acc in player_accum.items():
            gp = acc["gp"] or 1

            # Upsert player
            player = db.query(Player).filter_by(id=player_id).first()
            if not player:
                player = Player(
                    id=player_id,
                    full_name=acc["player_name"],
                    team_id=acc["team_id"],
                    is_active=True,
                )
                db.add(player)
            else:
                if acc["player_name"]:
                    player.full_name = acc["player_name"]
                if acc["team_id"]:
                    player.team_id = acc["team_id"]
                player.is_active = True
            db.flush()
            sync_player_aliases(db, player, source="bulk_sync")

            # Build season data
            season_data = {
                "season": season,
                "team_abbreviation": acc["team_abbreviation"],
                "gp": acc["gp"],
                "gs": acc["gs"],
                "min_total": acc["min_total"],
                "min_pg": round(acc["min_total"] / gp, 1),
                "pts": acc["pts"], "pts_pg": round(acc["pts"] / gp, 1),
                "reb": acc["reb"], "reb_pg": round(acc["reb"] / gp, 1),
                "ast": acc["ast"], "ast_pg": round(acc["ast"] / gp, 1),
                "stl": acc["stl"], "stl_pg": round(acc["stl"] / gp, 1),
                "blk": acc["blk"], "blk_pg": round(acc["blk"] / gp, 1),
                "tov": acc["tov"], "tov_pg": round(acc["tov"] / gp, 1),
                "fgm": acc["fgm"], "fga": acc["fga"],
                "fg_pct": round(acc["fgm"] / acc["fga"], 3) if acc["fga"] > 0 else 0,
                "fg3m": acc["fg3m"], "fg3a": acc["fg3a"],
                "fg3_pct": round(acc["fg3m"] / acc["fg3a"], 3) if acc["fg3a"] > 0 else 0,
                "ftm": acc["ftm"], "fta": acc["fta"],
                "ft_pct": round(acc["ftm"] / acc["fta"], 3) if acc["fta"] > 0 else 0,
                "oreb": acc["oreb"], "dreb": acc["dreb"],
                "pf": acc["pf"],
            }

            # Enrich with calculated advanced metrics (no NBA API data needed)
            season_data = enrich_season_with_advanced(season_data, None)

            # Upsert season stat
            stat = db.query(SeasonStat).filter_by(
                player_id=player_id,
                season=season,
                team_abbreviation=acc["team_abbreviation"],
                is_playoff=False,
            ).first()

            if not stat:
                stat = SeasonStat(
                    player_id=player_id,
                    season=season,
                    team_abbreviation=acc["team_abbreviation"],
                    is_playoff=False,
                )
                db.add(stat)

            for key in [
                "gp", "gs", "min_total", "min_pg", "pts", "pts_pg", "reb", "reb_pg",
                "ast", "ast_pg", "stl", "stl_pg", "blk", "blk_pg", "tov", "tov_pg",
                "fgm", "fga", "fg_pct", "fg3m", "fg3a", "fg3_pct", "ftm", "fta", "ft_pct",
                "oreb", "dreb", "pf", "ts_pct", "efg_pct", "per", "bpm",
                "ws", "vorp", "darko", "obpm", "dbpm", "ftr", "par3", "ast_tov", "oreb_pct",
            ]:
                if key in season_data:
                    setattr(stat, key, season_data[key])

            players_synced += 1

            if players_synced % 100 == 0:
                db.commit()

        db.commit()
        _mark_complete(db, status, players_synced)

        if progress_callback:
            progress_callback(
                f"Players sync complete: {players_synced} players, "
                f"{len(teams_seen)} teams, {games_processed} games processed"
            )

        return {
            "status": "ok",
            "sync_type": "players",
            "season": season,
            "players_synced": players_synced,
            "teams_synced": len(teams_seen),
            "games_processed": games_processed,
            "games_failed": games_failed,
        }

    except Exception as e:
        status = _get_or_update_sync_status(db, "players", season)
        _mark_failed(db, status, str(e))
        raise
    finally:
        db.close()


def sync_all_game_logs(
    season: str,
    progress_callback: Callable[[str], None] | None = None,
) -> dict:
    """Sync per-game player stats for all games in a season from CDN box scores.

    Iterates all games and inserts PlayerGameLog rows from CDN data.
    No stats.nba.com calls needed.
    """
    db = SessionLocal()
    try:
        if progress_callback:
            progress_callback("Fetching season schedule from CDN...")
        game_ids = _retry(get_season_game_ids, season)

        if not game_ids:
            if progress_callback:
                progress_callback(f"No games found for season {season}")
            return {"status": "skipped", "reason": "no games found"}

        status = _mark_running(db, "game_logs", season, total=len(game_ids))
        db.commit()

        if progress_callback:
            progress_callback(f"Syncing game logs for {len(game_ids)} games...")

        games_done = 0
        total_logs = 0

        for i, game_id in enumerate(game_ids):
            try:
                box = _retry(get_game_box_score_detailed, game_id, timeout=30)
                home_tid = box.get("home_team_id")

                game_date = None
                if box.get("game_date"):
                    try:
                        game_date = date_type.fromisoformat(box["game_date"][:10])
                    except (ValueError, IndexError):
                        pass

                for p in box.get("players", []):
                    pid = p.get("player_id")
                    if not pid:
                        continue

                    existing = db.query(PlayerGameLog).filter_by(
                        player_id=pid,
                        game_id=game_id,
                        season_type="Regular Season",
                    ).first()
                    if existing:
                        continue

                    # Ensure player exists
                    player = db.query(Player).filter_by(id=pid).first()
                    if not player:
                        player = Player(
                            id=pid,
                            full_name=p.get("player_name", ""),
                            team_id=p.get("team_id"),
                            is_active=True,
                        )
                        db.add(player)
                    else:
                        if p.get("player_name"):
                            player.full_name = p.get("player_name")
                        if p.get("team_id"):
                            player.team_id = p.get("team_id")
                        player.is_active = True
                    db.flush()
                    sync_player_aliases(db, player, source="bulk_sync")

                    is_home = p.get("team_id") == home_tid
                    matchup = box.get("matchup_home") if is_home else box.get("matchup_away")
                    won = box.get("home_won") if is_home else not box.get("home_won")

                    fga = p.get("fga", 0) or 0
                    fg3a = p.get("fg3a", 0) or 0
                    fta = p.get("fta", 0) or 0

                    db.add(PlayerGameLog(
                        player_id=pid,
                        game_id=game_id,
                        season=season,
                        season_type="Regular Season",
                        game_date=game_date,
                        matchup=matchup,
                        wl="W" if won else "L",
                        min=p.get("min"),
                        pts=p.get("pts"),
                        reb=p.get("reb"),
                        ast=p.get("ast"),
                        stl=p.get("stl"),
                        blk=p.get("blk"),
                        tov=p.get("tov"),
                        fgm=p.get("fgm"),
                        fga=fga,
                        fg_pct=round(p["fgm"] / fga, 3) if fga > 0 else None,
                        fg3m=p.get("fg3m"),
                        fg3a=fg3a,
                        fg3_pct=round(p["fg3m"] / fg3a, 3) if fg3a > 0 else None,
                        ftm=p.get("ftm"),
                        fta=fta,
                        ft_pct=round(p["ftm"] / fta, 3) if fta > 0 else None,
                        oreb=p.get("oreb"),
                        dreb=p.get("dreb"),
                        pf=p.get("pf"),
                        plus_minus=int(p.get("plus_minus", 0)),
                    ))
                    total_logs += 1

                games_done += 1

                if (i + 1) % 50 == 0:
                    db.commit()
                    status.records_synced = games_done
                    db.commit()
                    if progress_callback:
                        progress_callback(f"  Game logs: {i + 1}/{len(game_ids)} games ({total_logs} logs)")

            except Exception as e:
                logger.warning(f"Failed game logs for game {game_id}: {e}")
                continue

        db.commit()
        _mark_complete(db, status, total_logs)

        if progress_callback:
            progress_callback(f"Game logs sync complete: {games_done} games, {total_logs} player-game logs")

        return {
            "status": "ok",
            "sync_type": "game_logs",
            "season": season,
            "games_processed": games_done,
            "game_logs_synced": total_logs,
        }

    except Exception as e:
        status = _get_or_update_sync_status(db, "game_logs", season)
        _mark_failed(db, status, str(e))
        raise
    finally:
        db.close()


def sync_all_pbp(
    season: str,
    force: bool = False,
    progress_callback: Callable[[str], None] | None = None,
) -> dict:
    """Sync play-by-play data for all games in a season.

    Delegates to the existing sync_pbp_for_season which handles:
    - Fetching all game IDs
    - Fetching box scores and PBP events per game (via CDN)
    - Building stints, computing on/off, clutch, lineup stats
    - Persisting everything to PostgreSQL
    """
    db = SessionLocal()
    try:
        game_ids = get_season_game_ids(season)
        total_games = len(game_ids)

        status = _mark_running(db, "pbp", season, total=total_games)
        db.commit()
    finally:
        db.close()

    if progress_callback:
        progress_callback(f"Starting PBP sync for {total_games} games (this will take a while)...")
        progress_callback(f"Rate limit: ~1s per game = ~{total_games // 60} minutes estimated")

    try:
        result = sync_pbp_for_season(season, force_refresh=force)

        db = SessionLocal()
        try:
            status = _get_or_update_sync_status(db, "pbp", season)
            _mark_complete(db, status, result.get("games_processed", 0))
        finally:
            db.close()

        if progress_callback:
            progress_callback(
                f"PBP sync complete: {result.get('games_processed', 0)} games processed, "
                f"{result.get('players_updated', 0)} players updated, "
                f"{result.get('lineups_updated', 0)} lineups"
            )

        return {**result, "sync_type": "pbp"}

    except Exception as e:
        db = SessionLocal()
        try:
            status = _get_or_update_sync_status(db, "pbp", season)
            _mark_failed(db, status, str(e))
        finally:
            db.close()
        raise


def sync_shot_charts_for_season(
    season: str,
    season_type: str = "Regular Season",
    force: bool = False,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> dict:
    """Bulk-populate player_shot_charts for all active players in a season.

    Fetches from stats.nba.com via get_shot_chart_data() and persists to DB.
    Skips players who already have a valid (non-expired, shot_count > 0) row
    unless force=True. Rate-limited to 0.6s between calls.

    Returns: {"synced": N, "skipped": N, "failed": N}
    """
    db = SessionLocal()
    try:
        # Get active players who have game log data for this season
        player_ids = [
            row[0] for row in
            db.query(PlayerGameLog.player_id)
            .filter(
                PlayerGameLog.season == season,
                PlayerGameLog.season_type == season_type,
            )
            .distinct()
            .all()
        ]

        total = len(player_ids)
        if progress_callback:
            progress_callback(f"Found {total} players with {season_type} game logs for {season}")

        status_row = _mark_running(db, "shot_charts", season, total=total)

        synced = 0
        skipped = 0
        failed = 0
        now = datetime.utcnow()

        for i, player_id in enumerate(player_ids, start=1):
            if progress_callback and i % 20 == 0:
                progress_callback(f"  {i}/{total} — synced={synced} skipped={skipped} failed={failed}")

            # Check existing cache row
            if not force:
                existing = (
                    db.query(PlayerShotChart)
                    .filter(
                        PlayerShotChart.player_id == player_id,
                        PlayerShotChart.season == season,
                        PlayerShotChart.season_type == season_type,
                    )
                    .first()
                )
                if existing and existing.shot_count and existing.shot_count > 0:
                    if existing.expires_at and existing.expires_at > now:
                        skipped += 1
                        continue

            # Fetch from stats.nba.com
            try:
                raw_shots = get_shot_chart_data(player_id, season, season_type)
            except Exception as exc:
                logger.warning(f"Shot chart fetch failed for player {player_id}: {exc}")
                failed += 1
                continue

            # Persist to DB
            ttl_seconds = _cache_ttl_for_season(season)
            from datetime import timedelta
            expires_at = now + timedelta(seconds=ttl_seconds)

            try:
                existing = (
                    db.query(PlayerShotChart)
                    .filter(
                        PlayerShotChart.player_id == player_id,
                        PlayerShotChart.season == season,
                        PlayerShotChart.season_type == season_type,
                    )
                    .first()
                )
                if existing:
                    existing.shots = raw_shots
                    existing.shot_count = len(raw_shots)
                    existing.fetched_at = now
                    existing.expires_at = expires_at
                else:
                    db.add(PlayerShotChart(
                        player_id=player_id,
                        season=season,
                        season_type=season_type,
                        shots=raw_shots,
                        shot_count=len(raw_shots),
                        fetched_at=now,
                        expires_at=expires_at,
                    ))
                db.commit()
                synced += 1
            except Exception as exc:
                db.rollback()
                logger.warning(f"Failed to persist shot chart for player {player_id}: {exc}")
                failed += 1

        _mark_complete(db, status_row, synced)
        summary = {"synced": synced, "skipped": skipped, "failed": failed, "total": total}
        logger.info(f"sync_shot_charts_for_season complete: {summary}")
        if progress_callback:
            progress_callback(f"Done — synced={synced} skipped={skipped} failed={failed}")
        return summary

    except Exception as exc:
        _mark_failed(db, status_row, str(exc))
        raise
    finally:
        db.close()


def get_sync_status(season: str) -> list[dict]:
    """Return sync status for all sync types for a given season."""
    db = SessionLocal()
    try:
        rows = db.query(SyncStatus).filter_by(season=season).all()
        return [
            {
                "sync_type": row.sync_type,
                "season": row.season,
                "status": row.status,
                "records_synced": row.records_synced,
                "total_records": row.total_records,
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                "error_message": row.error_message,
            }
            for row in rows
        ]
    finally:
        db.close()
