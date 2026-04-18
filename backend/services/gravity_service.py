"""MVP-facing gravity profiles from official rows or transparent local proxies."""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

from sqlalchemy.orm import Session

from db.models import (
    Player,
    PlayerGravityStat,
    PlayerHustleStat,
    PlayerOnOff,
    PlayerPlayTypeStat,
    PlayerShotChart,
    PlayerTrackingStat,
    SeasonStat,
)
from models.mvp import MvpGravityProfile


def _round(value: Optional[float], digits: int = 1) -> Optional[float]:
    return round(float(value), digits) if value is not None else None


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _avg(values: Iterable[Optional[float]]) -> Optional[float]:
    filtered = [float(v) for v in values if v is not None]
    return sum(filtered) / len(filtered) if filtered else None


def _latest_official_row(db: Session, player_id: int, season: str, season_type: str) -> Optional[PlayerGravityStat]:
    return (
        db.query(PlayerGravityStat)
        .filter(
            PlayerGravityStat.player_id == player_id,
            PlayerGravityStat.season == season,
            PlayerGravityStat.season_type == season_type,
            PlayerGravityStat.source != "courtvue_proxy",
        )
        .order_by(PlayerGravityStat.updated_at.desc().nullslast())
        .first()
    )


def _proxy_row(db: Session, player_id: int, season: str, season_type: str) -> Optional[PlayerGravityStat]:
    return (
        db.query(PlayerGravityStat)
        .filter_by(player_id=player_id, season=season, season_type=season_type, source="courtvue_proxy")
        .first()
    )


def _profile_from_row(row: PlayerGravityStat) -> MvpGravityProfile:
    official = row.source != "courtvue_proxy"
    shooting_gravity = row.shooting_gravity
    rim_gravity = row.rim_gravity
    creation_gravity = row.creation_gravity
    off_ball_gravity = row.off_ball_gravity
    if official:
        shooting_gravity = shooting_gravity if shooting_gravity is not None else _avg([
            row.on_ball_perimeter_gravity,
            row.off_ball_perimeter_gravity,
        ])
        rim_gravity = rim_gravity if rim_gravity is not None else _avg([
            row.on_ball_interior_gravity,
            row.off_ball_interior_gravity,
        ])
        creation_gravity = creation_gravity if creation_gravity is not None else _avg([
            row.on_ball_perimeter_gravity,
            row.on_ball_interior_gravity,
        ])
        off_ball_gravity = off_ball_gravity if off_ball_gravity is not None else _avg([
            row.off_ball_perimeter_gravity,
            row.off_ball_interior_gravity,
        ])
    overall_gravity = row.overall_gravity if row.overall_gravity is not None else _avg([
        shooting_gravity,
        rim_gravity,
        creation_gravity,
        row.roll_or_screen_gravity,
        off_ball_gravity,
        row.spacing_lift,
    ])
    return MvpGravityProfile(
        player_id=row.player_id,
        source=row.source,
        source_label="Official NBA Gravity" if official else "CourtVue Proxy Gravity",
        overall_gravity=_round(overall_gravity, 1),
        shooting_gravity=_round(shooting_gravity, 1),
        rim_gravity=_round(rim_gravity, 1),
        creation_gravity=_round(creation_gravity, 1),
        roll_or_screen_gravity=_round(row.roll_or_screen_gravity, 1),
        off_ball_gravity=_round(off_ball_gravity, 1),
        spacing_lift=_round(row.spacing_lift, 1),
        gravity_confidence=row.gravity_confidence or "low",
        gravity_minutes=_round(row.gravity_minutes, 1),
        source_note=row.source_note or (
            "Official NBA Gravity fields persisted from the Inside the Game surface."
            if official else
            "CourtVue proxy derived from persisted shot, play-type, tracking, hustle, and on/off data."
        ),
        warnings=list(row.warnings or []),
    )


