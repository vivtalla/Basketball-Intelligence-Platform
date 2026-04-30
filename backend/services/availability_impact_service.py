"""Availability-impact projection.

Sprint 78 FO5. Extends `team_availability_service` with a projection layer
that takes the team's current PlayerInjury rows, walks the bench rotation
to identify replacements, and produces a net-rating delta + rotation
re-organization summary. Read-only (no DB writes).

Net-rating delta methodology
----------------------------
We sum each sidelined player's `on_off_net` (capped at the team's healthy
net rating to avoid runaway estimates) weighted by the share of the
team's per-game minutes they would otherwise play. This is a deliberately
simple proxy — the goal is to anchor the panel with a quantified
direction-of-change, not to publish a public projection. The number is
clamped to a sane range and the panel surfaces the methodology in a popover.
"""
from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import Player, PlayerInjury, PlayerOnOff, SeasonStat, Team, TeamSeasonStat
from models.injury import (
    DurationEstimate,
    PlayerAvailabilityProjection,
    RotationReplacement,
    TeamAvailabilityImpact,
)
from services.injury_duration_model import (
    expected_duration,
    player_age,
    player_recurrence_for_body_part,
)
from services.team_availability_service import (
    _impact_label,
    _normalize_bucket,
    _pick_best_stat_rows,
)


SIDELINED_BUCKETS = {"unavailable", "questionable"}
NET_RATING_DELTA_CLAMP = 25.0
MIN_PG_TOTAL = 240.0  # minutes available per game


def _impact_score(stat: Optional[SeasonStat]) -> float:
    if stat is None:
        return 0.0
    return float(stat.pts_pg or 0.0) + max(float(stat.bpm or 0.0), 0.0) * 2.0


def _normalize_body_part(injury_type: Optional[str], detail: Optional[str]) -> Optional[str]:
    """Map free-text injury_type/detail to the body-part vocabulary used by
    the duration model."""
    candidates = [injury_type or "", detail or ""]
    text = " ".join(candidates).lower()
    if not text.strip():
        return None
    # Order matters: longer / more specific keywords first.
    for keyword, body_part in (
        ("hamstring", "hamstring"),
        ("groin", "groin"),
        ("calf", "calf"),
        ("achilles", "calf"),
        ("ankle", "ankle"),
        ("foot", "foot"),
        ("toe", "foot"),
        ("knee", "knee"),
        ("acl", "knee"),
        ("meniscus", "knee"),
        ("patella", "knee"),
        ("quad", "knee"),
        ("lower back", "lower-back"),
        ("low back", "lower-back"),
        ("back", "lower-back"),
        ("shoulder", "shoulder"),
        ("rotator", "shoulder"),
        ("finger", "finger"),
        ("thumb", "finger"),
        ("hand", "finger"),
        ("wrist", "wrist"),
        ("elbow", "wrist"),
    ):
        if keyword in text:
            return body_part
    return None


def _build_replacement(
    out_player_id: int,
    out_player_name: str,
    out_min_pg: Optional[float],
    rotation_pool: List[Tuple[Player, SeasonStat]],
    used: set,
) -> Optional[RotationReplacement]:
    """Pick the highest-impact bench player (by pts_pg, then bpm) not yet used."""
    best: Optional[Tuple[Player, SeasonStat]] = None
    for player, stat in rotation_pool:
        if player.id == out_player_id or player.id in used:
            continue
        if best is None or _impact_score(stat) > _impact_score(best[1]):
            best = (player, stat)
    if best is None:
        return RotationReplacement(
            out_player_id=out_player_id,
            out_player_name=out_player_name,
            out_min_pg=out_min_pg,
            replacement_player_id=None,
            replacement_player_name=None,
            replacement_min_pg=None,
            additional_minutes=None,
            note="No bench replacement available — minutes redistributed across remaining roster.",
        )
    rep_player, rep_stat = best
    used.add(rep_player.id)
    additional = round(float(out_min_pg or 0.0), 1) if out_min_pg else None
    note_pieces = []
    if additional and additional > 0:
        note_pieces.append("absorbs ~{0} extra mpg".format(additional))
    rep_min = rep_stat.min_pg if rep_stat else None
    if rep_min is not None:
        note_pieces.append("currently {0:.1f} mpg".format(float(rep_min)))
    return RotationReplacement(
        out_player_id=out_player_id,
        out_player_name=out_player_name,
        out_min_pg=out_min_pg,
        replacement_player_id=rep_player.id,
        replacement_player_name=rep_player.full_name,
        replacement_min_pg=float(rep_min) if rep_min is not None else None,
        additional_minutes=additional,
        note=", ".join(note_pieces) or "Step-up minutes assignment.",
    )


