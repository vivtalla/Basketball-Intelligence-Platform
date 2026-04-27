from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import Player, SeasonStat, Team
from models.team_fit import (
    AlternativeTeamFit,
    CurrentTeamFit,
    FitDriver,
    OverlapFlag,
    TeamFitMethodology,
    TeamFitResponse,
)
from services.intel_math import clamp
from services.similarity_service import (
    MIN_GP,
    SIMILARITY_STATS_V2,
    TEAM_FIT_FEATURE_LABELS,
    _TEAM_FIT_DUPLICATE_THRESHOLD,
    _TEAM_FIT_PENALTY,
    _qualified_rows_v2,
    _raw_z,
    _season_norms_v2,
)


METHODOLOGY_VERSION = "team_fit_v2"
BETTER_FIT_DELTA_THRESHOLD = 5.0
MIN_TEAM_PLAYERS = 3

WEIGHTS: Dict[str, float] = {
    "value_supplied": 0.45,
    "teammate_overlap": 0.30,
    "role_runway": 0.25,
}

ROLE_FEATURES = [
    "usg_pct",
    "pts_pg",
    "ast_pg",
    "par3",
    "ftr",
    "stl_pg",
    "blk_pg",
    "reb_pg",
]

POSITION_BUCKET_MAP: Dict[str, str] = {
    "pg": "G",
    "sg": "G",
    "g": "G",
    "guard": "G",
    "sf": "F",
    "pf": "F",
    "f": "F",
    "forward": "F",
    "c": "C",
    "center": "C",
}


def _methodology() -> TeamFitMethodology:
    return TeamFitMethodology(
        version=METHODOLOGY_VERSION,
        weights=WEIGHTS,
        duplicate_threshold=_TEAM_FIT_DUPLICATE_THRESHOLD,
        duplicate_penalty=_TEAM_FIT_PENALTY,
        min_games=MIN_GP,
        min_team_players=MIN_TEAM_PLAYERS,
        better_fit_delta_threshold=BETTER_FIT_DELTA_THRESHOLD,
        notes=[
            "Team fit is deterministic roster fit only; salary, contracts, trade assets, injuries, and projections are excluded.",
            "Player and roster features use the same 13 z-scored role features as Team-Fit similarity mode.",
            "A feature is teammate-covered when the player and a teammate are within 0.5 z-score on that feature; covered features receive the Sprint 68 0.4x duplicate penalty.",
            "V2 exposes skill supply, roster need, role competition, and confidence so the score can be audited instead of treated as a black box.",
            "Alternative teams are ranked by roster gaps filled, lower role competition, and position-bucket runway against same-season rosters.",
        ],
    )


def _position_bucket(position: Optional[str]) -> str:
    if not position:
        return "other"
    cleaned = position.lower().strip().replace("/", "-")
    primary = cleaned.split("-", 1)[0].strip()
    return POSITION_BUCKET_MAP.get(primary, "other")


def _season_start(season: str) -> int:
    try:
        return int((season or "").split("-", 1)[0])
    except (TypeError, ValueError):
        return 0


def _latest_qualified_player_season(
    rows: List[SeasonStat],
    player_id: int,
    requested_season: str,
) -> Optional[str]:
    requested_start = _season_start(requested_season)
    seasons = {
        row.season
        for row in rows
        if row.player_id == player_id
        and (requested_start == 0 or _season_start(row.season) <= requested_start)
    }
    if not seasons:
        return None
    return sorted(seasons, key=_season_start, reverse=True)[0]


def _resolve_subject_row(
    rows: List[SeasonStat],
    player_id: int,
    season: str,
) -> Tuple[Optional[SeasonStat], List[str]]:
    warnings: List[str] = []
    player_rows = [
        r for r in rows
        if r.player_id == player_id and r.season == season and not r.is_playoff
    ]
    if not player_rows:
        return None, warnings

    non_tot = [r for r in player_rows if (r.team_abbreviation or "").upper() != "TOT"]
    if non_tot:
        non_tot.sort(key=lambda r: (float(r.min_pg or 0.0), int(r.gp or 0)), reverse=True)
        return non_tot[0], warnings

    player_rows.sort(key=lambda r: (float(r.min_pg or 0.0), int(r.gp or 0)), reverse=True)
    warnings.append(
        "Selected season only has a TOT row for this player, so current-team fit cannot be scored."
    )
    return player_rows[0], warnings


def _team_rows(rows: List[SeasonStat], season: str) -> Dict[str, List[SeasonStat]]:
    by_team: Dict[str, List[SeasonStat]] = defaultdict(list)
    for row in rows:
        team = (row.team_abbreviation or "").upper()
        if row.season == season and team and team != "TOT":
            by_team[team].append(row)
    return by_team


