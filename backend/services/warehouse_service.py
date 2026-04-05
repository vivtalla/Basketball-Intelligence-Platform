from __future__ import annotations

import hashlib
import json
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from data.nba_client import (
    _cache_ttl_for_season,
    _active_nba_season,
    _normalize_pbp_rows,
    _parse_cdn_minutes,
    get_game_box_score_payload,
    get_play_by_play_payload,
    get_player_game_logs,
    get_schedule_payload_for_season,
    get_shot_chart_data,
)
from db.database import SessionLocal
from db.models import (
    ApiRequestState,
    GameLog,
    GamePlayerStat,
    GameTeamStat,
    IngestionJob,
    LineupStats,
    Player,
    PlayerGameLog,
    PlayerShotChart,
    PlayerOnOff,
    PlayByPlay,
    PlayByPlayEvent,
    RawGamePayload,
    RawSchedulePayload,
    SeasonStat,
    SourceRun,
    Team,
    WarehouseGame,
)
from services.advanced_metrics import enrich_season_with_advanced
from services.shot_lab_service import enrich_and_validate_player_shot_payload, summarize_shot_completeness
from services.sync_service import canonical_player_name, sync_player
from services.pbp_service import (
    build_stints,
    compute_clutch_stats,
    compute_lineup_stats,
    compute_on_off,
    compute_second_chance_and_fast_break,
    load_pbp_events_for_game,
)

logger = logging.getLogger(__name__)

JOB_STATUS_QUEUED = "queued"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_COMPLETE = "complete"
JOB_STATUS_FAILED = "failed"
JOB_STATUS_SKIPPED = "skipped"

CURRENT_SEASON_LOOKBACK_DAYS = 3
PLAYER_PROFILE_STALE_AFTER = timedelta(days=14)
PLAYER_CAREER_STALE_AFTER = timedelta(hours=24)
PLAYER_GAMELOG_STALE_AFTER = timedelta(hours=24)


def _utcnow() -> datetime:
    return datetime.utcnow()