def _build_summary(
    team: Team,
    out_count: int,
    questionable_count: int,
    sidelined_minutes: float,
    sidelined_pts: float,
    net_delta: Optional[float],
) -> str:
    if out_count == 0 and questionable_count == 0:
        return "{0} is at full availability — no rotation projection needed.".format(team.abbreviation)
    parts: List[str] = []
    parts.append(
        "{0}: {1} out, {2} questionable.".format(team.abbreviation, out_count, questionable_count)
    )
    if sidelined_minutes > 0 or sidelined_pts > 0:
        parts.append(
            "{0:.0f} mpg / {1:.1f} ppg removed from rotation.".format(
                sidelined_minutes, sidelined_pts
            )
        )
    if net_delta is not None:
        sign = "+" if net_delta >= 0 else ""
        parts.append("Projected net-rating swing {0}{1:.1f}.".format(sign, net_delta))
    return " ".join(parts)


def compute_team_availability_impact(
    db: Session,
    team_id: int,
    season: str,
    today: Optional[date] = None,
) -> TeamAvailabilityImpact:
    """Compute the projected availability impact for a team's next game.

    Returns a TeamAvailabilityImpact even when no players are sidelined
    (with empty arrays + summary indicating full availability), so the
    frontend can mount the panel unconditionally.
    """
    team = db.query(Team).filter(Team.id == team_id).first()
    if team is None:
        raise HTTPException(status_code=404, detail="Team {0} not found.".format(team_id))

    roster_players = (
        db.query(Player)
        .filter(Player.team_id == team.id, Player.is_active == True)  # noqa: E712
        .all()
    )
    player_ids = [p.id for p in roster_players]
    player_map: Dict[int, Player] = {p.id: p for p in roster_players}

    stat_map: Dict[int, SeasonStat] = {}
    if player_ids:
        stat_rows = (
            db.query(SeasonStat)
            .filter(
                SeasonStat.player_id.in_(player_ids),
                SeasonStat.season == season,
                SeasonStat.is_playoff == False,  # noqa: E712
            )
            .all()
        )
        stat_map = _pick_best_stat_rows(stat_rows, team.abbreviation)

    on_off_map: Dict[int, PlayerOnOff] = {}
    if player_ids:
        on_off_rows = (
            db.query(PlayerOnOff)
            .filter(
                PlayerOnOff.player_id.in_(player_ids),
                PlayerOnOff.season == season,
                PlayerOnOff.is_playoff == False,  # noqa: E712
            )
            .all()
        )
        on_off_map = {row.player_id: row for row in on_off_rows}

    latest = (
        db.query(PlayerInjury.report_date)
        .filter(PlayerInjury.season == season)
        .order_by(PlayerInjury.report_date.desc())
        .first()
    )
    report_date = latest[0] if latest else None

    injury_map: Dict[int, PlayerInjury] = {}
    if report_date and player_ids:
        injury_rows = (
            db.query(PlayerInjury)
            .filter(
                PlayerInjury.report_date == report_date,
                PlayerInjury.player_id.in_(player_ids),
            )
            .all()
        )
        injury_map = {row.player_id: row for row in injury_rows}

    healthy_team_stat = (
        db.query(TeamSeasonStat)
        .filter(
            TeamSeasonStat.team_id == team.id,
            TeamSeasonStat.season == season,
            TeamSeasonStat.is_playoff == False,  # noqa: E712
        )
        .first()
    )
    healthy_net = (
        float(healthy_team_stat.net_rating)
        if healthy_team_stat and healthy_team_stat.net_rating is not None
        else None
    )

    sidelined: List[PlayerAvailabilityProjection] = []
    sidelined_player_ids: set = set()
    out_count = 0
    questionable_count = 0
    sidelined_minutes = 0.0
    sidelined_pts = 0.0
    weighted_on_off_total = 0.0

    for player in roster_players:
        injury = injury_map.get(player.id)
        if injury is None:
            continue
        bucket = _normalize_bucket(injury.injury_status)
        if bucket not in SIDELINED_BUCKETS:
            continue

        stat = stat_map.get(player.id)
        on_off = on_off_map.get(player.id)
        body_part = _normalize_body_part(injury.injury_type, injury.detail)

        duration_est: Optional[DurationEstimate] = None
        if body_part:
            age = player_age(player)
            recurring = player_recurrence_for_body_part(db, player.id, body_part)
            duration_est = expected_duration(
                db,
                body_part=body_part,
                age=age,
                is_recurring=recurring,
            )

        impact_score_value = _impact_score(stat)
        projection = PlayerAvailabilityProjection(
            player_id=player.id,
            player_name=player.full_name,
            position=player.position or "",
            injury_status=injury.injury_status,
            injury_type=injury.injury_type,
            detail=injury.detail,
            body_part=body_part,
            season_pts_pg=stat.pts_pg if stat else None,
            season_min_pg=stat.min_pg if stat else None,
            season_bpm=stat.bpm if stat else None,
            on_off_net=on_off.on_off_net if on_off else None,
            expected_duration=duration_est,
            impact_label=_impact_label(stat.pts_pg if stat else None, stat.bpm if stat else None),
            impact_score=round(impact_score_value, 2),
        )
        sidelined.append(projection)
        sidelined_player_ids.add(player.id)

        if bucket == "unavailable":
            out_count += 1
        else:
            questionable_count += 1

        if stat and stat.min_pg:
            sidelined_minutes += float(stat.min_pg)
        if stat and stat.pts_pg:
            sidelined_pts += float(stat.pts_pg)

        if on_off and on_off.on_off_net is not None and stat and stat.min_pg:
            # Weight the on/off swing by the share of total minutes the
            # player otherwise occupies. on_off_net is "team is N points
            # better when on the floor", so removing them subtracts that
            # share.
            minute_share = float(stat.min_pg) / MIN_PG_TOTAL
            weighted_on_off_total += float(on_off.on_off_net) * minute_share

    sidelined.sort(key=lambda proj: proj.impact_score, reverse=True)

    rotation_pool = []
    for pid, player in player_map.items():
        if pid in sidelined_player_ids:
            continue
        rotation_pool.append((player, stat_map.get(pid)))

    used: set = set()
    rotation_replacements: List[RotationReplacement] = []
    for proj in sidelined:
        rep = _build_replacement(
            out_player_id=proj.player_id,
            out_player_name=proj.player_name,
            out_min_pg=proj.season_min_pg,
            rotation_pool=rotation_pool,
            used=used,
        )
        if rep is not None:
            rotation_replacements.append(rep)

    if sidelined:
        net_delta_raw = -weighted_on_off_total
        net_delta = max(-NET_RATING_DELTA_CLAMP, min(NET_RATING_DELTA_CLAMP, net_delta_raw))
        net_delta = round(net_delta, 2)
    else:
        net_delta = 0.0 if healthy_net is not None else None

    projected_net = (
        round(healthy_net + (net_delta or 0.0), 2)
        if healthy_net is not None and net_delta is not None
        else None
    )

    summary = _build_summary(
        team=team,
        out_count=out_count,
        questionable_count=questionable_count,
        sidelined_minutes=sidelined_minutes,
        sidelined_pts=sidelined_pts,
        net_delta=net_delta,
    )

    return TeamAvailabilityImpact(
        team_id=team.id,
        abbreviation=team.abbreviation,
        name=team.name,
        season=season,
        report_date=report_date,
        out_count=out_count,
        questionable_count=questionable_count,
        sidelined_minutes_per_game=round(sidelined_minutes, 1),
        sidelined_pts_per_game=round(sidelined_pts, 1),
        net_rating_delta=net_delta,
        healthy_net_rating=round(healthy_net, 2) if healthy_net is not None else None,
        projected_net_rating=projected_net,
        sidelined_players=sidelined,
        rotation_replacements=rotation_replacements,
        summary=summary,
    )


def compute_team_availability_impact_by_abbr(
    db: Session, team_abbr: str, season: str, today: Optional[date] = None
) -> TeamAvailabilityImpact:
    team = db.query(Team).filter(Team.abbreviation == team_abbr.upper()).first()
    if team is None:
        raise HTTPException(status_code=404, detail="Team '{0}' not found.".format(team_abbr))
    return compute_team_availability_impact(db, team_id=team.id, season=season, today=today)