def _feature_team_best(
    roster: List[SeasonStat],
    norms: Dict[str, Dict[str, Dict[str, float]]],
    exclude_player_id: Optional[int] = None,
) -> Dict[str, float]:
    best: Dict[str, float] = {}
    for row in roster:
        if exclude_player_id is not None and row.player_id == exclude_player_id:
            continue
        raw = _raw_z(row, norms)
        if raw is None:
            continue
        for key, value in raw.items():
            if key not in best or value > best[key]:
                best[key] = value
    return best


def _team_overlap_flags(
    db: Session,
    subject_row: SeasonStat,
    roster: List[SeasonStat],
    norms: Dict[str, Dict[str, Dict[str, float]]],
) -> List[OverlapFlag]:
    subject_z = _raw_z(subject_row, norms) or {}
    closest: Dict[str, Tuple[float, SeasonStat, float]] = {}

    for row in roster:
        if row.player_id == subject_row.player_id:
            continue
        teammate_z = _raw_z(row, norms)
        if teammate_z is None:
            continue
        for key, _weight in SIMILARITY_STATS_V2:
            subj = subject_z.get(key)
            tm = teammate_z.get(key)
            if subj is None or tm is None:
                continue
            gap = abs(subj - tm)
            if gap >= _TEAM_FIT_DUPLICATE_THRESHOLD:
                continue
            current = closest.get(key)
            if current is None or gap < current[0]:
                closest[key] = (gap, row, tm)

    teammate_ids = [row.player_id for _gap, row, _tm_z in closest.values()]
    names = {
        p.id: p.full_name
        for p in db.query(Player).filter(Player.id.in_(teammate_ids)).all()
    } if teammate_ids else {}

    flags: List[OverlapFlag] = []
    for key, (gap, row, teammate_z) in closest.items():
        flags.append(
            OverlapFlag(
                feature_key=key,
                label=TEAM_FIT_FEATURE_LABELS.get(key, key),
                teammate_id=row.player_id,
                teammate_name=names.get(row.player_id, str(row.player_id)),
                player_z=round(float(subject_z[key]), 3),
                teammate_z=round(float(teammate_z), 3),
                gap=round(float(gap), 3),
                multiplier=_TEAM_FIT_PENALTY,
            )
        )
    flags.sort(key=lambda f: (f.gap, f.label))
    return flags


def _driver_summary(label: str, need: float) -> str:
    if need >= 1.0:
        return "{0} is a clear roster gap this player can cover.".format(label)
    return "{0} is thinner on this roster than in the player's profile.".format(label)


def _build_drivers(
    subject_z: Dict[str, float],
    team_best: Dict[str, float],
    feature_keys: List[str],
    limit: int,
) -> List[FitDriver]:
    drivers: List[FitDriver] = []
    for key in feature_keys:
        player_z = float(subject_z.get(key, 0.0))
        if player_z <= 0.25:
            continue
        best_z = float(team_best.get(key, 0.0))
        need = clamp(player_z - max(0.0, best_z), 0.0, 2.0)
        if need <= 0.2:
            continue
        contribution = clamp((player_z * 0.55) + (need * 0.45), 0.0, 2.0)
        label = TEAM_FIT_FEATURE_LABELS.get(key, key)
        drivers.append(
            FitDriver(
                feature_key=key,
                label=label,
                player_z=round(player_z, 3),
                team_need_z=round(need, 3),
                contribution=round(contribution, 3),
                summary=_driver_summary(label, need),
            )
        )
    drivers.sort(key=lambda d: d.contribution, reverse=True)
    return drivers[:limit]


def _bucket_runway_bonus(
    player: Player,
    subject_row: SeasonStat,
    roster: List[SeasonStat],
    player_lookup: Dict[int, Player],
) -> float:
    bucket = _position_bucket(player.position)
    if bucket == "other":
        return 0.0
    same_bucket = [
        row for row in roster
        if row.player_id != subject_row.player_id
        and _position_bucket(player_lookup.get(row.player_id).position if player_lookup.get(row.player_id) else None) == bucket
    ]
    if len(same_bucket) <= 1:
        return 0.35
    subject_minutes = float(subject_row.min_pg or 0.0)
    top_minutes = max(float(row.min_pg or 0.0) for row in same_bucket)
    if subject_minutes >= top_minutes + 4.0:
        return 0.25
    return 0.0