def _shot_profile(db: Session, player_id: int, season: str, season_type: str) -> Dict[str, float]:
    row = (
        db.query(PlayerShotChart)
        .filter_by(player_id=player_id, season=season, season_type=season_type)
        .order_by(PlayerShotChart.fetched_at.desc().nullslast())
        .first()
    )
    shots = list(row.shots or []) if row else []
    total = float(len(shots))
    if total <= 0:
        return {"total": 0.0, "three_rate": 0.0, "rim_rate": 0.0, "deep_three_rate": 0.0}
    threes = [shot for shot in shots if "3PT" in str(shot.get("shot_type", "")).upper()]
    rim = [
        shot for shot in shots
        if str(shot.get("zone_basic", "")).lower() == "restricted area" or float(shot.get("distance") or 99) <= 4
    ]
    deep = [shot for shot in threes if float(shot.get("distance") or 0) >= 26]
    return {
        "total": total,
        "three_rate": len(threes) / total,
        "rim_rate": len(rim) / total,
        "deep_three_rate": len(deep) / total,
    }


def _play_type_map(db: Session, player_id: int, season: str, season_type: str) -> Dict[str, PlayerPlayTypeStat]:
    rows = db.query(PlayerPlayTypeStat).filter_by(player_id=player_id, season=season, season_type=season_type).all()
    return {row.play_type.lower(): row for row in rows}


def _tracking_rows(db: Session, player_id: int, season: str, season_type: str) -> List[PlayerTrackingStat]:
    return db.query(PlayerTrackingStat).filter_by(player_id=player_id, season=season, season_type=season_type).all()


def _hustle_row(db: Session, player_id: int, season: str, season_type: str) -> Optional[PlayerHustleStat]:
    return db.query(PlayerHustleStat).filter_by(player_id=player_id, season=season, season_type=season_type).first()