def _serialize_dt(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _shot_chart_job_key(player_id: int, season: str, season_type: str) -> str:
    return "{0}:{1}:{2}".format(player_id, season, season_type)


def _player_profile_job_key(player_id: int) -> str:
    return "{0}".format(player_id)


def _player_career_job_key(player_id: int) -> str:
    return "{0}".format(player_id)


def _player_gamelog_job_key(player_id: int, season: str, season_type: str) -> str:
    return "{0}:{1}:{2}".format(player_id, season, season_type)


def _player_profile_status(player: Optional[Player]) -> str:
    if not player:
        return "missing"
    updated_at = getattr(player, "updated_at", None)
    if player.is_active and updated_at and (_utcnow() - updated_at) > PLAYER_PROFILE_STALE_AFTER:
        return "stale"
    return "ready"


def _season_stat_status(rows: List[SeasonStat]) -> str:
    if not rows:
        return "missing"
    latest_updated = max((row.updated_at for row in rows if row.updated_at is not None), default=None)
    latest_season = max((row.season for row in rows if row.season), default=None)
    if (
        latest_updated
        and latest_season == _active_nba_season()
        and (_utcnow() - latest_updated) > PLAYER_CAREER_STALE_AFTER
    ):
        return "stale"
    return "ready"


def _player_gamelog_status(rows: List[PlayerGameLog], season: str) -> str:
    if not rows:
        return "missing"
    if season != _active_nba_season():
        return "ready"
    latest_synced = max((row.synced_at for row in rows if row.synced_at is not None), default=None)
    if latest_synced is None or (_utcnow() - latest_synced) > PLAYER_GAMELOG_STALE_AFTER:
        return "stale"
    return "ready"


def _payload_hash(payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _parse_iso_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    value = value[:10]
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _acquire_season_advisory_lock(db: Session, season: str, purpose: str) -> None:
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
        {"lock_key": "{0}:{1}".format(purpose, season)},
    )


def _schedule_status_from_code(code: Any) -> str:
    try:
        code_int = int(code)
    except (TypeError, ValueError):
        return "scheduled"
    if code_int >= 3:
        return "final"
    if code_int == 2:
        return "live"
    return "scheduled"


def _get_or_create_team(
    db: Session,
    team_id: Optional[int],
    abbreviation: Optional[str],
    name: Optional[str],
) -> Optional[Team]:
    if not team_id:
        return None
    team = db.get(Team, team_id)
    if not team:
        for pending in db.new:
            if isinstance(pending, Team) and pending.id == team_id:
                team = pending
                break
    if not team:
        team = Team(
            id=team_id,
            abbreviation=abbreviation or f"T{team_id}",
            name=name or abbreviation or f"Team {team_id}",
        )
        db.add(team)
    else:
        if abbreviation:
            team.abbreviation = abbreviation
        if name:
            team.name = name
    return team


def _get_or_create_player(
    db: Session,
    player_id: Optional[int],
    full_name: Optional[str],
    team_id: Optional[int],
) -> Optional[Player]:
    if not player_id:
        return None
    player = db.get(Player, player_id)
    if not player:
        for pending in db.new:
            if isinstance(pending, Player) and pending.id == player_id:
                player = pending
                break
    if not player:
        player = Player(
            id=player_id,
            full_name=canonical_player_name(full_name, None, None) or "Player {0}".format(player_id),
            team_id=team_id,
            is_active=True,
        )
        db.add(player)
        db.flush()
    else:
        if full_name:
            resolved = canonical_player_name(full_name, player.first_name, player.last_name)
            if resolved and (not player.full_name or " " not in player.full_name):
                player.full_name = resolved
        if team_id:
            player.team_id = team_id
        player.is_active = True
    return player


def _start_source_run(
    db: Session,
    *,
    source: str,
    job_type: str,
    entity_type: str,
    entity_id: str,
    attempt_count: int = 1,
    run_metadata: Optional[dict] = None,
) -> SourceRun:
    row = SourceRun(
        source=source,
        job_type=job_type,
        entity_type=entity_type,
        entity_id=entity_id,
        status=JOB_STATUS_RUNNING,
        attempt_count=attempt_count,
        run_metadata=run_metadata or {},
        started_at=_utcnow(),
    )
    db.add(row)
    db.flush()
    return row


def _finish_source_run(
    db: Session,
    run: SourceRun,
    *,
    status: str,
    records_written: int = 0,
    error_message: Optional[str] = None,
    run_metadata: Optional[dict] = None,
) -> None:
    run.status = status
    run.records_written = records_written
    run.error_message = error_message[:1000] if error_message else None
    run.completed_at = _utcnow()
    if run_metadata:
        merged = dict(run.run_metadata or {})
        merged.update(run_metadata)
        run.run_metadata = merged


def _normalize_schedule_games(payload: dict, source: str, season: str, date_key: Optional[str]) -> List[dict]:
    results: List[dict] = []
    if source == "cdn_schedule":
        for game_date in payload.get("leagueSchedule", {}).get("gameDates", []):
            game_day = game_date.get("gameDate")
            if date_key and game_day != date_key:
                continue
            for game in game_date.get("games", []):
                game_id = str(game.get("gameId") or "")
                if not game_id or not game_id.startswith("002"):
                    continue
                results.append(
                    {
                        "game_id": game_id,
                        "season": season,
                        "game_date": _parse_iso_date(game.get("gameDateEst") or game_day),
                        "status": _schedule_status_from_code(game.get("gameStatus")),
                        "home_team_id": game.get("homeTeam", {}).get("teamId"),
                        "away_team_id": game.get("awayTeam", {}).get("teamId"),
                        "home_team_abbreviation": game.get("homeTeam", {}).get("teamTricode"),
                        "away_team_abbreviation": game.get("awayTeam", {}).get("teamTricode"),
                        "home_team_name": game.get("homeTeam", {}).get("teamName"),
                        "away_team_name": game.get("awayTeam", {}).get("teamName"),
                        "home_score": int(game.get("homeTeam", {}).get("score") or 0),
                        "away_score": int(game.get("awayTeam", {}).get("score") or 0),
                    }
                )
    else:
        for month in payload.get("lscd", []):
            for game in month.get("mscd", {}).get("g", []):
                game_id = str(game.get("gid") or "")
                if not game_id or not game_id.startswith("002"):
                    continue
                game_day = game.get("gdte") or game.get("gdtutc")
                parsed_date = _parse_iso_date(game_day)
                if date_key and parsed_date and parsed_date.isoformat() != date_key:
                    continue
                home = game.get("h", {})
                away = game.get("v", {})
                results.append(
                    {
                        "game_id": game_id,
                        "season": season,
                        "game_date": parsed_date,
                        "status": "final" if game_id.startswith("002") else "scheduled",
                        "home_team_id": int(home.get("tid")) if str(home.get("tid") or "").isdigit() else None,
                        "away_team_id": int(away.get("tid")) if str(away.get("tid") or "").isdigit() else None,
                        "home_team_abbreviation": home.get("ta"),
                        "away_team_abbreviation": away.get("ta"),
                        "home_team_name": home.get("tn") or home.get("tc"),
                        "away_team_name": away.get("tn") or away.get("tc"),
                        "home_score": int(home.get("s") or 0),
                        "away_score": int(away.get("s") or 0),
                    }
                )
    return results


def _normalize_box_payload(game_id: str, payload: dict) -> dict:
    game = payload.get("game", payload)
    home_team = game.get("homeTeam", {})
    away_team = game.get("awayTeam", {})
    game_date = _parse_iso_date(game.get("gameTimeUTC"))

    players: List[dict] = []
    for team in [home_team, away_team]:
        team_id = team.get("teamId")
        team_tricode = team.get("teamTricode", "")
        for player in team.get("players", []):
            stats = player.get("statistics", {})
            minutes = _parse_cdn_minutes(stats.get("minutes", ""))
            players.append(
                {
                    "player_id": player.get("personId"),
                    "player_name": canonical_player_name(
                        player.get("name", ""),
                        player.get("firstName", ""),
                        player.get("familyName", ""),
                    ),
                    "team_id": team_id,
                    "team_abbreviation": team_tricode,
                    "start_position": player.get("position", "") if player.get("starter") == "1" else "",
                    "min": minutes,
                    "pts": int(stats.get("points") or 0),
                    "reb": int(stats.get("reboundsTotal") or 0),
                    "ast": int(stats.get("assists") or 0),
                    "stl": int(stats.get("steals") or 0),
                    "blk": int(stats.get("blocks") or 0),
                    "tov": int(stats.get("turnovers") or 0),
                    "fgm": int(stats.get("fieldGoalsMade") or 0),
                    "fga": int(stats.get("fieldGoalsAttempted") or 0),
                    "fg3m": int(stats.get("threePointersMade") or 0),
                    "fg3a": int(stats.get("threePointersAttempted") or 0),
                    "ftm": int(stats.get("freeThrowsMade") or 0),
                    "fta": int(stats.get("freeThrowsAttempted") or 0),
                    "oreb": int(stats.get("reboundsOffensive") or 0),
                    "dreb": int(stats.get("reboundsDefensive") or 0),
                    "pf": int(stats.get("foulsPersonal") or 0),
                    "plus_minus": float(stats.get("plusMinusPoints") or 0),
                }
            )

    return {
        "game_id": game_id,
        "game_date": game_date,
        "status": "final" if str(game.get("gameStatus") or "") in {"2", "3"} else "scheduled",
        "home_team_id": home_team.get("teamId"),
        "away_team_id": away_team.get("teamId"),
        "home_team_abbreviation": home_team.get("teamTricode"),
        "away_team_abbreviation": away_team.get("teamTricode"),
        "home_team_name": home_team.get("teamName"),
        "away_team_name": away_team.get("teamName"),
        "home_score": int(home_team.get("score") or 0),
        "away_score": int(away_team.get("score") or 0),
        "players": players,
    }


def _normalize_team_totals(game: dict) -> List[dict]:
    grouped: Dict[int, dict] = {}
    home_team_id = game.get("home_team_id")
    away_team_id = game.get("away_team_id")
    for player in game.get("players", []):
        team_id = player.get("team_id")
        if not team_id:
            continue
        row = grouped.setdefault(
            team_id,
            {
                "team_id": team_id,
                "team_abbreviation": player.get("team_abbreviation"),
                "is_home": team_id == home_team_id,
                "won": None,
                "minutes": 0.0,
                "pts": 0,
                "reb": 0,
                "ast": 0,
                "stl": 0,
                "blk": 0,
                "tov": 0,
                "fgm": 0,
                "fga": 0,
                "fg3m": 0,
                "fg3a": 0,
                "ftm": 0,
                "fta": 0,
                "oreb": 0,
                "dreb": 0,
                "pf": 0,
                "plus_minus": 0.0,
            },
        )
        for field in ["pts", "reb", "ast", "stl", "blk", "tov", "fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "oreb", "dreb", "pf"]:
            row[field] += int(player.get(field) or 0)
        row["minutes"] += float(player.get("min") or 0.0)
        row["plus_minus"] += float(player.get("plus_minus") or 0.0)

    home_score = game.get("home_score")
    away_score = game.get("away_score")
    for team_id, row in grouped.items():
        if team_id == home_team_id and home_score is not None and away_score is not None:
            row["won"] = home_score > away_score
        elif team_id == away_team_id and home_score is not None and away_score is not None:
            row["won"] = away_score > home_score
    return list(grouped.values())


def _upsert_warehouse_game(db: Session, game_data: dict, *, source_field: str, has_schedule: bool = False) -> WarehouseGame:
    game = db.query(WarehouseGame).filter_by(game_id=game_data["game_id"]).first()
    if not game:
        game = WarehouseGame(game_id=game_data["game_id"], season=game_data["season"])
        db.add(game)

    for field in [
        "season",
        "game_date",
        "status",
        "home_team_id",
        "away_team_id",
        "home_team_abbreviation",
        "away_team_abbreviation",
        "home_team_name",
        "away_team_name",
        "home_score",
        "away_score",
    ]:
        if field in game_data:
            setattr(game, field, game_data[field])

    setattr(game, source_field, game_data.get("source"))
    game.source = game.source or game_data.get("source")
    if has_schedule:
        game.has_schedule = True
        game.last_schedule_sync_at = _utcnow()
    return game


def _store_schedule_payload(db: Session, season: str, date_key: str, source: str, payload: dict) -> RawSchedulePayload:
    content_hash = _payload_hash(payload)
    row = (
        db.query(RawSchedulePayload)
        .filter_by(source=source, season=season, date_key=date_key, content_hash=content_hash)
        .first()
    )
    if row:
        return row
    row = RawSchedulePayload(
        source=source,
        season=season,
        date_key=date_key,
        content_hash=content_hash,
        payload=payload,
    )
    db.add(row)
    db.flush()
    return row


def _store_raw_game_payload(db: Session, game_id: str, season: str, source: str, payload_type: str, payload: dict) -> RawGamePayload:
    content_hash = _payload_hash(payload)
    row = (
        db.query(RawGamePayload)
        .filter_by(game_id=game_id, source=source, payload_type=payload_type, content_hash=content_hash)
        .first()
    )
    if row:
        return row
    row = RawGamePayload(
        game_id=game_id,
        season=season,
        source=source,
        payload_type=payload_type,
        content_hash=content_hash,
        payload=payload,
    )
    try:
        with db.begin_nested():
            db.add(row)
            db.flush()
        return row
    except IntegrityError:
        existing = (
            db.query(RawGamePayload)
            .filter_by(game_id=game_id, source=source, payload_type=payload_type, content_hash=content_hash)
            .first()
        )
        if existing:
            return existing
        raise


def sync_schedule(db: Session, season: str, date_key: Optional[str] = None) -> dict:
    response = get_schedule_payload_for_season(season)
    source = response["source"]
    payload = response["payload"]
    run = _start_source_run(
        db,
        source=source,
        job_type="sync_schedule",
        entity_type="season",
        entity_id=date_key or season,
        run_metadata={"season": season, "date_key": date_key},
    )
    try:
        _store_schedule_payload(db, season, date_key or "season", source, payload)
        games = _normalize_schedule_games(payload, source, season, date_key)
        written = 0
        for game_data in games:
            _get_or_create_team(db, game_data.get("home_team_id"), game_data.get("home_team_abbreviation"), game_data.get("home_team_name"))
            _get_or_create_team(db, game_data.get("away_team_id"), game_data.get("away_team_abbreviation"), game_data.get("away_team_name"))
            game_data["source"] = source
            _upsert_warehouse_game(db, game_data, source_field="schedule_source", has_schedule=True)
            written += 1
        _finish_source_run(db, run, status=JOB_STATUS_COMPLETE, records_written=written)
        db.commit()
        return {"status": "ok", "season": season, "date_key": date_key, "games_written": written, "source": source}
    except Exception as exc:
        db.rollback()
        _finish_source_run(db, run, status=JOB_STATUS_FAILED, error_message=str(exc))
        db.commit()
        raise


def sync_game_boxscore(db: Session, game_id: str) -> dict:
    payload = get_game_box_score_payload(game_id)
    normalized = _normalize_box_payload(game_id, payload)
    game = db.query(WarehouseGame).filter_by(game_id=game_id).first()
    season = game.season if game else ""
    run = _start_source_run(
        db,
        source="cdn_boxscore",
        job_type="sync_game_boxscore",
        entity_type="game",
        entity_id=game_id,
        run_metadata={"season": season},
    )
    try:
        if not season:
            season = _infer_season_from_date(normalized.get("game_date"))
            normalized["season"] = season
        else:
            normalized["season"] = season
        _store_raw_game_payload(db, game_id, season, "cdn_boxscore", "boxscore", payload)
        _get_or_create_team(db, normalized.get("home_team_id"), normalized.get("home_team_abbreviation"), normalized.get("home_team_name"))
        _get_or_create_team(db, normalized.get("away_team_id"), normalized.get("away_team_abbreviation"), normalized.get("away_team_name"))
        warehouse_game = _upsert_warehouse_game(db, normalized, source_field="box_score_source")
        warehouse_game.has_final_box_score = normalized.get("status") == "final"
        warehouse_game.last_box_score_sync_at = _utcnow()

        db.query(GameTeamStat).filter_by(game_id=game_id).delete(synchronize_session=False)
        db.query(GamePlayerStat).filter_by(game_id=game_id).delete(synchronize_session=False)

        team_rows = _normalize_team_totals(normalized)
        for row in team_rows:
            db.add(GameTeamStat(game_id=game_id, season=season, **row))

        home_abbr = normalized.get("home_team_abbreviation") or ""
        away_abbr = normalized.get("away_team_abbreviation") or ""
        game_date = normalized.get("game_date")
        for player in normalized.get("players", []):
            _get_or_create_player(db, player.get("player_id"), player.get("player_name"), player.get("team_id"))
            team_abbr = player.get("team_abbreviation") or ""
            is_home = team_abbr == home_abbr
            matchup = f"{away_abbr} @ {home_abbr}" if is_home else f"{team_abbr} @ {home_abbr}"
            won = None
            if normalized.get("home_score") is not None and normalized.get("away_score") is not None:
                won = normalized["home_score"] > normalized["away_score"] if is_home else normalized["away_score"] > normalized["home_score"]
            db.add(
                GamePlayerStat(
                    game_id=game_id,
                    season=season,
                    player_id=player.get("player_id"),
                    team_id=player.get("team_id"),
                    team_abbreviation=team_abbr,
                    game_date=game_date,
                    matchup=matchup,
                    wl="W" if won else "L" if won is not None else None,
                    min=player.get("min"),
                    pts=player.get("pts"),
                    reb=player.get("reb"),
                    ast=player.get("ast"),
                    stl=player.get("stl"),
                    blk=player.get("blk"),
                    tov=player.get("tov"),
                    fgm=player.get("fgm"),
                    fga=player.get("fga"),
                    fg_pct=round(player["fgm"] / player["fga"], 3) if player.get("fga") else 0,
                    fg3m=player.get("fg3m"),
                    fg3a=player.get("fg3a"),
                    fg3_pct=round(player["fg3m"] / player["fg3a"], 3) if player.get("fg3a") else 0,
                    ftm=player.get("ftm"),
                    fta=player.get("fta"),
                    ft_pct=round(player["ftm"] / player["fta"], 3) if player.get("fta") else 0,
                    oreb=player.get("oreb"),
                    dreb=player.get("dreb"),
                    pf=player.get("pf"),
                    plus_minus=player.get("plus_minus"),
                    is_starter=bool(player.get("start_position")),
                )
            )
        warehouse_game.has_materialized_game_stats = True
        warehouse_game.last_materialized_at = _utcnow()
        _finish_source_run(
            db,
            run,
            status=JOB_STATUS_COMPLETE,
            records_written=len(team_rows) + len(normalized.get("players", [])),
        )
        db.commit()
        materialize_game_stats(db, game_id)
        return {
            "status": "ok",
            "game_id": game_id,
            "season": season,
            "players_written": len(normalized.get("players", [])),
            "teams_written": len(team_rows),
        }
    except Exception as exc:
        db.rollback()
        _finish_source_run(db, run, status=JOB_STATUS_FAILED, error_message=str(exc))
        db.commit()
        raise


def sync_game_pbp(db: Session, game_id: str) -> dict:
    game = db.query(WarehouseGame).filter_by(game_id=game_id).first()
    season = game.season if game else ""
    payload = get_play_by_play_payload(game_id)
    raw_events = payload.get("game", {}).get("actions") or payload.get("actions") or []
    normalized_events = _normalize_pbp_rows(raw_events)
    run = _start_source_run(
        db,
        source="cdn_pbp",
        job_type="sync_game_pbp",
        entity_type="game",
        entity_id=game_id,
        run_metadata={"season": season},
    )
    try:
        if not season:
            season = _infer_season_from_date(game.game_date if game else None)
        _store_raw_game_payload(db, game_id, season, "cdn_pbp", "pbp", payload)
        warehouse_game = db.query(WarehouseGame).filter_by(game_id=game_id).first()
        if not warehouse_game:
            warehouse_game = WarehouseGame(game_id=game_id, season=season)
            db.add(warehouse_game)
        warehouse_game.has_pbp_payload = True
        warehouse_game.pbp_source = "cdn_pbp"
        warehouse_game.last_pbp_sync_at = _utcnow()

        db.query(PlayByPlay).filter_by(game_id=game_id).delete(synchronize_session=False)
        db.query(PlayByPlayEvent).filter_by(game_id=game_id).delete(synchronize_session=False)

        for idx, event in enumerate(normalized_events, start=1):
            source_event_id = str(event.get("actionId") or event.get("actionNumber") or idx)
            action_number = event.get("actionId") or event.get("actionNumber") or idx
            action_type = (event.get("actionType") or "")[:50]
            sub_type = (event.get("subType") or "")[:50]
            action_family = _event_family(action_type)
            _get_or_create_player(db, event.get("personId"), event.get("playerName"), event.get("teamId"))
            db.add(
                PlayByPlayEvent(
                    game_id=game_id,
                    season=season,
                    source_event_id=source_event_id,
                    action_number=action_number if isinstance(action_number, int) else idx,
                    order_index=idx,
                    period=event.get("period"),
                    clock=event.get("clock"),
                    team_id=event.get("teamId"),
                    player_id=event.get("personId"),
                    action_type=action_type,
                    action_family=action_family,
                    sub_type=sub_type,
                    description=(event.get("description") or "")[:500],
                    score_home=_to_int(event.get("scoreHome")),
                    score_away=_to_int(event.get("scoreAway")),
                    raw_event=event,
                )
            )
            db.add(
                PlayByPlay(
                    game_id=game_id,
                    action_number=action_number if isinstance(action_number, int) else idx,
                    period=event.get("period"),
                    clock=event.get("clock"),
                    team_id=event.get("teamId"),
                    player_id=event.get("personId"),
                    action_type=action_type,
                    sub_type=sub_type,
                    description=(event.get("description") or "")[:500],
                    score_home=_to_int(event.get("scoreHome")),
                    score_away=_to_int(event.get("scoreAway")),
                )
            )

        warehouse_game.has_parsed_pbp = len(normalized_events) > 0
        warehouse_game.pbp_parse_status = "complete" if normalized_events else "empty"
        _finish_source_run(db, run, status=JOB_STATUS_COMPLETE, records_written=len(normalized_events))
        db.commit()
        rematerialize_pbp_derived_metrics(db, game_id)
        return {"status": "ok", "game_id": game_id, "events_written": len(normalized_events)}
    except Exception as exc:
        db.rollback()
        warehouse_game = db.query(WarehouseGame).filter_by(game_id=game_id).first()
        if warehouse_game:
            warehouse_game.pbp_parse_status = "failed"
        _finish_source_run(db, run, status=JOB_STATUS_FAILED, error_message=str(exc))
        db.commit()
        raise


def materialize_game_stats(db: Session, game_id: str) -> dict:
    game = db.query(WarehouseGame).filter_by(game_id=game_id).first()
    if not game:
        return {"status": "skipped", "reason": "game not found", "game_id": game_id}

    row = db.query(GameLog).filter_by(game_id=game_id).first()
    if not row:
        row = GameLog(game_id=game_id)
        db.add(row)
    row.season = game.season
    row.game_date = game.game_date
    row.home_team_id = game.home_team_id
    row.away_team_id = game.away_team_id
    row.home_score = game.home_score
    row.away_score = game.away_score

    player_rows = db.query(GamePlayerStat).filter_by(game_id=game_id).all()
    existing_logs = {
        (existing.player_id, existing.game_id, existing.season_type): existing
        for existing in db.query(PlayerGameLog).filter_by(game_id=game_id, season_type="Regular Season").all()
    }
    for stat in player_rows:
        key = (stat.player_id, game_id, "Regular Season")
        log_row = existing_logs.get(key)
        if not log_row:
            log_row = PlayerGameLog(
                player_id=stat.player_id,
                game_id=game_id,
                season=stat.season,
                season_type="Regular Season",
            )
            db.add(log_row)
            existing_logs[key] = log_row

        log_row.season = stat.season
        log_row.game_date = stat.game_date
        log_row.matchup = stat.matchup
        log_row.wl = stat.wl
        log_row.min = stat.min
        log_row.pts = stat.pts
        log_row.reb = stat.reb
        log_row.ast = stat.ast
        log_row.stl = stat.stl
        log_row.blk = stat.blk
        log_row.tov = stat.tov
        log_row.fgm = stat.fgm
        log_row.fga = stat.fga
        log_row.fg_pct = stat.fg_pct
        log_row.fg3m = stat.fg3m
        log_row.fg3a = stat.fg3a
        log_row.fg3_pct = stat.fg3_pct
        log_row.ftm = stat.ftm
        log_row.fta = stat.fta
        log_row.ft_pct = stat.ft_pct
        log_row.oreb = stat.oreb
        log_row.dreb = stat.dreb
        log_row.pf = stat.pf
        log_row.plus_minus = int(stat.plus_minus) if stat.plus_minus is not None else None

    game.has_materialized_game_stats = True
    game.last_materialized_at = _utcnow()
    db.commit()
    return {"status": "ok", "game_id": game_id, "player_game_logs_written": len(player_rows)}


def materialize_season_aggregates(db: Session, season: str) -> dict:
    grouped_rows = (
        db.query(
            GamePlayerStat.player_id,
            GamePlayerStat.team_abbreviation,
            func.max(GamePlayerStat.team_id),
            func.count(GamePlayerStat.id),
            func.sum(GamePlayerStat.min),
            func.sum(GamePlayerStat.pts),
            func.sum(GamePlayerStat.reb),
            func.sum(GamePlayerStat.ast),
            func.sum(GamePlayerStat.stl),
            func.sum(GamePlayerStat.blk),
            func.sum(GamePlayerStat.tov),
            func.sum(GamePlayerStat.fgm),
            func.sum(GamePlayerStat.fga),
            func.sum(GamePlayerStat.fg3m),
            func.sum(GamePlayerStat.fg3a),
            func.sum(GamePlayerStat.ftm),
            func.sum(GamePlayerStat.fta),
            func.sum(GamePlayerStat.oreb),
            func.sum(GamePlayerStat.dreb),
            func.sum(GamePlayerStat.pf),
        )
        .filter(GamePlayerStat.season == season)
        .group_by(GamePlayerStat.player_id, GamePlayerStat.team_abbreviation)
        .all()
    )

    existing = db.query(SeasonStat).filter_by(season=season, is_playoff=False).all()
    existing_keys = {(row.player_id, row.team_abbreviation): row for row in existing}
    updated = 0
    for (
        player_id,
        team_abbreviation,
        team_id,
        gp,
        min_total,
        pts,
        reb,
        ast,
        stl,
        blk,
        tov,
        fgm,
        fga,
        fg3m,
        fg3a,
        ftm,
        fta,
        oreb,
        dreb,
        pf,
    ) in grouped_rows:
        gp = int(gp or 0)
        gp_safe = gp or 1
        season_data = {
            "season": season,
            "team_abbreviation": team_abbreviation or (db.query(Team).filter_by(id=team_id).first().abbreviation if team_id else ""),
            "gp": gp,
            "gs": 0,
            "min_total": float(min_total or 0),
            "min_pg": round(float(min_total or 0) / gp_safe, 1),
            "pts": int(pts or 0),
            "pts_pg": round(float(pts or 0) / gp_safe, 1),
            "reb": int(reb or 0),
            "reb_pg": round(float(reb or 0) / gp_safe, 1),
            "ast": int(ast or 0),
            "ast_pg": round(float(ast or 0) / gp_safe, 1),
            "stl": int(stl or 0),
            "stl_pg": round(float(stl or 0) / gp_safe, 1),
            "blk": int(blk or 0),
            "blk_pg": round(float(blk or 0) / gp_safe, 1),
            "tov": int(tov or 0),
            "tov_pg": round(float(tov or 0) / gp_safe, 1),
            "fgm": int(fgm or 0),
            "fga": int(fga or 0),
            "fg_pct": round(float(fgm or 0) / float(fga or 1), 3) if fga else 0,
            "fg3m": int(fg3m or 0),
            "fg3a": int(fg3a or 0),
            "fg3_pct": round(float(fg3m or 0) / float(fg3a or 1), 3) if fg3a else 0,
            "ftm": int(ftm or 0),
            "fta": int(fta or 0),
            "ft_pct": round(float(ftm or 0) / float(fta or 1), 3) if fta else 0,
            "oreb": int(oreb or 0),
            "dreb": int(dreb or 0),
            "pf": int(pf or 0),
        }
        season_data = enrich_season_with_advanced(season_data, None)

        row = existing_keys.get((player_id, season_data["team_abbreviation"]))
        if not row:
            row = SeasonStat(
                player_id=player_id,
                season=season,
                team_abbreviation=season_data["team_abbreviation"],
                is_playoff=False,
            )
            db.add(row)
            existing_keys[(player_id, season_data["team_abbreviation"])] = row

        for key, value in season_data.items():
            if hasattr(row, key):
                setattr(row, key, value)
        updated += 1

    db.query(WarehouseGame).filter_by(season=season).update(
        {
            WarehouseGame.has_materialized_season: True,
            WarehouseGame.last_materialized_at: _utcnow(),
        },
        synchronize_session=False,
    )
    db.commit()
    return {"status": "ok", "season": season, "season_rows_updated": updated}


def rematerialize_pbp_derived_metrics(db: Session, game_id: str) -> dict:
    game = db.query(WarehouseGame).filter_by(game_id=game_id).first()
    if not game:
        return {"status": "skipped", "reason": "missing warehouse game", "game_id": game_id}
    season = game.season
    parsed_games = (
        db.query(WarehouseGame)
        .filter_by(season=season, has_parsed_pbp=True)
        .order_by(WarehouseGame.game_date.asc(), WarehouseGame.game_id.asc())
        .all()
    )
    if not parsed_games:
        game.pbp_parse_status = "empty"
        db.commit()
        return {"status": "skipped", "reason": "no parsed games in season", "game_id": game_id}

    _acquire_season_advisory_lock(db, season, "pbp_rematerialize")

    clutch_totals: Dict[int, dict] = defaultdict(lambda: {"clutch_pts": 0, "clutch_fga": 0, "clutch_fgm": 0})
    pace_totals: Dict[int, dict] = defaultdict(lambda: {"second_chance_pts": 0, "fast_break_pts": 0})
    on_off_totals: Dict[int, dict] = {}
    lineup_totals: Dict[Tuple[str, Optional[int]], Any] = {}
    parsed_with_stints = 0

    rows = db.query(SeasonStat).filter_by(season=season, is_playoff=False).all()
    for row in rows:
        row.clutch_pts = None
        row.clutch_fga = None
        row.clutch_fg_pct = None
        row.second_chance_pts = None
        row.fast_break_pts = None

    db.query(PlayerOnOff).filter_by(season=season, is_playoff=False).delete(synchronize_session=False)
    db.query(LineupStats).filter_by(season=season).delete(synchronize_session=False)
    db.flush()

    for parsed_game in parsed_games:
        player_stats = db.query(GamePlayerStat).filter_by(game_id=parsed_game.game_id).all()
        if not player_stats:
            continue

        player_map = {
            player.id: player.full_name
            for player in db.query(Player).filter(Player.id.in_([row.player_id for row in player_stats])).all()
        }
        box_score = {
            "home_team_id": parsed_game.home_team_id,
            "away_team_id": parsed_game.away_team_id,
            "home_score": parsed_game.home_score,
            "away_score": parsed_game.away_score,
            "players": [
                {
                    "player_id": row.player_id,
                    "player_name": player_map.get(row.player_id, ""),
                    "team_id": row.team_id,
                    "start_position": "G" if row.is_starter else "",
                }
                for row in player_stats
            ],
        }
        pbp_events = load_pbp_events_for_game(db, parsed_game.game_id)

        for team_id in [parsed_game.home_team_id, parsed_game.away_team_id]:
            if not team_id:
                continue
            clutch = compute_clutch_stats(pbp_events, team_id)
            pace_stats = compute_second_chance_and_fast_break(pbp_events, team_id)
            for player_id, stat_payload in clutch.items():
                acc = clutch_totals[player_id]
                acc["clutch_pts"] += stat_payload.get("clutch_pts", 0)
                acc["clutch_fga"] += stat_payload.get("clutch_fga", 0)
                acc["clutch_fgm"] += stat_payload.get("clutch_fgm", 0)
            for player_id, stat_payload in pace_stats.items():
                acc = pace_totals[player_id]
                acc["second_chance_pts"] += stat_payload.get("second_chance_pts", 0)
                acc["fast_break_pts"] += stat_payload.get("fast_break_pts", 0)

        stints = build_stints(pbp_events, box_score)
        if not stints:
            continue
        parsed_with_stints += 1

        all_team_players: Dict[int, Set[int]] = defaultdict(set)
        for row in player_stats:
            if row.team_id and row.player_id:
                all_team_players[row.team_id].add(row.player_id)

        for team_id, roster in all_team_players.items():
            for player_id, payload in compute_on_off(stints, roster).items():
                existing = on_off_totals.get(player_id)
                if not existing:
                    on_off_totals[player_id] = {
                        "on_possessions": payload.on_possessions,
                        "off_possessions": payload.off_possessions,
                        "on_team_pts": payload.on_team_pts,
                        "on_opp_pts": payload.on_opp_pts,
                        "off_team_pts": payload.off_team_pts,
                        "off_opp_pts": payload.off_opp_pts,
                        "on_seconds": payload.on_seconds,
                        "off_seconds": payload.off_seconds,
                    }
                else:
                    existing["on_possessions"] += payload.on_possessions
                    existing["off_possessions"] += payload.off_possessions
                    existing["on_team_pts"] += payload.on_team_pts
                    existing["on_opp_pts"] += payload.on_opp_pts
                    existing["off_team_pts"] += payload.off_team_pts
                    existing["off_opp_pts"] += payload.off_opp_pts
                    existing["on_seconds"] += payload.on_seconds
                    existing["off_seconds"] += payload.off_seconds

        player_team_lookup = {
            row.player_id: row.team_id
            for row in player_stats
            if row.player_id and row.team_id
        }
        for lineup_key, acc in compute_lineup_stats(stints, parsed_game.home_team_id).items():
            first_player = int(lineup_key.split("-")[0]) if lineup_key else None
            team_id = player_team_lookup.get(first_player)
            existing = lineup_totals.get((lineup_key, team_id))
            if not existing:
                lineup_totals[(lineup_key, team_id)] = acc
            else:
                existing.plus_minus += acc.plus_minus
                existing.possessions += acc.possessions
                existing.team_pts += acc.team_pts
                existing.opp_pts += acc.opp_pts
                existing.seconds += acc.seconds

    for player_id, stat_payload in clutch_totals.items():
        season_row = db.query(SeasonStat).filter_by(player_id=player_id, season=season, is_playoff=False).first()
        if not season_row:
            continue
        season_row.clutch_pts = stat_payload.get("clutch_pts")
        season_row.clutch_fga = stat_payload.get("clutch_fga") or None
        fga = stat_payload.get("clutch_fga") or 0
        fgm = stat_payload.get("clutch_fgm") or 0
        season_row.clutch_fg_pct = round(fgm / fga, 3) if fga else None

    for player_id, stat_payload in pace_totals.items():
        season_row = db.query(SeasonStat).filter_by(player_id=player_id, season=season, is_playoff=False).first()
        if not season_row:
            continue
        season_row.second_chance_pts = stat_payload.get("second_chance_pts")
        season_row.fast_break_pts = stat_payload.get("fast_break_pts")

    for player_id in sorted(on_off_totals.keys()):
        payload = on_off_totals[player_id]
        on_poss = payload["on_possessions"]
        off_poss = payload["off_possessions"]
        on_net = round((payload["on_team_pts"] - payload["on_opp_pts"]) / on_poss * 100, 1) if on_poss else None
        off_net = round((payload["off_team_pts"] - payload["off_opp_pts"]) / off_poss * 100, 1) if off_poss else None
        row = db.query(PlayerOnOff).filter_by(
            player_id=player_id, season=season, is_playoff=False
        ).first()
        if not row:
            row = PlayerOnOff(player_id=player_id, season=season, is_playoff=False)
            db.add(row)
        row.on_minutes = round(payload["on_seconds"] / 60.0, 1) if payload["on_seconds"] else None
        row.off_minutes = round(payload["off_seconds"] / 60.0, 1) if payload["off_seconds"] else None
        row.on_net_rating = on_net
        row.off_net_rating = off_net
        row.on_off_net = round(on_net - off_net, 1) if on_net is not None and off_net is not None else None
        row.on_ortg = round(payload["on_team_pts"] / on_poss * 100, 1) if on_poss else None
        row.on_drtg = round(payload["on_opp_pts"] / on_poss * 100, 1) if on_poss else None
        row.off_ortg = round(payload["off_team_pts"] / off_poss * 100, 1) if off_poss else None
        row.off_drtg = round(payload["off_opp_pts"] / off_poss * 100, 1) if off_poss else None

    for lineup_key, team_id in sorted(lineup_totals.keys(), key=lambda item: (item[1] or 0, item[0])):
        acc = lineup_totals[(lineup_key, team_id)]
        possessions = acc.possessions
        ortg = round(acc.team_pts / possessions * 100, 1) if possessions else None
        drtg = round(acc.opp_pts / possessions * 100, 1) if possessions else None
        row = db.query(LineupStats).filter_by(lineup_key=lineup_key, season=season).first()
        if not row:
            row = LineupStats(lineup_key=lineup_key, season=season, team_id=team_id)
            db.add(row)
        row.team_id = team_id
        seconds = getattr(acc, "seconds", 0.0)
        row.minutes = round(seconds / 60.0, 1) if seconds > 0 else (round(possessions / 2.0, 1) if possessions else None)
        row.net_rating = round(ortg - drtg, 1) if ortg is not None and drtg is not None else None
        row.ortg = ortg
        row.drtg = drtg
        row.plus_minus = acc.plus_minus
        row.possessions = possessions

    game.pbp_parse_status = "complete"
    game.has_parsed_pbp = True
    game.last_materialized_at = _utcnow()
    db.commit()
    return {"status": "ok", "game_id": game_id, "season": season, "games_with_stints": parsed_with_stints}


def enqueue_job(
    db: Session,
    *,
    job_type: str,
    job_key: str,
    season: Optional[str] = None,
    game_id: Optional[str] = None,
    priority: int = 100,
    payload: Optional[dict] = None,
    run_after: Optional[datetime] = None,
) -> IngestionJob:
    row = db.query(IngestionJob).filter_by(job_type=job_type, job_key=job_key).first()
    if row:
        if row.status in {JOB_STATUS_COMPLETE, JOB_STATUS_FAILED, JOB_STATUS_SKIPPED}:
            row.status = JOB_STATUS_QUEUED
            row.last_error = None
            row.completed_at = None
        row.priority = min(row.priority, priority)
        row.payload = payload or row.payload
        row.run_after = run_after or row.run_after
        db.flush()
        return row

    row = IngestionJob(
        job_type=job_type,
        job_key=job_key,
        season=season,
        game_id=game_id,
        priority=priority,
        status=JOB_STATUS_QUEUED,
        payload=payload or {},
        run_after=run_after or _utcnow(),
    )
    db.add(row)
    db.flush()
    return row


def queue_backfill_season(db: Session, season: str) -> List[IngestionJob]:
    return [enqueue_job(db, job_type="backfill_season", job_key=season, season=season, priority=10)]


def queue_date_sync(db: Session, season: str, date_key: str) -> List[IngestionJob]:
    return [enqueue_job(db, job_type="sync_date", job_key=f"{season}:{date_key}", season=season, priority=20, payload={"date_key": date_key})]


def queue_game_resync(db: Session, game_id: str, season: Optional[str] = None) -> List[IngestionJob]:
    jobs = [
        enqueue_job(db, job_type="sync_game_boxscore", job_key=game_id, season=season, game_id=game_id, priority=30),
        enqueue_job(db, job_type="sync_game_pbp", job_key=game_id, season=season, game_id=game_id, priority=31),
        enqueue_job(db, job_type="materialize_game_stats", job_key=game_id, season=season, game_id=game_id, priority=32),
    ]
    return jobs


def queue_current_season_daily_sync(db: Session, season: str) -> List[IngestionJob]:
    jobs: List[IngestionJob] = []
    today = _utcnow().date()
    for delta in range(CURRENT_SEASON_LOOKBACK_DAYS):
        day = today - timedelta(days=delta)
        jobs.extend(queue_date_sync(db, season, day.isoformat()))
    jobs.extend(queue_season_shot_charts(db, season, season_type="Regular Season"))
    return jobs


def queue_player_profile_sync(
    db: Session,
    player_id: int,
    force: bool = False,
) -> List[IngestionJob]:
    return [
        enqueue_job(
            db,
            job_type="sync_player_profile",
            job_key=_player_profile_job_key(player_id),
            priority=40,
            payload={"player_id": player_id, "force": force},
        )
    ]


def queue_player_career_sync(
    db: Session,
    player_id: int,
    force: bool = False,
) -> List[IngestionJob]:
    return [
        enqueue_job(
            db,
            job_type="sync_player_career",
            job_key=_player_career_job_key(player_id),
            priority=41,
            payload={"player_id": player_id, "force": force},
        )
    ]


def queue_player_gamelogs_sync(
    db: Session,
    player_id: int,
    season: str,
    season_type: str = "Regular Season",
    force: bool = False,
) -> List[IngestionJob]:
    return [
        enqueue_job(
            db,
            job_type="sync_player_gamelogs",
            job_key=_player_gamelog_job_key(player_id, season, season_type),
            season=season,
            priority=42,
            payload={
                "player_id": player_id,
                "season_type": season_type,
                "force": force,
            },
        )
    ]


def _replace_player_game_logs(
    db: Session,
    player_id: int,
    season: str,
    season_type: str,
    logs: List[dict],
) -> None:
    db.execute(
        PlayerGameLog.__table__.delete().where(
            PlayerGameLog.player_id == player_id,
            PlayerGameLog.season == season,
            PlayerGameLog.season_type == season_type,
        )
    )
    now = _utcnow()
    for game in logs:
        raw_date = game.get("game_date")
        game_date = None
        if raw_date:
            try:
                game_date = datetime.strptime(raw_date, "%b %d, %Y").date()
            except ValueError:
                try:
                    game_date = date.fromisoformat(raw_date)
                except ValueError:
                    game_date = None
        db.add(
            PlayerGameLog(
                player_id=player_id,
                game_id=game.get("game_id", ""),
                season=season,
                season_type=season_type,
                game_date=game_date,
                matchup=game.get("matchup"),
                wl=game.get("wl"),
                min=game.get("min"),
                pts=game.get("pts"),
                reb=game.get("reb"),
                ast=game.get("ast"),
                stl=game.get("stl"),
                blk=game.get("blk"),
                tov=game.get("tov"),
                fgm=game.get("fgm"),
                fga=game.get("fga"),
                fg_pct=game.get("fg_pct"),
                fg3m=game.get("fg3m"),
                fg3a=game.get("fg3a"),
                fg3_pct=game.get("fg3_pct"),
                ftm=game.get("ftm"),
                fta=game.get("fta"),
                ft_pct=game.get("ft_pct"),
                oreb=game.get("oreb"),
                dreb=game.get("dreb"),
                pf=game.get("pf"),
                plus_minus=game.get("plus_minus"),
                synced_at=now,
            )
        )


def _sync_player_profile_record(
    db: Session,
    player_id: int,
    force: bool = False,
) -> dict:
    run = _start_source_run(
        db,
        source="stats_player_profile",
        job_type="sync_player_profile",
        entity_type="player",
        entity_id=_player_profile_job_key(player_id),
        run_metadata={"player_id": player_id, "force": force},
    )
    try:
        player = db.query(Player).filter(Player.id == player_id).first()
        if not force and _player_profile_status(player) == "ready":
            _finish_source_run(
                db,
                run,
                status=JOB_STATUS_SKIPPED,
                records_written=1 if player else 0,
                run_metadata={"reason": "fresh_cache"},
            )
            db.commit()
            return {"status": "skipped", "player_id": player_id, "reason": "fresh cache"}

        synced = sync_player(db, player_id)
        _finish_source_run(
            db,
            run,
            status=JOB_STATUS_COMPLETE,
            records_written=1,
            run_metadata={"player_name": synced.full_name},
        )
        db.commit()
        return {"status": "ok", "player_id": player_id}
    except Exception as exc:
        db.rollback()
        _finish_source_run(db, run, status=JOB_STATUS_FAILED, error_message=str(exc))
        db.commit()
        raise


def _sync_player_career_record(
    db: Session,
    player_id: int,
    force: bool = False,
) -> dict:
    run = _start_source_run(
        db,
        source="stats_player_career",
        job_type="sync_player_career",
        entity_type="player",
        entity_id=_player_career_job_key(player_id),
        run_metadata={"player_id": player_id, "force": force},
    )
    try:
        rows = (
            db.query(SeasonStat)
            .filter(SeasonStat.player_id == player_id)
            .all()
        )
        if not force and _season_stat_status(rows) == "ready":
            _finish_source_run(
                db,
                run,
                status=JOB_STATUS_SKIPPED,
                records_written=len(rows),
                run_metadata={"reason": "fresh_cache"},
            )
            db.commit()
            return {"status": "skipped", "player_id": player_id, "reason": "fresh cache"}

        sync_player(db, player_id)
        refreshed = (
            db.query(SeasonStat)
            .filter(SeasonStat.player_id == player_id)
            .count()
        )
        _finish_source_run(
            db,
            run,
            status=JOB_STATUS_COMPLETE,
            records_written=refreshed,
        )
        db.commit()
        return {"status": "ok", "player_id": player_id, "season_rows": refreshed}
    except Exception as exc:
        db.rollback()
        _finish_source_run(db, run, status=JOB_STATUS_FAILED, error_message=str(exc))
        db.commit()
        raise


def _sync_player_game_logs(
    db: Session,
    player_id: int,
    season: str,
    season_type: str,
    force: bool = False,
) -> dict:
    run = _start_source_run(
        db,
        source="stats_gamelogs",
        job_type="sync_player_gamelogs",
        entity_type="player_season",
        entity_id=_player_gamelog_job_key(player_id, season, season_type),
        run_metadata={
            "player_id": player_id,
            "season": season,
            "season_type": season_type,
            "force": force,
        },
    )
    try:
        existing = (
            db.query(PlayerGameLog)
            .filter(
                PlayerGameLog.player_id == player_id,
                PlayerGameLog.season == season,
                PlayerGameLog.season_type == season_type,
            )
            .all()
        )
        if not force and _player_gamelog_status(existing, season) == "ready":
            _finish_source_run(
                db,
                run,
                status=JOB_STATUS_SKIPPED,
                records_written=len(existing),
                run_metadata={"reason": "fresh_cache"},
            )
            db.commit()
            return {"status": "skipped", "player_id": player_id, "reason": "fresh cache"}

        logs = get_player_game_logs(player_id, season, season_type)
        _replace_player_game_logs(db, player_id, season, season_type, logs)
        _finish_source_run(
            db,
            run,
            status=JOB_STATUS_COMPLETE,
            records_written=len(logs),
        )
        db.commit()
        return {
            "status": "ok",
            "player_id": player_id,
            "season": season,
            "season_type": season_type,
            "game_count": len(logs),
        }
    except Exception as exc:
        db.rollback()
        _finish_source_run(db, run, status=JOB_STATUS_FAILED, error_message=str(exc))
        db.commit()
        raise


def _eligible_shot_chart_player_ids(
    db: Session,
    season: str,
    season_type: str,
) -> List[int]:
    if season_type == "Regular Season":
        game_player_ids = [
            row[0]
            for row in (
                db.query(GamePlayerStat.player_id)
                .filter(GamePlayerStat.season == season)
                .distinct()
                .all()
            )
            if row[0] is not None
        ]
        if game_player_ids:
            return sorted(set(game_player_ids))

    player_game_log_ids = [
        row[0]
        for row in (
            db.query(PlayerGameLog.player_id)
            .filter(
                PlayerGameLog.season == season,
                PlayerGameLog.season_type == season_type,
            )
            .distinct()
            .all()
        )
        if row[0] is not None
    ]
    return sorted(set(player_game_log_ids))


def _sync_player_shot_chart(
    db: Session,
    player_id: int,
    season: str,
    season_type: str,
    force: bool = False,
) -> dict:
    run = _start_source_run(
        db,
        source="stats_shotchart",
        job_type="sync_player_shot_chart",
        entity_type="player_season",
        entity_id=_shot_chart_job_key(player_id, season, season_type),
        run_metadata={
            "season": season,
            "season_type": season_type,
            "player_id": player_id,
            "force": force,
        },
    )
    try:
        now = _utcnow()
        existing = (
            db.query(PlayerShotChart)
            .filter(
                PlayerShotChart.player_id == player_id,
                PlayerShotChart.season == season,
                PlayerShotChart.season_type == season_type,
            )
            .first()
        )

        if (
            existing
            and not force
            and existing.expires_at
            and existing.expires_at > now
        ):
            _finish_source_run(
                db,
                run,
                status=JOB_STATUS_SKIPPED,
                records_written=existing.shot_count or 0,
                run_metadata={"reason": "fresh_cache"},
            )
            db.commit()
            return {
                "status": "skipped",
                "player_id": player_id,
                "season": season,
                "season_type": season_type,
                "reason": "fresh cache",
            }

        raw_shots = get_shot_chart_data(player_id, season, season_type)
        raw_shots = enrich_and_validate_player_shot_payload(db, player_id, raw_shots)
        expires_at = now + timedelta(seconds=_cache_ttl_for_season(season))

        if existing:
            existing.shots = raw_shots
            existing.shot_count = len(raw_shots)
            existing.fetched_at = now
            existing.expires_at = expires_at
        else:
            db.add(
                PlayerShotChart(
                    player_id=player_id,
                    season=season,
                    season_type=season_type,
                    shots=raw_shots,
                    shot_count=len(raw_shots),
                    fetched_at=now,
                    expires_at=expires_at,
                )
            )

        _finish_source_run(
            db,
            run,
            status=JOB_STATUS_COMPLETE,
            records_written=len(raw_shots),
            run_metadata={
                "shot_count": len(raw_shots),
                "completeness": summarize_shot_completeness(raw_shots).model_dump(),
            },
        )
        db.commit()
        return {
            "status": "ok",
            "player_id": player_id,
            "season": season,
            "season_type": season_type,
            "shot_count": len(raw_shots),
        }
    except Exception as exc:
        db.rollback()
        _finish_source_run(db, run, status=JOB_STATUS_FAILED, error_message=str(exc))
        db.commit()
        raise


def queue_player_shot_chart_sync(
    db: Session,
    player_id: int,
    season: str,
    season_type: str = "Regular Season",
    force: bool = False,
) -> List[IngestionJob]:
    if season_type not in ("Regular Season", "Playoffs"):
        raise ValueError('season_type must be "Regular Season" or "Playoffs"')
    return [
        enqueue_job(
            db,
            job_type="sync_player_shot_chart",
            job_key=_shot_chart_job_key(player_id, season, season_type),
            season=season,
            priority=46,
            payload={
                "player_id": player_id,
                "season_type": season_type,
                "force": force,
            },
        )
    ]


def queue_season_shot_charts(
    db: Session,
    season: str,
    season_type: str = "Regular Season",
    force: bool = False,
) -> List[IngestionJob]:
    if season_type not in ("Regular Season", "Playoffs"):
        raise ValueError('season_type must be "Regular Season" or "Playoffs"')
    return [
        enqueue_job(
            db,
            job_type="sync_season_shot_charts",
            job_key="{0}:{1}".format(season, season_type),
            season=season,
            priority=45,
            payload={"season_type": season_type, "force": force},
        )
    ]


def queue_shot_context_upgrade(
    db: Session,
    season: str,
    season_type: str = "Regular Season",
    force: bool = True,
) -> List[IngestionJob]:
    return queue_season_shot_charts(db, season, season_type=season_type, force=force)


def queue_shot_linkage_upgrade(
    db: Session,
    season: str,
    season_type: str = "Regular Season",
    force: bool = True,
) -> List[IngestionJob]:
    return queue_season_shot_charts(db, season, season_type=season_type, force=force)


def queue_completeness_reconciliation(
    db: Session,
    season: str,
    season_type: str = "Regular Season",
    force: bool = True,
) -> List[IngestionJob]:
    return queue_season_shot_charts(db, season, season_type=season_type, force=force)


def _claim_next_job(db: Session, season: Optional[str] = None) -> Optional[IngestionJob]:
    now = _utcnow()
    query = db.query(IngestionJob).filter(
        IngestionJob.status == JOB_STATUS_QUEUED,
        IngestionJob.run_after <= now,
    )
    if season:
        query = query.filter(IngestionJob.season == season)
    job = query.order_by(IngestionJob.priority.asc(), IngestionJob.created_at.asc()).first()
    if not job:
        return None
    job.status = JOB_STATUS_RUNNING
    job.attempt_count = (job.attempt_count or 0) + 1
    job.leased_until = now + timedelta(minutes=5)
    db.commit()
    db.refresh(job)
    return job


def run_next_job(db: Session, season: Optional[str] = None) -> dict:
    job = _claim_next_job(db, season=season)
    if not job:
        return {"status": "idle"}

    try:
        result = _dispatch_job(db, job)
        job.status = JOB_STATUS_COMPLETE if result.get("status") not in {"failed", "skipped"} else (JOB_STATUS_SKIPPED if result.get("status") == "skipped" else JOB_STATUS_FAILED)
        job.last_error = result.get("reason")
        job.leased_until = None
        job.completed_at = _utcnow()
        db.commit()
        return {"status": "ok", "job_id": job.id, "job_type": job.job_type, "result": result}
    except Exception as exc:
        db.rollback()
        job = db.query(IngestionJob).filter_by(id=job.id).first()
        if job:
            if (job.attempt_count or 0) < 3:
                job.status = JOB_STATUS_QUEUED
                job.run_after = _utcnow() + timedelta(minutes=5 * job.attempt_count)
                job.completed_at = None
            else:
                job.status = JOB_STATUS_FAILED
                job.completed_at = _utcnow()
            job.last_error = str(exc)[:1000]
            job.leased_until = None
            db.commit()
        return {"status": "failed", "job_id": job.id if job else None, "job_type": job.job_type if job else None, "reason": str(exc)}


def retry_failed_jobs(db: Session, season: str) -> List[IngestionJob]:
    now = _utcnow()
    rows = db.query(IngestionJob).filter_by(season=season, status=JOB_STATUS_FAILED).all()
    for row in rows:
        row.status = JOB_STATUS_QUEUED
        row.attempt_count = 0
        row.last_error = None
        row.completed_at = None
        row.leased_until = None
        row.run_after = now
    db.commit()
    return rows


def reset_stale_jobs(db: Session, season: Optional[str] = None) -> List[IngestionJob]:
    now = _utcnow()
    stale_before = now - timedelta(minutes=1)
    query = db.query(IngestionJob).filter(
        IngestionJob.status == JOB_STATUS_RUNNING,
        IngestionJob.leased_until.isnot(None),
        IngestionJob.leased_until < stale_before,
    )
    if season:
        query = query.filter(IngestionJob.season == season)
    rows = query.all()
    for row in rows:
        row.status = JOB_STATUS_QUEUED
        row.leased_until = None
        row.completed_at = None
        row.run_after = now
        row.last_error = row.last_error or "Lease expired; returned to queue"
    db.commit()
    return rows


def get_job_summary(db: Session, season: Optional[str] = None) -> dict:
    base_query = db.query(IngestionJob)
    if season:
        base_query = base_query.filter(IngestionJob.season == season)

    status_counts = {
        JOB_STATUS_QUEUED: 0,
        JOB_STATUS_RUNNING: 0,
        JOB_STATUS_COMPLETE: 0,
        JOB_STATUS_FAILED: 0,
        JOB_STATUS_SKIPPED: 0,
    }
    for status, count in (
        base_query.with_entities(IngestionJob.status, func.count(IngestionJob.id))
        .group_by(IngestionJob.status)
        .all()
    ):
        status_counts[status] = count

    job_type_rows = (
        base_query.with_entities(
            IngestionJob.job_type,
            IngestionJob.status,
            func.count(IngestionJob.id),
        )
        .group_by(IngestionJob.job_type, IngestionJob.status)
        .order_by(IngestionJob.job_type.asc(), IngestionJob.status.asc())
        .all()
    )
    grouped_job_types: Dict[str, Dict[str, int]] = defaultdict(dict)
    for job_type, status, count in job_type_rows:
        grouped_job_types[job_type][status] = count

    oldest_queued_job = (
        base_query.filter(IngestionJob.status == JOB_STATUS_QUEUED)
        .order_by(IngestionJob.run_after.asc(), IngestionJob.created_at.asc())
        .first()
    )
    stalled_running = (
        base_query.filter(
            IngestionJob.status == JOB_STATUS_RUNNING,
            IngestionJob.leased_until.isnot(None),
            IngestionJob.leased_until < _utcnow(),
        )
        .order_by(IngestionJob.leased_until.asc())
        .all()
    )
    recent_failed_jobs = (
        base_query.filter(IngestionJob.status == JOB_STATUS_FAILED)
        .order_by(IngestionJob.updated_at.desc(), IngestionJob.id.desc())
        .limit(10)
        .all()
    )
    throttle = db.query(ApiRequestState).filter_by(source="nba_public").first()

    return {
        "season": season,
        "status_counts": status_counts,
        "job_types": [
            {
                "job_type": job_type,
                "queued": counts.get(JOB_STATUS_QUEUED, 0),
                "running": counts.get(JOB_STATUS_RUNNING, 0),
                "complete": counts.get(JOB_STATUS_COMPLETE, 0),
                "failed": counts.get(JOB_STATUS_FAILED, 0),
                "skipped": counts.get(JOB_STATUS_SKIPPED, 0),
            }
            for job_type, counts in sorted(grouped_job_types.items())
        ],
        "oldest_queued_job": _serialize_job(oldest_queued_job),
        "stalled_running_count": len(stalled_running),
        "stalled_running_jobs": [_serialize_job(row) for row in stalled_running[:10]],
        "recent_failed_jobs": [_serialize_job(row) for row in recent_failed_jobs],
        "global_request_throttle": {
            "source": throttle.source,
            "available_at": _serialize_dt(throttle.available_at),
            "last_request_at": _serialize_dt(throttle.last_request_at),
            "seconds_until_available": max(
                0.0,
                (throttle.available_at - _utcnow()).total_seconds(),
            ) if throttle and throttle.available_at else 0.0,
        } if throttle else None,
    }


def get_readiness_summary(db: Session, season: str) -> dict:
    profile_players = db.query(Player).all()
    profile_counts = {"ready": 0, "stale": 0, "missing": 0}
    for player in profile_players:
        profile_counts[_player_profile_status(player)] += 1

    career_player_ids = sorted(
        {
            row[0]
            for row in (
                db.query(SeasonStat.player_id)
                .filter(SeasonStat.season == season)
                .distinct()
                .all()
            )
            if row[0] is not None
        }
    )
    career_rows_by_player: Dict[int, List[SeasonStat]] = defaultdict(list)
    if career_player_ids:
        for row in db.query(SeasonStat).filter(SeasonStat.player_id.in_(career_player_ids)).all():
            career_rows_by_player[row.player_id].append(row)
    career_counts = {"ready": 0, "stale": 0, "missing": 0}
    for player_id in career_player_ids:
        career_counts[_season_stat_status(career_rows_by_player.get(player_id, []))] += 1

    gamelog_player_ids = sorted(
        {
            row[0]
            for row in (
                db.query(GamePlayerStat.player_id)
                .filter(GamePlayerStat.season == season)
                .distinct()
                .all()
            )
            if row[0] is not None
        }
    )
    gamelog_rows_by_player: Dict[int, List[PlayerGameLog]] = defaultdict(list)
    if gamelog_player_ids:
        for row in (
            db.query(PlayerGameLog)
            .filter(
                PlayerGameLog.season == season,
                PlayerGameLog.season_type == "Regular Season",
                PlayerGameLog.player_id.in_(gamelog_player_ids),
            )
            .all()
        ):
            gamelog_rows_by_player[row.player_id].append(row)
    gamelog_counts = {"ready": 0, "stale": 0, "missing": 0}
    for player_id in gamelog_player_ids:
        gamelog_counts[_player_gamelog_status(gamelog_rows_by_player.get(player_id, []), season)] += 1

    shotchart_player_ids = _eligible_shot_chart_player_ids(db, season, "Regular Season")
    shotchart_rows = {}
    if shotchart_player_ids:
        shotchart_rows = {
            row.player_id: row
            for row in db.query(PlayerShotChart).filter(
                PlayerShotChart.season == season,
                PlayerShotChart.season_type == "Regular Season",
                PlayerShotChart.player_id.in_(shotchart_player_ids),
            ).all()
        }
    now = _utcnow()
    shotchart_counts = {"ready": 0, "stale": 0, "missing": 0}
    for player_id in shotchart_player_ids:
        row = shotchart_rows.get(player_id)
        if row is None:
            shotchart_counts["missing"] += 1
        elif row.expires_at and row.expires_at > now:
            shotchart_counts["ready"] += 1
        else:
            shotchart_counts["stale"] += 1

    return {
        "season": season,
        "domains": [
            {
                "domain": "player_profile",
                "eligible_count": len(profile_players),
                "ready_count": profile_counts["ready"],
                "stale_count": profile_counts["stale"],
                "missing_count": profile_counts["missing"],
            },
            {
                "domain": "career_stats",
                "eligible_count": len(career_player_ids),
                "ready_count": career_counts["ready"],
                "stale_count": career_counts["stale"],
                "missing_count": career_counts["missing"],
            },
            {
                "domain": "game_logs",
                "eligible_count": len(gamelog_player_ids),
                "ready_count": gamelog_counts["ready"],
                "stale_count": gamelog_counts["stale"],
                "missing_count": gamelog_counts["missing"],
            },
            {
                "domain": "shot_charts",
                "eligible_count": len(shotchart_player_ids),
                "ready_count": shotchart_counts["ready"],
                "stale_count": shotchart_counts["stale"],
                "missing_count": shotchart_counts["missing"],
            },
        ],
    }


def get_completeness_summary(db: Session, season: str, season_type: str = "Regular Season") -> dict:
    shotchart_player_ids = _eligible_shot_chart_player_ids(db, season, season_type)
    shotchart_rows = {}
    if shotchart_player_ids:
        shotchart_rows = {
            row.player_id: row
            for row in db.query(PlayerShotChart).filter(
                PlayerShotChart.season == season,
                PlayerShotChart.season_type == season_type,
                PlayerShotChart.player_id.in_(shotchart_player_ids),
            ).all()
        }

    shot_counts = {"ready": 0, "partial": 0, "legacy": 0, "missing": 0}
    for player_id in shotchart_player_ids:
        row = shotchart_rows.get(player_id)
        if row is None:
            shot_counts["missing"] += 1
            continue
        completeness = summarize_shot_completeness(row.shots or [])
        shot_counts[completeness.status] = shot_counts.get(completeness.status, 0) + 1

    warehouse_games = db.query(WarehouseGame).filter(WarehouseGame.season == season).all()
    event_counts = {"ready": 0, "partial": 0, "legacy": 0, "missing": 0}
    for game in warehouse_games:
        if game.has_parsed_pbp:
            event_counts["ready"] += 1
        elif game.has_pbp_payload:
            event_counts["partial"] += 1
        else:
            legacy_rows = db.query(PlayByPlay).filter(PlayByPlay.game_id == game.game_id).count()
            if legacy_rows > 0:
                event_counts["legacy"] += 1
            else:
                event_counts["missing"] += 1

    def _pct(ready: int, partial: int, total: int) -> float:
        if total <= 0:
            return 0.0
        return round(((ready + (0.5 * partial)) / total) * 100.0, 1)

    return {
        "season": season,
        "season_type": season_type,
        "domains": [
            {
                "domain": "shot_charts",
                "ready_count": shot_counts["ready"],
                "partial_count": shot_counts["partial"],
                "legacy_count": shot_counts["legacy"],
                "missing_count": shot_counts["missing"],
                "completeness_pct": _pct(
                    shot_counts["ready"],
                    shot_counts["partial"],
                    len(shotchart_player_ids),
                ),
            },
            {
                "domain": "game_events",
                "ready_count": event_counts["ready"],
                "partial_count": event_counts["partial"],
                "legacy_count": event_counts["legacy"],
                "missing_count": event_counts["missing"],
                "completeness_pct": _pct(
                    event_counts["ready"],
                    event_counts["partial"],
                    len(warehouse_games),
                ),
            },
        ],
    }


def _dispatch_job(db: Session, job: IngestionJob) -> dict:
    if job.job_type == "sync_schedule":
        return sync_schedule(db, job.season or "", (job.payload or {}).get("date_key"))
    if job.job_type == "sync_date":
        result = sync_schedule(db, job.season or "", (job.payload or {}).get("date_key"))
        date_key = (job.payload or {}).get("date_key")
        games = (
            db.query(WarehouseGame)
            .filter_by(season=job.season, game_date=_parse_iso_date(date_key))
            .all()
        )
        for game in games:
            if game.status in {"live", "final"}:
                queue_game_resync(db, game.game_id, season=job.season)
        db.commit()
        return result
    if job.job_type == "sync_game_boxscore":
        return sync_game_boxscore(db, job.game_id or job.job_key)
    if job.job_type == "sync_game_pbp":
        return sync_game_pbp(db, job.game_id or job.job_key)
    if job.job_type == "materialize_game_stats":
        return materialize_game_stats(db, job.game_id or job.job_key)
    if job.job_type == "materialize_season_aggregates":
        return materialize_season_aggregates(db, job.season or job.job_key)
    if job.job_type == "sync_player_profile":
        payload = job.payload or {}
        player_id = payload.get("player_id")
        if player_id is None:
            raise ValueError("sync_player_profile payload missing player_id")
        return _sync_player_profile_record(
            db,
            int(player_id),
            force=bool(payload.get("force")),
        )
    if job.job_type == "sync_player_career":
        payload = job.payload or {}
        player_id = payload.get("player_id")
        if player_id is None:
            raise ValueError("sync_player_career payload missing player_id")
        return _sync_player_career_record(
            db,
            int(player_id),
            force=bool(payload.get("force")),
        )
    if job.job_type == "sync_player_gamelogs":
        payload = job.payload or {}
        player_id = payload.get("player_id")
        if player_id is None:
            raise ValueError("sync_player_gamelogs payload missing player_id")
        return _sync_player_game_logs(
            db,
            int(player_id),
            job.season or "",
            payload.get("season_type") or "Regular Season",
            force=bool(payload.get("force")),
        )
    if job.job_type == "sync_season_shot_charts":
        season = job.season or job.job_key.split(":", 1)[0]
        payload = job.payload or {}
        season_type = payload.get("season_type") or "Regular Season"
        force = bool(payload.get("force"))
        player_ids = _eligible_shot_chart_player_ids(db, season, season_type)
        existing_rows = {
            row.player_id: row
            for row in db.query(PlayerShotChart).filter(
                PlayerShotChart.season == season,
                PlayerShotChart.season_type == season_type,
                PlayerShotChart.player_id.in_(player_ids),
            ).all()
        } if player_ids else {}
        now = _utcnow()
        queued = 0
        skipped = 0
        for player_id in player_ids:
            existing = existing_rows.get(player_id)
            is_fresh = (
                existing is not None
                and existing.expires_at is not None
                and existing.expires_at > now
            )
            if not force and is_fresh:
                skipped += 1
                continue
            queue_player_shot_chart_sync(
                db,
                player_id=player_id,
                season=season,
                season_type=season_type,
                force=force,
            )
            queued += 1
        db.commit()
        return {
            "status": "ok",
            "season": season,
            "season_type": season_type,
            "eligible_players": len(player_ids),
            "queued_players": queued,
            "skipped_players": skipped,
        }
    if job.job_type == "sync_player_shot_chart":
        payload = job.payload or {}
        player_id = payload.get("player_id")
        if player_id is None:
            raise ValueError("sync_player_shot_chart payload missing player_id")
        return _sync_player_shot_chart(
            db,
            int(player_id),
            job.season or "",
            payload.get("season_type") or "Regular Season",
            force=bool(payload.get("force")),
        )
    if job.job_type == "sync_injuries":
        from services.sync_service import sync_injuries as _sync_injuries
        summary = _sync_injuries(db, job.season or "2024-25")
        return {"status": "ok", **summary}
    if job.job_type == "backfill_season":
        result = sync_schedule(db, job.season or job.job_key)
        completed_games = db.query(WarehouseGame).filter(
            WarehouseGame.season == (job.season or job.job_key),
            WarehouseGame.status.in_(["live", "final"]),
        ).all()
        for game in completed_games:
            queue_game_resync(db, game.game_id, season=game.season)
        enqueue_job(
            db,
            job_type="materialize_season_aggregates",
            job_key=job.season or job.job_key,
            season=job.season or job.job_key,
            priority=80,
            run_after=_utcnow() + timedelta(minutes=5),
        )
        db.commit()
        return {
            **result,
            "games_enqueued": len(completed_games),
        }
    raise ValueError(f"Unknown job type: {job.job_type}")


def get_game_health(db: Session, game_id: str) -> Optional[dict]:
    game = db.query(WarehouseGame).filter_by(game_id=game_id).first()
    if not game:
        return None
    raw_types = [
        row.payload_type
        for row in db.query(RawGamePayload).filter_by(game_id=game_id).order_by(RawGamePayload.payload_type.asc()).all()
    ]
    return {
        "game_id": game.game_id,
        "season": game.season,
        "game_date": _serialize_dt(game.game_date),
        "status": game.status,
        "home_team_abbreviation": game.home_team_abbreviation,
        "away_team_abbreviation": game.away_team_abbreviation,
        "has_schedule": bool(game.has_schedule),
        "has_final_box_score": bool(game.has_final_box_score),
        "has_pbp_payload": bool(game.has_pbp_payload),
        "has_parsed_pbp": bool(game.has_parsed_pbp),
        "has_materialized_game_stats": bool(game.has_materialized_game_stats),
        "has_materialized_season": bool(game.has_materialized_season),
        "pbp_parse_status": game.pbp_parse_status,
        "game_player_rows": db.query(GamePlayerStat).filter_by(game_id=game_id).count(),
        "game_team_rows": db.query(GameTeamStat).filter_by(game_id=game_id).count(),
        "pbp_event_rows": db.query(PlayByPlayEvent).filter_by(game_id=game_id).count(),
        "raw_payload_types": raw_types,
        "last_box_score_sync_at": _serialize_dt(game.last_box_score_sync_at),
        "last_pbp_sync_at": _serialize_dt(game.last_pbp_sync_at),
        "last_materialized_at": _serialize_dt(game.last_materialized_at),
    }


def get_season_health(db: Session, season: str) -> dict:
    latest_runs = (
        db.query(SourceRun)
        .order_by(SourceRun.started_at.desc(), SourceRun.id.desc())
        .limit(10)
        .all()
    )
    filtered_runs = [
        row
        for row in latest_runs
        if (row.run_metadata or {}).get("season") == season or row.entity_id == season
    ]
    return {
        "season": season,
        "total_games": db.query(WarehouseGame).filter_by(season=season).count(),
        "scheduled_games": db.query(WarehouseGame).filter_by(season=season, has_schedule=True).count(),
        "completed_games": db.query(WarehouseGame).filter(
            WarehouseGame.season == season,
            WarehouseGame.status.in_(["live", "final"]),
        ).count(),
        "games_with_box_score": db.query(WarehouseGame).filter_by(season=season, has_final_box_score=True).count(),
        "games_with_pbp_payload": db.query(WarehouseGame).filter_by(season=season, has_pbp_payload=True).count(),
        "games_with_parsed_pbp": db.query(WarehouseGame).filter_by(season=season, has_parsed_pbp=True).count(),
        "games_materialized": db.query(WarehouseGame).filter_by(season=season, has_materialized_game_stats=True).count(),
        "pending_jobs": db.query(IngestionJob).filter_by(season=season, status=JOB_STATUS_QUEUED).count(),
        "running_jobs": db.query(IngestionJob).filter_by(season=season, status=JOB_STATUS_RUNNING).count(),
        "failed_jobs": db.query(IngestionJob).filter_by(season=season, status=JOB_STATUS_FAILED).count(),
        "latest_runs": [
            {
                "id": row.id,
                "source": row.source,
                "job_type": row.job_type,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "status": row.status,
                "attempt_count": row.attempt_count,
                "records_written": row.records_written,
                "error_message": row.error_message,
                "started_at": _serialize_dt(row.started_at),
                "completed_at": _serialize_dt(row.completed_at),
                "run_metadata": row.run_metadata or {},
            }
            for row in filtered_runs
        ],
    }


def list_jobs(
    db: Session,
    status: Optional[str] = None,
    season: Optional[str] = None,
    limit: int = 50,
) -> List[IngestionJob]:
    query = db.query(IngestionJob)
    if status:
        query = query.filter_by(status=status)
    if season:
        query = query.filter(IngestionJob.season == season)
    return query.order_by(IngestionJob.created_at.desc()).limit(limit).all()


def _serialize_job(row: Optional[IngestionJob]) -> Optional[dict]:
    if not row:
        return None
    return {
        "id": row.id,
        "job_type": row.job_type,
        "job_key": row.job_key,
        "season": row.season,
        "game_id": row.game_id,
        "priority": row.priority,
        "status": row.status,
        "attempt_count": row.attempt_count,
        "last_error": row.last_error,
        "run_after": _serialize_dt(row.run_after),
        "leased_until": _serialize_dt(row.leased_until),
        "completed_at": _serialize_dt(row.completed_at),
    }


def _infer_season_from_date(game_date: Optional[date]) -> str:
    base = game_date or _utcnow().date()
    start_year = base.year if base.month >= 8 else base.year - 1
    return f"{start_year}-{str((start_year + 1) % 100).zfill(2)}"


def _event_family(action_type: str) -> str:
    if action_type in {"2pt", "3pt", "freethrow"}:
        return "shot"
    if action_type == "rebound":
        return "rebound"
    if action_type == "turnover":
        return "turnover"
    if action_type == "substitution":
        return "substitution"
    if action_type == "period":
        return "period"
    return action_type or "other"


def _to_int(value: Any) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