def _score_team_fit(
    db: Session,
    player: Player,
    subject_row: SeasonStat,
    roster: List[SeasonStat],
    norms: Dict[str, Dict[str, Dict[str, float]]],
    player_lookup: Dict[int, Player],
) -> Tuple[float, float, float, float, List[FitDriver], List[FitDriver], List[OverlapFlag]]:
    subject_z = _raw_z(subject_row, norms) or {}
    team_best = _feature_team_best(roster, norms, exclude_player_id=subject_row.player_id)
    overlap_flags = _team_overlap_flags(db, subject_row, roster, norms)
    overlap_keys = {flag.feature_key for flag in overlap_flags}

    value_drivers = _build_drivers(subject_z, team_best, list(dict(SIMILARITY_STATS_V2).keys()), 4)
    role_drivers = _build_drivers(subject_z, team_best, ROLE_FEATURES, 4)

    value_signal = sum(d.contribution for d in value_drivers) / float(len(value_drivers) or 1)
    role_signal = sum(d.contribution for d in role_drivers) / float(len(role_drivers) or 1)
    role_signal += _bucket_runway_bonus(player, subject_row, roster, player_lookup)

    unique_feature_count = len(set(key for key, _weight in SIMILARITY_STATS_V2))
    overlap_ratio = len(overlap_keys) / float(unique_feature_count or 1)
    overlap_score = clamp(100.0 - (overlap_ratio * 72.0), 0.0, 100.0)
    value_score = clamp(45.0 + (value_signal * 27.5), 0.0, 100.0)
    role_score = clamp(45.0 + (role_signal * 27.5), 0.0, 100.0)

    fit_score = (
        value_score * WEIGHTS["value_supplied"]
        + overlap_score * WEIGHTS["teammate_overlap"]
        + role_score * WEIGHTS["role_runway"]
    )
    return (
        round(fit_score, 1),
        round(value_score, 1),
        round(overlap_score, 1),
        round(role_score, 1),
        value_drivers,
        role_drivers,
        overlap_flags,
    )


def _confidence_for_team(roster: List[SeasonStat], drivers: List[FitDriver], warnings: List[str]) -> Tuple[str, List[str]]:
    notes: List[str] = []
    if len(roster) >= 8:
        notes.append("{0} qualified roster rows support the fit read.".format(len(roster)))
        confidence = "high"
    elif len(roster) >= MIN_TEAM_PLAYERS:
        notes.append("{0} qualified roster rows; treat the fit read as directional.".format(len(roster)))
        confidence = "medium"
    else:
        notes.append("Roster sample is below the Team-Fit minimum.")
        confidence = "low"
    if not drivers:
        notes.append("No dominant roster-gap driver cleared the v2 explanation threshold.")
        confidence = "medium" if confidence == "high" else confidence
    if warnings:
        notes.append("Season fallback or data warnings are active.")
        confidence = "medium" if confidence == "high" else confidence
    return confidence, notes


def _current_summary(team: str, score: float, drivers: List[FitDriver], overlaps: List[OverlapFlag]) -> str:
    if drivers and overlaps:
        return "{0} fit is {1:.1f}: strongest unlocked value is {2}, while {3} is already teammate-covered.".format(
            team,
            score,
            drivers[0].label.lower(),
            overlaps[0].label.lower(),
        )
    if drivers:
        return "{0} fit is {1:.1f}: the clearest value add is {2}.".format(
            team,
            score,
            drivers[0].label.lower(),
        )
    if overlaps:
        return "{0} fit is {1:.1f}: overlap is the main story, led by {2}.".format(
            team,
            score,
            overlaps[0].label.lower(),
        )
    return "{0} fit is {1:.1f}: no single role feature dominates the fit read.".format(team, score)


def _alternative_label(delta: float) -> str:
    if delta >= BETTER_FIT_DELTA_THRESHOLD:
        return "better_fit"
    if abs(delta) < BETTER_FIT_DELTA_THRESHOLD:
        return "similar_fit"
    return "different_fit"


def _alternative_summary(team: str, label: str, delta: float, drivers: List[FitDriver]) -> str:
    if label == "better_fit":
        prefix = "{0} grades {1:.1f} points better than the current team".format(team, delta)
    elif label == "similar_fit":
        prefix = "{0} is a similar basketball fit".format(team)
    else:
        prefix = "{0} is a different but lower-scoring basketball fit".format(team)
    if drivers:
        return "{0}, mainly because of {1} runway.".format(prefix, drivers[0].label.lower())
    return "{0}, with no single dominant gap-driver.".format(prefix)