def compute_proxy_gravity_profile(
    db: Session,
    player_id: int,
    season: str,
    season_type: str = "Regular Season",
) -> MvpGravityProfile:
    stat = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.player_id == player_id,
            SeasonStat.season == season,
            SeasonStat.is_playoff == (season_type != "Regular Season"),
        )
        .order_by(SeasonStat.team_abbreviation.desc())
        .first()
    )
    on_off = db.query(PlayerOnOff).filter_by(player_id=player_id, season=season, is_playoff=False).first()
    shots = _shot_profile(db, player_id, season, season_type)
    play_types = _play_type_map(db, player_id, season, season_type)
    tracking = _tracking_rows(db, player_id, season, season_type)
    hustle = _hustle_row(db, player_id, season, season_type)

    warnings: List[str] = []
    if shots["total"] <= 0:
        warnings.append("Shot-chart coverage missing; shooting and rim gravity use season stat fallbacks.")
    if not play_types:
        warnings.append("Official play-type rows missing; creation and roll gravity are partial.")
    if not tracking:
        warnings.append("Tracking rows missing; off-ball gravity is partial.")
    if not hustle:
        warnings.append("Hustle rows missing; screen gravity is partial.")

    fg3a_pg = float(stat.fg3a or 0) / float(stat.gp or 1) if stat else 0.0
    fta_pg = float(stat.fta or 0) / float(stat.gp or 1) if stat else 0.0
    ast_pg = float(stat.ast_pg or 0.0) if stat else 0.0
    usage = float(stat.usg_pct or 0.0) if stat else 0.0
    usage = usage * 100.0 if usage <= 1.0 else usage
    ts = float(stat.ts_pct or 0.0) if stat else 0.0
    ts = ts * 100.0 if ts <= 1.0 else ts

    catch_shoot_fga = sum(float(row.catch_shoot_fga or 0.0) for row in tracking)
    passes_received = sum(float(row.passes_received or 0.0) for row in tracking)
    drives = sum(float(row.drives or 0.0) for row in tracking)
    screen_assists = float(hustle.screen_assists or 0.0) if hustle else 0.0
    on_off_net = float(on_off.on_off_net or 0.0) if on_off else 0.0

    isolation = play_types.get("isolation")
    pnr = play_types.get("pick and roll ball handler") or play_types.get("p&r ball handler")
    roll = play_types.get("roll man") or play_types.get("cut")
    spot = play_types.get("spot up")

    shooting = _clamp(38 + fg3a_pg * 5.0 + shots["three_rate"] * 28.0 + shots["deep_three_rate"] * 25.0 + (spot.ppp if spot and spot.ppp else 0.0) * 6.0)
    rim = _clamp(35 + fta_pg * 5.0 + shots["rim_rate"] * 30.0 + usage * 0.35)
    creation = _clamp(35 + ast_pg * 4.0 + usage * 0.7 + drives * 0.25 + (isolation.ppp if isolation and isolation.ppp else 0.0) * 5.0 + (pnr.ppp if pnr and pnr.ppp else 0.0) * 5.0)
    roll_screen = _clamp(35 + screen_assists * 1.4 + (roll.ppp if roll and roll.ppp else 0.0) * 12.0)
    off_ball = _clamp(35 + catch_shoot_fga * 0.35 + passes_received * 0.08 + shots["three_rate"] * 25.0)
    spacing_lift = _clamp(50 + on_off_net * 1.4 + (ts - 57.0) * 1.1)
    overall = _avg([shooting, rim, creation, roll_screen, off_ball, spacing_lift]) or 50.0
    coverage = sum([shots["total"] > 0, bool(play_types), bool(tracking), hustle is not None, on_off is not None])
    confidence = "high" if coverage >= 4 else "medium" if coverage >= 2 else "low"

    return MvpGravityProfile(
        player_id=player_id,
        source="courtvue_proxy",
        source_label="CourtVue Proxy Gravity",
        overall_gravity=_round(overall, 1),
        shooting_gravity=_round(shooting, 1),
        rim_gravity=_round(rim, 1),
        creation_gravity=_round(creation, 1),
        roll_or_screen_gravity=_round(roll_screen, 1),
        off_ball_gravity=_round(off_ball, 1),
        spacing_lift=_round(spacing_lift, 1),
        gravity_confidence=confidence,
        gravity_minutes=_round(stat.min_total if stat else None, 1),
        source_note="CourtVue proxy derived from persisted shot, play-type, tracking, hustle, and on/off data. It is not official NBA Gravity.",
        warnings=warnings,
    )


def build_gravity_profile(
    db: Session,
    player_id: int,
    season: str,
    season_type: str = "Regular Season",
) -> MvpGravityProfile:
    official = _latest_official_row(db, player_id, season, season_type)
    if official:
        return _profile_from_row(official)
    proxy = _proxy_row(db, player_id, season, season_type)
    if proxy:
        return _profile_from_row(proxy)
    return compute_proxy_gravity_profile(db, player_id, season, season_type)


def persist_proxy_gravity_profiles(
    db: Session,
    player_ids: Sequence[int],
    season: str,
    season_type: str = "Regular Season",
) -> int:
    count = 0
    for player_id in player_ids:
        profile = compute_proxy_gravity_profile(db, int(player_id), season, season_type)
        row = _proxy_row(db, int(player_id), season, season_type)
        if not row:
            player = db.query(Player).filter_by(id=int(player_id)).first()
            row = PlayerGravityStat(
                player_id=int(player_id),
                season=season,
                season_type=season_type,
                source="courtvue_proxy",
                team_id=player.team_id if player else None,
            )
            db.add(row)
        for field in [
            "overall_gravity",
            "shooting_gravity",
            "rim_gravity",
            "creation_gravity",
            "roll_or_screen_gravity",
            "off_ball_gravity",
            "spacing_lift",
            "gravity_confidence",
            "gravity_minutes",
            "source_note",
            "warnings",
        ]:
            setattr(row, field, getattr(profile, field))
        count += 1
    db.commit()
    return count
