from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import Player, PlayerInjury, SeasonStat, Team
from models.team import (
    TeamAvailabilityPlayer,
    TeamAvailabilityResponse,
)
from services.schedule_service import get_next_game_for_team


def _normalize_bucket(status: Optional[str]) -> str:
    normalized = (status or "").strip().lower()
    if not normalized:
        return "available"
    if "avail" in normalized:
        return "available"
    if "prob" in normalized:
        return "probable"
    if (
        "doubt" in normalized
        or "quest" in normalized
        or "gtd" in normalized
        or "day-to-day" in normalized
        or "day to day" in normalized
    ):
        return "questionable"
    if "out" in normalized or "inactive" in normalized or "suspend" in normalized:
        return "unavailable"
    return "questionable"


def _impact_score(pts_pg: Optional[float], bpm: Optional[float]) -> float:
    return float(pts_pg or 0.0) + (max(float(bpm or 0.0), 0.0) * 2.0)


def _impact_label(pts_pg: Optional[float], bpm: Optional[float]) -> str:
    if (pts_pg or 0.0) >= 18.0 or (bpm or 0.0) >= 4.0:
        return "high impact"
    if (pts_pg or 0.0) >= 11.0 or (bpm or 0.0) >= 1.5:
        return "core rotation"
    return "depth piece"


def _pick_best_stat_rows(
    rows: List[SeasonStat],
    team_abbreviation: str,
) -> Dict[int, SeasonStat]:
    best: Dict[int, SeasonStat] = {}
    for row in rows:
        current = best.get(row.player_id)
        candidate_rank = (
            1 if row.team_abbreviation == team_abbreviation else 0,
            row.gp or 0,
            row.pts_pg or 0.0,
        )
        if current is None:
            best[row.player_id] = row
            continue
        current_rank = (
            1 if current.team_abbreviation == team_abbreviation else 0,
            current.gp or 0,
            current.pts_pg or 0.0,
        )
        if candidate_rank > current_rank:
            best[row.player_id] = row
    return best


def _serialize_player(
    player: Player,
    injury: PlayerInjury,
    stat: Optional[SeasonStat],
) -> TeamAvailabilityPlayer:
    return TeamAvailabilityPlayer(
        player_id=player.id,
        player_name=player.full_name,
        position=player.position or "",
        jersey=player.jersey or "",
        headshot_url=player.headshot_url or "",
        injury_status=injury.injury_status,
        injury_type=injury.injury_type,
        detail=injury.detail,
        comment=injury.comment,
        return_date=injury.return_date,
        pts_pg=stat.pts_pg if stat else None,
        bpm=stat.bpm if stat else None,
        impact_label=_impact_label(stat.pts_pg if stat else None, stat.bpm if stat else None),
    )


def _sort_players(players: List[TeamAvailabilityPlayer]) -> List[TeamAvailabilityPlayer]:
    return sorted(
        players,
        key=lambda player: (
            -_impact_score(player.pts_pg, player.bpm),
            player.player_name,
        ),
    )


def _overall_status(
    report_date: Optional[date],
    unavailable_players: List[TeamAvailabilityPlayer],
    questionable_players: List[TeamAvailabilityPlayer],
    probable_players: List[TeamAvailabilityPlayer],
) -> str:
    if report_date is None:
        return "unknown"
    if unavailable_players and (
        len(unavailable_players) >= 2
        or unavailable_players[0].impact_label == "high impact"
    ):
        return "shorthanded"
    if unavailable_players or questionable_players or probable_players:
        return "monitor"
    return "healthy"


def _summary_text(
    season: str,
    report_date: Optional[date],
    unavailable_players: List[TeamAvailabilityPlayer],
    questionable_players: List[TeamAvailabilityPlayer],
    probable_players: List[TeamAvailabilityPlayer],
) -> str:
    if report_date is None:
        return "No synced injury report is available for {0}; treat availability as unverified.".format(season)
    if not unavailable_players and not questionable_players and not probable_players:
        return "No active injury flags on the latest report."

    parts: List[str] = []
    if unavailable_players:
        parts.append("{0} unavailable".format(len(unavailable_players)))
    if questionable_players:
        parts.append("{0} questionable/doubtful".format(len(questionable_players)))
    if probable_players:
        parts.append("{0} probable".format(len(probable_players)))

    key_names = [player.player_name for player in unavailable_players[:2]]
    if not key_names:
        key_names = [player.player_name for player in questionable_players[:2]]
    if key_names:
        parts.append("Key names: {0}".format(", ".join(key_names)))

    return "; ".join(parts) + "."


def build_team_availability(
    db: Session,
    abbr: str,
    season: str,
    today: Optional[date] = None,
) -> TeamAvailabilityResponse:
    team = db.query(Team).filter(Team.abbreviation == abbr.upper()).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team '{0}' not found.".format(abbr))

    roster_players = (
        db.query(Player)
        .filter(Player.team_id == team.id, Player.is_active == True)  # noqa: E712
        .order_by(Player.last_name.asc(), Player.first_name.asc(), Player.full_name.asc())
        .all()
    )
    player_ids = [player.id for player in roster_players]

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

    latest_report = (
        db.query(PlayerInjury.report_date)
        .filter(PlayerInjury.season == season)
        .order_by(PlayerInjury.report_date.desc())
        .first()
    )
    report_date = latest_report[0] if latest_report else None

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

    unavailable_players: List[TeamAvailabilityPlayer] = []
    questionable_players: List[TeamAvailabilityPlayer] = []
    probable_players: List[TeamAvailabilityPlayer] = []

    for player in roster_players:
        injury = injury_map.get(player.id)
        if not injury:
            continue
        serialized = _serialize_player(player, injury, stat_map.get(player.id))
        bucket = _normalize_bucket(injury.injury_status)
        if bucket == "unavailable":
            unavailable_players.append(serialized)
        elif bucket == "probable":
            probable_players.append(serialized)
        elif bucket == "available":
            continue
        else:
            questionable_players.append(serialized)

    unavailable_players = _sort_players(unavailable_players)
    questionable_players = _sort_players(questionable_players)
    probable_players = _sort_players(probable_players)
    key_absences = unavailable_players[:3] if unavailable_players else questionable_players[:3]

    unavailable_count = len(unavailable_players)
    questionable_count = len(questionable_players)
    probable_count = len(probable_players)
    available_count = max(
        len(roster_players) - unavailable_count - questionable_count - probable_count,
        0,
    )

    return TeamAvailabilityResponse(
        team_id=team.id,
        abbreviation=team.abbreviation,
        name=team.name,
        season=season,
        report_date=report_date,
        overall_status=_overall_status(
            report_date,
            unavailable_players,
            questionable_players,
            probable_players,
        ),
        summary=_summary_text(
            season,
            report_date,
            unavailable_players,
            questionable_players,
            probable_players,
        ),
        available_count=available_count,
        unavailable_count=unavailable_count,
        questionable_count=questionable_count,
        probable_count=probable_count,
        next_game=get_next_game_for_team(db, team=team, season=season, today=today),
        key_absences=key_absences,
        unavailable_players=unavailable_players,
        questionable_players=questionable_players,
        probable_players=probable_players,
    )