def build_team_fit_report(
    db: Session,
    player_id: int,
    season: str,
    limit: int = 5,
) -> TeamFitResponse:
    player = db.query(Player).filter(Player.id == player_id).first()
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found.")

    all_rows = _qualified_rows_v2(db)
    norms = _season_norms_v2(all_rows)
    effective_season = season
    warnings: List[str] = []
    if not any(r.player_id == player_id and r.season == season for r in all_rows):
        fallback = _latest_qualified_player_season(all_rows, player_id, season)
        if fallback is not None:
            warnings.append(
                "{0} is not qualified for Team-Fit yet, so this panel is using the latest qualified season: {1}.".format(
                    season,
                    fallback,
                )
            )
            effective_season = fallback

    subject_row, row_warnings = _resolve_subject_row(all_rows, player_id, effective_season)
    warnings.extend(row_warnings)
    if subject_row is None:
        raise HTTPException(
            status_code=404,
            detail="No qualified regular-season row found for player {0} in {1}.".format(player_id, season),
        )

    player_ids = list({row.player_id for row in all_rows})
    player_lookup = {
        p.id: p for p in db.query(Player).filter(Player.id.in_(player_ids)).all()
    } if player_ids else {}
    teams = {
        t.abbreviation: t.name
        for t in db.query(Team).all()
    }

    by_team = _team_rows(all_rows, effective_season)
    current_abbr = (subject_row.team_abbreviation or "").upper()
    current_team: Optional[CurrentTeamFit] = None
    current_score: Optional[float] = None

    if not current_abbr or current_abbr == "TOT":
        warnings.append("Current team could not be resolved, so team-fit scoring was skipped.")
    else:
        current_roster = by_team.get(current_abbr, [])
        if len(current_roster) < MIN_TEAM_PLAYERS:
            warnings.append(
                "{0} has only {1} qualified roster rows, below the {2}-player team-fit minimum.".format(
                    current_abbr,
                    len(current_roster),
                    MIN_TEAM_PLAYERS,
                )
            )
        else:
            (
                score,
                value_score,
                overlap_score,
                role_score,
                value_drivers,
                role_drivers,
                overlaps,
            ) = _score_team_fit(db, player, subject_row, current_roster, norms, player_lookup)
            confidence, confidence_notes = _confidence_for_team(current_roster, value_drivers or role_drivers, warnings)
            current_score = score
            current_team = CurrentTeamFit(
                team_abbreviation=current_abbr,
                fit_score=score,
                value_supplied_score=value_score,
                teammate_overlap_score=overlap_score,
                role_runway_score=role_score,
                skill_supply_score=value_score,
                roster_need_score=role_score,
                role_competition_score=overlap_score,
                confidence=confidence,
                confidence_notes=confidence_notes,
                summary=_current_summary(current_abbr, score, value_drivers, overlaps),
                value_drivers=value_drivers,
                role_runway_drivers=role_drivers,
                overlap_flags=overlaps,
            )

    alternatives: List[AlternativeTeamFit] = []
    if current_score is not None:
        for team_abbr, roster in by_team.items():
            if team_abbr == current_abbr:
                continue
            if len(roster) < MIN_TEAM_PLAYERS:
                continue
            (
                score,
                value_score,
                overlap_score,
                role_score,
                value_drivers,
                role_drivers,
                overlaps,
            ) = _score_team_fit(db, player, subject_row, roster, norms, player_lookup)
            delta = round(score - current_score, 1)
            label = _alternative_label(delta)
            confidence, confidence_notes = _confidence_for_team(roster, value_drivers or role_drivers, warnings)
            alternatives.append(
                AlternativeTeamFit(
                    team_abbreviation=team_abbr,
                    team_name=teams.get(team_abbr),
                    fit_score=score,
                    score_delta_vs_current=delta,
                    label=label,
                    skill_supply_score=value_score,
                    roster_need_score=role_score,
                    role_competition_score=overlap_score,
                    confidence=confidence,
                    confidence_notes=confidence_notes,
                    summary=_alternative_summary(team_abbr, label, delta, role_drivers or value_drivers),
                    value_drivers=value_drivers,
                    role_runway_drivers=role_drivers,
                    overlap_flags=overlaps,
                )
            )
        alternatives.sort(key=lambda row: (row.fit_score, row.score_delta_vs_current), reverse=True)

    return TeamFitResponse(
        player_id=player_id,
        player_name=player.full_name,
        season=effective_season,
        current_team=current_team,
        alternative_teams=alternatives[:max(0, min(limit, 10))],
        methodology=_methodology(),
        warnings=warnings,
    )
