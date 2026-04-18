"""Persist MVP-relevant official context feeds for DB-first gravity reads."""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, Optional, Sequence

from sqlalchemy.orm import Session

from data.nba_client import (
    get_inside_game_gravity_rows,
    get_league_hustle_player_stats,
    get_player_tracking_dashboard,
    get_synergy_player_play_types,
)
from db.models import PlayerGravityStat, PlayerHustleStat, PlayerPlayTypeStat, PlayerTrackingStat
from services.gravity_service import persist_proxy_gravity_profiles


logger = logging.getLogger(__name__)


def _float(row: Dict[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _int(row: Dict[str, Any], *keys: str) -> Optional[int]:
    value = _float(row, *keys)
    return int(value) if value is not None else None


def _player_id(row: Dict[str, Any]) -> Optional[int]:
    value = row.get("PLAYER_ID") or row.get("PLAYERID") or row.get("PERSON_ID") or row.get("playerId")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def sync_player_play_type_stats(
    db: Session,
    season: str,
    season_type: str = "Regular Season",
    player_ids: Optional[Sequence[int]] = None,
) -> dict:
    refreshed = 0
    created = 0
    requested = {int(pid) for pid in player_ids} if player_ids else None
    for grouping in ["offensive", "defensive"]:
        try:
            rows = get_synergy_player_play_types(season, season_type=season_type, type_grouping=grouping)
        except Exception as exc:  # pragma: no cover - network/source defensive guard
            logger.warning("Synergy play-type sync failed for %s/%s: %s", season, grouping, exc)
            rows = []
        for payload in rows:
            pid = _player_id(payload)
            if not pid or (requested and pid not in requested):
                continue
            play_type = str(payload.get("PLAY_TYPE") or payload.get("playType") or "").strip()
            type_grouping = str(payload.get("TYPE_GROUPING") or grouping or "offensive").strip().lower()
            if not play_type:
                continue
            row = (
                db.query(PlayerPlayTypeStat)
                .filter_by(
                    player_id=pid,
                    season=season,
                    season_type=season_type,
                    play_type=play_type,
                    type_grouping=type_grouping,
                    source="stats.nba.com/synergy-play-types",
                )
                .first()
            )
            if not row:
                row = PlayerPlayTypeStat(
                    player_id=pid,
                    season=season,
                    season_type=season_type,
                    play_type=play_type,
                    type_grouping=type_grouping,
                )
                db.add(row)
                created += 1
            row.team_id = _int(payload, "TEAM_ID")
            row.team_abbreviation = payload.get("TEAM_ABBREVIATION")
            row.gp = _int(payload, "GP")
            row.possessions = _float(payload, "POSS")
            row.poss_pct = _float(payload, "POSS_PCT")
            row.points = _float(payload, "PTS")
            row.ppp = _float(payload, "PPP")
            row.percentile = _float(payload, "PERCENTILE")
            row.fg_pct = _float(payload, "FG_PCT")
            row.efg_pct = _float(payload, "EFG_PCT")
            row.tov_poss_pct = _float(payload, "TOV_POSS_PCT")
            row.score_poss_pct = _float(payload, "SCORE_POSS_PCT")
            row.raw_payload = payload
            refreshed += 1
    db.commit()
    return {"status": "ok", "rows_synced": refreshed, "rows_created": created}


def sync_player_hustle_stats(db: Session, season: str, season_type: str = "Regular Season") -> dict:
    try:
        rows = get_league_hustle_player_stats(season, season_type=season_type)
    except Exception as exc:  # pragma: no cover
        logger.warning("Hustle sync failed for %s: %s", season, exc)
        rows = []
    refreshed = 0
    created = 0
    for payload in rows:
        pid = _player_id(payload)
        if not pid:
            continue
        row = (
            db.query(PlayerHustleStat)
            .filter_by(player_id=pid, season=season, season_type=season_type, source="stats.nba.com/league-hustle")
            .first()
        )
        if not row:
            row = PlayerHustleStat(player_id=pid, season=season, season_type=season_type)
            db.add(row)
            created += 1
        row.team_id = _int(payload, "TEAM_ID")
        row.team_abbreviation = payload.get("TEAM_ABBREVIATION")
        row.gp = _int(payload, "G", "GP")
        row.minutes = _float(payload, "MIN")
        row.contested_shots = _float(payload, "CONTESTED_SHOTS")
        row.deflections = _float(payload, "DEFLECTIONS")
        row.charges_drawn = _float(payload, "CHARGES_DRAWN")
        row.screen_assists = _float(payload, "SCREEN_ASSISTS")
        row.screen_assist_points = _float(payload, "SCREEN_AST_PTS")
        row.loose_balls_recovered = _float(payload, "LOOSE_BALLS_RECOVERED")
        row.box_outs = _float(payload, "BOX_OUTS")
        row.raw_payload = payload
        refreshed += 1
    db.commit()
    return {"status": "ok", "rows_synced": refreshed, "rows_created": created}


def sync_player_tracking_stats(
    db: Session,
    season: str,
    player_ids: Sequence[int],
    season_type: str = "Regular Season",
) -> dict:
    refreshed = 0
    created = 0
    for player_id in player_ids:
        try:
            rows = get_player_tracking_dashboard(int(player_id), season, season_type=season_type)
        except Exception as exc:  # pragma: no cover
            logger.warning("Tracking sync failed for %s/%s: %s", player_id, season, exc)
            rows = []
        for item in rows:
            payload = dict(item.get("raw") or {})
            family = str(item.get("family") or "tracking")
            split_key = str(item.get("split_key") or "overall")
            row = (
                db.query(PlayerTrackingStat)
                .filter_by(
                    player_id=int(player_id),
                    season=season,
                    season_type=season_type,
                    tracking_family=family,
                    split_key=split_key,
                    source="stats.nba.com/player-tracking",
                )
                .first()
            )
            if not row:
                row = PlayerTrackingStat(
                    player_id=int(player_id),
                    season=season,
                    season_type=season_type,
                    tracking_family=family,
                    split_key=split_key,
                )
                db.add(row)
                created += 1
            row.gp = _int(payload, "GP", "G")
            row.touches = _float(payload, "TOUCHES")
            row.drives = _float(payload, "DRIVES")
            row.passes_made = _float(payload, "PASS")
            row.passes_received = _float(payload, "PASS")
            row.catch_shoot_fga = _float(payload, "CATCH_SHOOT_FGA", "FGA")
            row.catch_shoot_pts = _float(payload, "CATCH_SHOOT_PTS", "PTS")
            row.pull_up_fga = _float(payload, "PULL_UP_FGA")
            row.pull_up_pts = _float(payload, "PULL_UP_PTS")
            row.paint_touch_pts = _float(payload, "PAINT_TOUCH_PTS")
            row.close_touch_pts = _float(payload, "CLOSE_TOUCH_PTS")
            row.raw_payload = payload
            refreshed += 1
    db.commit()
    return {"status": "ok", "rows_synced": refreshed, "rows_created": created}


def sync_official_gravity_stats(
    db: Session,
    season: str,
    season_type: str = "Regular Season",
    fallback_player_ids: Optional[Iterable[int]] = None,
) -> dict:
    rows = get_inside_game_gravity_rows(season, season_type=season_type)
    created = 0
    refreshed = 0
    if rows:
        for payload in rows:
            pid = _player_id(payload)
            if not pid:
                continue
            row = (
                db.query(PlayerGravityStat)
                .filter_by(player_id=pid, season=season, season_type=season_type, source="nba_inside_the_game")
                .first()
            )
            if not row:
                row = PlayerGravityStat(player_id=pid, season=season, season_type=season_type, source="nba_inside_the_game")
                db.add(row)
                created += 1
            row.overall_gravity = _float(payload, "GRAV", "AVG_GRAVITY", "gravity")
            row.on_ball_perimeter_gravity = _float(payload, "ON_BALL_PERIM_GRAV", "AVGONBALLPERIMETERGRAVITYSCORE")
            row.off_ball_perimeter_gravity = _float(payload, "OFF_BALL_PERIM_GRAV", "AVGOFFBALLPERIMETERGRAVITYSCORE")
            row.on_ball_interior_gravity = _float(payload, "ON_BALL_INTERIOR_GRAV")
            row.off_ball_interior_gravity = _float(payload, "OFF_BALL_INTERIOR_GRAV")
            row.gravity_minutes = _float(payload, "GV-MP", "GRAVITY_MINUTES")
            row.gravity_confidence = "high"
            row.source_note = "Official NBA Inside the Game Gravity persisted when a structured source was available."
            row.raw_payload = payload
            refreshed += 1
        db.commit()
        return {"status": "ok", "source": "nba_inside_the_game", "rows_synced": refreshed, "rows_created": created}

    fallback_ids = [int(pid) for pid in fallback_player_ids or []]
    proxy_count = persist_proxy_gravity_profiles(db, fallback_ids, season, season_type) if fallback_ids else 0
    return {
        "status": "fallback",
        "source": "courtvue_proxy",
        "rows_synced": proxy_count,
        "rows_created": 0,
        "warnings": ["Official NBA Gravity structured source unavailable; persisted CourtVue proxy rows instead."],
    }
