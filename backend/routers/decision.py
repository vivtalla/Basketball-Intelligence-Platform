from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from data.cache import CacheManager
from db.database import get_db
from db.models import GamePlayerStat, GameTeamStat, LineupStats, PlayByPlayEvent, Player, Team, WarehouseGame
from models.decision import (
    FollowThroughGame,
    FollowThroughRequest,
    FollowThroughResponse,
    LineupImpactFilters,
    LineupImpactResponse,
    LineupImpactRow,
    MatchupFlag,
    MatchupFlagEvidence,
    MatchupFlagsResponse,
    PlayTypeEVFilters,
    PlayTypeEVResponse,
    PlayTypeEVRow,
    PlayTypeFlag,
)
from routers.styles import build_team_style_profile
from services.compare_service import build_team_comparison_report
from services.team_focus_service import build_team_focus_levers_report
from services.team_rotation_service import build_team_rotation_report

router = APIRouter()
follow_router = APIRouter()


_ACTION_FAMILIES: List[Tuple[str, str]] = [
    ("transition", "Transition"),
    ("rim_pressure", "Rim Pressure"),
    ("perimeter_creation", "Perimeter Creation"),
    ("post_mismatch", "Post Mismatch"),
    ("handoff_pnr", "Handoff / P&R"),
    ("spot_up", "Spot-Up"),
    ("late_clock_bailout", "Late-Clock Bailout"),
    ("misc", "Miscellaneous"),
]


def _safe_round(value: Optional[float], digits: int = 2) -> Optional[float]:
    if value is None:
        return None
    return round(value, digits)


def _safe_div(numerator: float, denominator: float) -> Optional[float]:
    if denominator <= 0:
        return None
    return numerator / denominator


def _fetch_team(db: Session, abbr: str) -> Team:
    team = db.query(Team).filter(Team.abbreviation == abbr.upper()).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team '{0}' not found.".format(abbr))
    return team


def _season_watermark(db: Session, season: str) -> str:
    values = [
        db.query(func.max(LineupStats.updated_at)).filter(LineupStats.season == season).scalar(),
        db.query(func.max(GameTeamStat.updated_at)).filter(GameTeamStat.season == season).scalar(),
        db.query(func.max(PlayByPlayEvent.updated_at)).filter(PlayByPlayEvent.season == season).scalar(),
    ]
    watermark = max([value for value in values if value is not None], default=None)
    return watermark.isoformat() if watermark else "none"


def _lineup_player_names(db: Session, lineup_key: str) -> Tuple[List[int], List[str]]:
    player_ids = [int(pid) for pid in lineup_key.split("-") if pid]
    roster = db.query(Player).filter(Player.id.in_(player_ids)).all()
    name_map = {player.id: player.full_name for player in roster}
    player_names = [name_map.get(player_id, str(player_id)) for player_id in player_ids]
    return player_ids, player_names


def _possessions_for_team_row(row: GameTeamStat) -> Optional[float]:
    possessions = float(row.fga or 0) - float(row.oreb or 0) + float(row.tov or 0) + (0.44 * float(row.fta or 0))
    if possessions <= 0:
        return None
    return possessions


def _infer_action_family(event: PlayByPlayEvent, fallback: str = "misc") -> str:
    desc = (event.description or "").lower()
    clock = event.clock or ""

    if event.action_type == "freethrow":
        if clock and clock.endswith("S") and any(token in desc for token in ["and-1", "foul", "shooting"]):
            return "rim_pressure"
        return "rim_pressure"
    if any(token in desc for token in ["fast break", "transition", "runout", "leak out", "leak-out"]):
        return "transition"
    if any(token in desc for token in ["pick and roll", "pnr", "handoff", "screen", "roll"]):
        return "handoff_pnr"
    if any(token in desc for token in ["corner", "catch and shoot", "catch-and-shoot", "spot up", "spot-up"]):
        return "spot_up"
    if any(token in desc for token in ["post", "hook", "turnaround", "back to basket"]):
        return "post_mismatch"
    if any(token in desc for token in ["drive", "driving", "layup", "dunk", "rim", "paint"]):
        return "rim_pressure"
    if any(token in desc for token in ["pullup", "pull-up", "stepback", "iso", "isolation", "midrange"]):
        return "perimeter_creation"
    if clock and clock.startswith("PT0") and any(token in desc for token in ["shot clock", "late", "buzzer"]):
        return "late_clock_bailout"
    if event.action_type == "turnover":
        if any(token in desc for token in ["bad pass", "lost ball", "steal", "offensive foul"]):
            return fallback
        return fallback
    if event.action_type == "2pt":
        return "rim_pressure"
    if event.action_type == "3pt":
        return "spot_up"
    return fallback


def _lineup_row_payload(
    db: Session,
    row: LineupStats,
    team_baseline_net: Optional[float],
    team_pace: Optional[float],
    minute_delta: float,
    confidence: str,
) -> LineupImpactRow:
    player_ids, player_names = _lineup_player_names(db, row.lineup_key)
    observed_net = row.net_rating
    shrink_weight = None
    shrunk_net = observed_net
    if observed_net is not None and team_baseline_net is not None and row.possessions is not None:
        shrink_weight = row.possessions / float(row.possessions + 150.0)
        shrunk_net = (observed_net * shrink_weight) + (team_baseline_net * (1.0 - shrink_weight))
    elif team_baseline_net is not None:
        shrunk_net = team_baseline_net
    expected_points_per_100 = shrunk_net
    expected_points_per_game = None
    if shrunk_net is not None and team_pace is not None:
        possessions_delta = (team_pace / 48.0) * abs(minute_delta)
        expected_points_per_game = ((shrunk_net - (team_baseline_net or 0.0)) / 100.0) * possessions_delta

    evidence = [
        "{0} possessions".format(row.possessions or 0),
        "{0:.1f} minutes".format(row.minutes or 0.0),
    ]
    if shrink_weight is not None:
        evidence.append("Shrinkage weight {0:.2f}".format(shrink_weight))
    return LineupImpactRow(
        lineup_key=row.lineup_key,
        player_ids=player_ids,
        player_names=player_names,
        minutes=_safe_round(row.minutes, 1),
        possessions=row.possessions,
        observed_net_rating=_safe_round(observed_net, 2),
        shrunk_net_rating=_safe_round(shrunk_net, 2),
        expected_points_per_100=_safe_round(expected_points_per_100, 2),
        expected_points_per_game=_safe_round(expected_points_per_game, 2),
        minute_delta=_safe_round(minute_delta, 1),
        confidence=confidence,  # type: ignore[arg-type]
        evidence=evidence,
    )


def build_lineup_impact_report(
    db: Session,
    team_abbr: str,
    season: str,
    opponent_abbr: Optional[str],
    window_games: int,
    min_possessions: int,
) -> LineupImpactResponse:
    team = _fetch_team(db, team_abbr)
    opponent = _fetch_team(db, opponent_abbr) if opponent_abbr else None
    watermark = _season_watermark(db, season)
    cache_key = "lineup_impact:{0}:{1}:{2}:{3}:{4}:{5}".format(
        team.abbreviation,
        season,
        opponent.abbreviation if opponent else "none",
        window_games,
        min_possessions,
        watermark,
    )
    cached = CacheManager.get(cache_key)
    if cached:
        return LineupImpactResponse(**cached)

    style_report = build_team_style_profile(db=db, abbr=team.abbreviation, season=season, window=window_games, opponent_abbr=opponent_abbr)
    team_baseline_net = next((row.team_value for row in style_report.current_profile if row.metric_id == "net_rating"), None)
    team_pace = next((row.team_value for row in style_report.current_profile if row.metric_id == "pace"), None)

    lineup_rows = (
        db.query(LineupStats)
        .filter(
            LineupStats.season == season,
            LineupStats.team_id == team.id,
            LineupStats.minutes.isnot(None),
            LineupStats.possessions >= min_possessions,
        )
        .order_by(LineupStats.minutes.desc(), LineupStats.net_rating.desc().nullslast())
        .all()
    )
    warnings: List[str] = []
    if len(lineup_rows) < 5:
        warnings.append("Only {0} qualifying lineups were found, so this read is directional only.".format(len(lineup_rows)))

    if not lineup_rows:
        response = LineupImpactResponse(
            team_abbreviation=team.abbreviation,
            season=season,
            filters=LineupImpactFilters(
                season=season,
                opponent_abbreviation=opponent.abbreviation if opponent else None,
                window_games=window_games,
                min_possessions=min_possessions,
            ),
            current_rotation=[],
            recommended_rotation=[],
            lineup_rows=[],
            impact_summary="No qualifying lineups were found for the selected filters.",
            confidence="low",
            warnings=warnings,
        )
        CacheManager.set(cache_key, response.model_dump(), 300)
        return response

    row_payloads: List[LineupImpactRow] = []
    for row in lineup_rows:
        minute_delta = 5.0
        confidence = "high" if (row.possessions or 0) >= 200 else "medium" if (row.possessions or 0) >= 80 else "low"
        payload = _lineup_row_payload(db, row, team_baseline_net, team_pace, minute_delta, confidence)
        row_payloads.append(payload)

    ranked_rows = sorted(
        row_payloads,
        key=lambda item: item.expected_points_per_game if item.expected_points_per_game is not None else -9999.0,
        reverse=True,
    )
    current_rotation = sorted(row_payloads, key=lambda item: item.minutes or 0.0, reverse=True)[:5]
    recommended_rotation: List[LineupImpactRow] = []
    for row in ranked_rows[:5]:
        minute_delta = 5.0 if (row.expected_points_per_game or 0.0) >= 0 else -5.0
        recommended_rotation.append(
            LineupImpactRow(
                lineup_key=row.lineup_key,
                player_ids=row.player_ids,
                player_names=row.player_names,
                minutes=row.minutes,
                possessions=row.possessions,
                observed_net_rating=row.observed_net_rating,
                shrunk_net_rating=row.shrunk_net_rating,
                expected_points_per_100=row.expected_points_per_100,
                expected_points_per_game=row.expected_points_per_game,
                minute_delta=_safe_round(minute_delta, 1),
                confidence=row.confidence,
                evidence=row.evidence,
            )
        )

    best_row = ranked_rows[0]
    worst_row = ranked_rows[-1]
    impact_summary = "The strongest lineup is {0}, while {1} looks like the clearest minute candidate to trim.".format(
        " · ".join(best_row.player_names[:3]),
        " · ".join(worst_row.player_names[:3]),
    )
    if opponent:
        impact_summary = "{0} Against {1}, the minute shift is most favorable when the high-end unit sees more run.".format(
            impact_summary,
            opponent.abbreviation,
        )

    confidence = "high" if len(lineup_rows) >= 10 and (lineup_rows[0].possessions or 0) >= 150 else "medium" if len(lineup_rows) >= 5 else "low"
    if opponent is None:
        warnings.append("No opponent-style context was provided, so the rotation guidance is season-context only.")
    if any(row.confidence == "low" for row in row_payloads[:3]):
        warnings.append("Some lineup rows are still sample-limited.")

    response = LineupImpactResponse(
        team_abbreviation=team.abbreviation,
        season=season,
        filters=LineupImpactFilters(
            season=season,
            opponent_abbreviation=opponent.abbreviation if opponent else None,
            window_games=window_games,
            min_possessions=min_possessions,
        ),
        current_rotation=current_rotation,
        recommended_rotation=recommended_rotation,
        lineup_rows=ranked_rows[:10],
        impact_summary=impact_summary,
        confidence=confidence,  # type: ignore[arg-type]
        warnings=warnings,
    )
    CacheManager.set(cache_key, response.model_dump(), 900)
    return response


def _family_row_notes(family: str) -> str:
    notes = dict(_ACTION_FAMILIES)
    return notes.get(family, family.replace("_", " ").title())


def build_play_type_ev_report(
    db: Session,
    team_abbr: str,
    season: str,
    opponent_abbr: Optional[str],
    window_games: int,
) -> PlayTypeEVResponse:
    team = _fetch_team(db, team_abbr)
    opponent = _fetch_team(db, opponent_abbr) if opponent_abbr else None
    watermark = _season_watermark(db, season)
    cache_key = "play_type_ev:{0}:{1}:{2}:{3}:{4}".format(
        team.abbreviation,
        season,
        opponent.abbreviation if opponent else "none",
        window_games,
        watermark,
    )
    cached = CacheManager.get(cache_key)
    if cached:
        return PlayTypeEVResponse(**cached)

    game_rows = (
        db.query(GameTeamStat, WarehouseGame)
        .join(WarehouseGame, WarehouseGame.game_id == GameTeamStat.game_id)
        .filter(GameTeamStat.season == season, GameTeamStat.team_id == team.id)
        .order_by(WarehouseGame.game_date.desc().nullslast(), GameTeamStat.game_id.desc())
        .all()
    )
    if opponent is not None:
        opponent_game_ids = {
            row.game_id
            for row, game in game_rows
            if game.home_team_id == opponent.id or game.away_team_id == opponent.id
        }
        game_rows = [(row, game) for row, game in game_rows if row.game_id in opponent_game_ids]

    if not game_rows:
        response = PlayTypeEVResponse(
            team_abbreviation=team.abbreviation,
            season=season,
            filters=PlayTypeEVFilters(
                season=season,
                opponent_abbreviation=opponent.abbreviation if opponent else None,
                window_games=window_games,
            ),
            action_rows=[],
            overused_flags=[],
            underused_flags=[],
            warnings=["No play-by-play coverage was found for the requested team and season."],
        )
        CacheManager.set(cache_key, response.model_dump(), 300)
        return response

    recent_game_ids = [row.game_id for row, _game in game_rows[:window_games]] if window_games else [row.game_id for row, _game in game_rows]
    events = (
        db.query(PlayByPlayEvent)
        .filter(PlayByPlayEvent.season == season, PlayByPlayEvent.game_id.in_(recent_game_ids), PlayByPlayEvent.team_id == team.id)
        .order_by(PlayByPlayEvent.game_id.asc(), PlayByPlayEvent.order_index.asc())
        .all()
    )

    family_stats: Dict[str, Dict[str, float]] = defaultdict(lambda: {"usage": 0.0, "points": 0.0, "turnovers": 0.0, "fouls": 0.0, "oreb": 0.0})
    total_usage = 0.0
    last_family_by_game: Dict[str, str] = {}
    for event in events:
        family = _infer_action_family(event, last_family_by_game.get(event.game_id, "misc"))
        desc = (event.description or "").lower()
        if event.action_type in {"2pt", "3pt", "freethrow"}:
            family_stats[family]["usage"] += 1.0
            total_usage += 1.0
            if event.sub_type == "made":
                family_stats[family]["points"] += 3.0 if event.action_type == "3pt" else 2.0 if event.action_type == "2pt" else 1.0
            if any(token in desc for token in ["foul", "and-1", "shooting"]):
                family_stats[family]["fouls"] += 1.0
            last_family_by_game[event.game_id] = family
        elif event.action_type == "turnover":
            family_stats[family]["turnovers"] += 1.0
            family_stats[family]["usage"] += 1.0
            total_usage += 1.0
        elif event.action_type == "rebound" and (event.sub_type or "").lower() == "offensive":
            family_stats[family]["oreb"] += 1.0

    if total_usage <= 0:
        response = PlayTypeEVResponse(
            team_abbreviation=team.abbreviation,
            season=season,
            filters=PlayTypeEVFilters(
                season=season,
                opponent_abbreviation=opponent.abbreviation if opponent else None,
                window_games=window_games,
            ),
            action_rows=[],
            overused_flags=[],
            underused_flags=[],
            warnings=["Could not infer any action-family usage for this team."],
        )
        CacheManager.set(cache_key, response.model_dump(), 300)
        return response

    rows: List[PlayTypeEVRow] = []
    raw_ev_values: List[float] = []
    for family, label in _ACTION_FAMILIES:
        stats = family_stats.get(family, {})
        usage = float(stats.get("usage", 0.0))
        points = float(stats.get("points", 0.0))
        turnovers = float(stats.get("turnovers", 0.0))
        fouls = float(stats.get("fouls", 0.0))
        oreb = float(stats.get("oreb", 0.0))
        if usage <= 0 and points <= 0 and turnovers <= 0 and fouls <= 0 and oreb <= 0:
            continue
        possessions = max(usage + turnovers, 1.0)
        ppp = points / possessions
        turnover_rate = turnovers / possessions
        foul_rate = fouls / possessions
        offensive_rebound_rate = oreb / possessions
        ev_score = ppp - turnover_rate + (0.2 * foul_rate) + (0.1 * offensive_rebound_rate)
        raw_ev_values.append(ev_score)
        rows.append(
            PlayTypeEVRow(
                action_family=family,
                label=label,
                usage_share=_safe_round(usage / total_usage, 3),
                points_per_possession=_safe_round(ppp, 3),
                turnover_rate=_safe_round(turnover_rate, 3),
                foul_rate=_safe_round(foul_rate, 3),
                offensive_rebound_rate=_safe_round(offensive_rebound_rate, 3),
                ev_score=_safe_round(ev_score, 3),
                league_percentile=None,
                note="{0} is inferred from play-by-play descriptions and shot/turnover outcomes.".format(label),
            )
        )

    rows.sort(key=lambda row: row.ev_score if row.ev_score is not None else -999.0, reverse=True)
    ev_values = [row.ev_score for row in rows if row.ev_score is not None]
    for row in rows:
        if row.ev_score is not None and ev_values:
            below = sum(1 for value in ev_values if value <= row.ev_score)
            row.league_percentile = _safe_round((below / float(len(ev_values))) * 100.0, 1)

    overused_flags: List[PlayTypeFlag] = []
    underused_flags: List[PlayTypeFlag] = []
    median_ev = statistics.median(ev_values) if ev_values else 0.0
    for row in rows:
        if row.usage_share is None or row.ev_score is None:
            continue
        if row.usage_share >= 0.18 and row.ev_score < median_ev:
            overused_flags.append(
                PlayTypeFlag(
                    action_family=row.action_family,
                    label=row.label,
                    reason="This action is absorbing too much usage relative to its value.",
                    severity="medium" if row.usage_share < 0.28 else "high",  # type: ignore[arg-type]
                    confidence="medium",
                    evidence=[
                        "{0} usage share".format(row.usage_share),
                        "{0} EV score".format(row.ev_score),
                    ],
                )
            )
        if row.usage_share <= 0.12 and row.ev_score > median_ev:
            underused_flags.append(
                PlayTypeFlag(
                    action_family=row.action_family,
                    label=row.label,
                    reason="This action is returning more value than its current usage suggests.",
                    severity="medium" if row.ev_score < (median_ev + 0.15) else "high",  # type: ignore[arg-type]
                    confidence="medium",
                    evidence=[
                        "{0} usage share".format(row.usage_share),
                        "{0} EV score".format(row.ev_score),
                    ],
                )
            )

    warnings: List[str] = []
    if opponent is None:
        warnings.append("No opponent filter was provided; the EV view is team-season based.")
    if not rows:
        warnings.append("No inferred action families cleared the sample threshold.")

    response = PlayTypeEVResponse(
        team_abbreviation=team.abbreviation,
        season=season,
        filters=PlayTypeEVFilters(
            season=season,
            opponent_abbreviation=opponent.abbreviation if opponent else None,
            window_games=window_games,
        ),
        action_rows=rows,
        overused_flags=overused_flags[:3],
        underused_flags=underused_flags[:3],
        warnings=warnings,
    )
    CacheManager.set(cache_key, response.model_dump(), 900)
    return response


def build_matchup_flags_report(
    db: Session,
    team_abbr: str,
    opponent_abbr: str,
    season: str,
) -> MatchupFlagsResponse:
    team = _fetch_team(db, team_abbr)
    opponent = _fetch_team(db, opponent_abbr)
    watermark = _season_watermark(db, season)
    cache_key = "matchup_flags:{0}:{1}:{2}:{3}".format(team.abbreviation, opponent.abbreviation, season, watermark)
    cached = CacheManager.get(cache_key)
    if cached:
        return MatchupFlagsResponse(**cached)

    comparison = build_team_comparison_report(db=db, team_a=team.abbreviation, team_b=opponent.abbreviation, season=season)
    team_style = build_team_style_profile(db=db, abbr=team.abbreviation, season=season, window=10, opponent_abbr=opponent.abbreviation)
    opponent_style = build_team_style_profile(db=db, abbr=opponent.abbreviation, season=season, window=10, opponent_abbr=team.abbreviation)
    team_rotation = build_team_rotation_report(db=db, team=team, season=season)
    opponent_rotation = build_team_rotation_report(db=db, team=opponent, season=season)

    team_rows = {row.stat_id: row for row in team_style.opponent_comparison}
    style_rows = {row.stat_id: row for row in comparison.rows}

    flags: List[MatchupFlag] = []

    def _flag(
        flag_id: str,
        title: str,
        summary: str,
        severity: str,
        confidence: str,
        evidence: List[MatchupFlagEvidence],
        drilldowns: List[str],
    ) -> None:
        flags.append(
            MatchupFlag(
                flag_id=flag_id,
                title=title,
                summary=summary,
                severity=severity,  # type: ignore[arg-type]
                confidence=confidence,  # type: ignore[arg-type]
                evidence=evidence,
                drilldowns=drilldowns,
            )
        )

    pace_row = team_rows.get("pace")
    three_row = team_rows.get("three_point_rate")
    tov_row = team_rows.get("turnover_rate")
    oreb_row = team_rows.get("oreb_rate")
    ts_row = team_rows.get("ts_pct")
    ftr_row = team_rows.get("ftr")
    net_row = style_rows.get("net_rating")

    if pace_row and pace_row.entity_a_value is not None and pace_row.entity_b_value is not None and abs(pace_row.entity_a_value - pace_row.entity_b_value) >= 1.5:
        faster = "team_a" if pace_row.entity_a_value > pace_row.entity_b_value else "team_b"
        leader = team if faster == "team_a" else opponent
        _flag(
            "pace_edge",
            "Pace edge",
            "{0} can pull the game toward its preferred tempo.".format(leader.abbreviation),
            "medium" if abs(pace_row.entity_a_value - pace_row.entity_b_value) < 3.0 else "high",
            "high",
            [
                MatchupFlagEvidence(
                    metric_id="pace",
                    label="Estimated pace",
                    team_value=pace_row.entity_a_value,
                    opponent_value=pace_row.entity_b_value,
                    league_reference=team_rows.get("pace").entity_a_value,
                    note="Pace is a clean style proxy in this matchup.",
                )
            ],
            [
                "/compare?mode=teams&team_a={0}&team_b={1}&season={2}".format(team.abbreviation, opponent.abbreviation, season),
                "/teams/{0}".format(team.abbreviation),
            ],
        )

    if three_row and three_row.entity_a_value is not None and three_row.entity_b_value is not None and abs(three_row.entity_a_value - three_row.entity_b_value) >= 0.04:
        leader = team if three_row.entity_a_value > three_row.entity_b_value else opponent
        _flag(
            "spacing_edge",
            "Spacing and shot-volume edge",
            "{0} brings the cleaner three-point profile into the matchup.".format(leader.abbreviation),
            "medium",
            "high",
            [
                MatchupFlagEvidence(
                    metric_id="three_point_rate",
                    label="3PA rate",
                    team_value=three_row.entity_a_value,
                    opponent_value=three_row.entity_b_value,
                    league_reference=None,
                    note="Shot profile mismatch is visible in the current style profiles.",
                ),
                MatchupFlagEvidence(
                    metric_id="ts_pct",
                    label="True shooting",
                    team_value=ts_row.entity_a_value if ts_row else None,
                    opponent_value=ts_row.entity_b_value if ts_row else None,
                    league_reference=None,
                    note="Efficiency context supports the spacing read.",
                ),
            ],
            [
                "/compare?mode=teams&team_a={0}&team_b={1}&season={2}".format(team.abbreviation, opponent.abbreviation, season),
                "/pre-read?team={0}&opponent={1}&season={2}".format(team.abbreviation, opponent.abbreviation, season),
            ],
        )

    if tov_row and tov_row.entity_a_value is not None and tov_row.entity_b_value is not None and abs(tov_row.entity_a_value - tov_row.entity_b_value) >= 0.03:
        cleaner = team if tov_row.entity_a_value < tov_row.entity_b_value else opponent
        _flag(
            "turnover_edge",
            "Turnover control edge",
            "{0} protects the ball more cleanly.".format(cleaner.abbreviation),
            "medium",
            "high",
            [
                MatchupFlagEvidence(
                    metric_id="turnover_rate",
                    label="Turnover rate",
                    team_value=tov_row.entity_a_value,
                    opponent_value=tov_row.entity_b_value,
                    league_reference=None,
                    note="Possession security is a clear swing factor here.",
                )
            ],
            [
                "/compare?mode=teams&team_a={0}&team_b={1}&season={2}".format(team.abbreviation, opponent.abbreviation, season),
                "/games?team={0}&opponent={1}&season={2}".format(team.abbreviation, opponent.abbreviation, season),
            ],
        )

    if oreb_row and oreb_row.entity_a_value is not None and oreb_row.entity_b_value is not None and abs(oreb_row.entity_a_value - oreb_row.entity_b_value) >= 0.03:
        glass = team if oreb_row.entity_a_value > oreb_row.entity_b_value else opponent
        _flag(
            "glass_edge",
            "Glass edge",
            "{0} has the better offensive-rebounding base.".format(glass.abbreviation),
            "medium",
            "medium",
            [
                MatchupFlagEvidence(
                    metric_id="oreb_rate",
                    label="Offensive rebound rate",
                    team_value=oreb_row.entity_a_value,
                    opponent_value=oreb_row.entity_b_value,
                    league_reference=None,
                    note="Second-chance pressure should matter in this matchup.",
                ),
            ],
            [
                "/compare?mode=teams&team_a={0}&team_b={1}&season={2}".format(team.abbreviation, opponent.abbreviation, season),
                "/pre-read?team={0}&opponent={1}&season={2}".format(team.abbreviation, opponent.abbreviation, season),
            ],
        )

    if ftr_row and ftr_row.entity_a_value is not None and ftr_row.entity_b_value is not None and abs(ftr_row.entity_a_value - ftr_row.entity_b_value) >= 0.03:
        pressure = team if ftr_row.entity_a_value > ftr_row.entity_b_value else opponent
        _flag(
            "foul_pressure_edge",
            "Foul pressure edge",
            "{0} should create more free-throw pressure.".format(pressure.abbreviation),
            "medium",
            "medium",
            [
                MatchupFlagEvidence(
                    metric_id="ftr",
                    label="Free throw rate",
                    team_value=ftr_row.entity_a_value,
                    opponent_value=ftr_row.entity_b_value,
                    league_reference=None,
                    note="Free-throw pressure is a practical coaching lever.",
                ),
            ],
            [
                "/compare?mode=teams&team_a={0}&team_b={1}&season={2}".format(team.abbreviation, opponent.abbreviation, season),
                "/pre-read?team={0}&opponent={1}&season={2}".format(team.abbreviation, opponent.abbreviation, season),
            ],
        )

    starter_gap = None
    if team_rotation.starter_stability and opponent_rotation.starter_stability:
        if team_rotation.starter_stability != opponent_rotation.starter_stability:
            starter_gap = "team" if "stable" in team_rotation.starter_stability.lower() else "opponent"
            _flag(
                "rotation_stability_edge",
                "Rotation stability edge",
                "{0} has the steadier recent rotation shape.".format(team.abbreviation if starter_gap == "team" else opponent.abbreviation),
                "low",
                "medium",
                [
                    MatchupFlagEvidence(
                        metric_id="starter_stability",
                        label="Starter stability",
                        team_value=None,
                        opponent_value=None,
                        league_reference=None,
                        note="{0} vs {1}".format(team_rotation.starter_stability, opponent_rotation.starter_stability),
                    ),
                ],
                [
                    "/teams/{0}".format(team.abbreviation),
                    "/teams/{0}".format(opponent.abbreviation),
                ],
            )

    warnings: List[str] = []
    if not comparison.rows:
        warnings.append("Team comparison context is limited for this season.")
    if not flags:
        warnings.append("No clear matchup flags cleared the confidence threshold.")

    response = MatchupFlagsResponse(
        team_abbreviation=team.abbreviation,
        opponent_abbreviation=opponent.abbreviation,
        season=season,
        flags=flags,
        warnings=warnings,
    )
    CacheManager.set(cache_key, response.model_dump(), 900)
    return response


def _candidate_games(
    db: Session,
    team: Team,
    season: str,
    opponent_abbreviation: Optional[str],
) -> List[WarehouseGame]:
    query = (
        db.query(WarehouseGame)
        .filter(WarehouseGame.season == season)
        .filter((WarehouseGame.home_team_id == team.id) | (WarehouseGame.away_team_id == team.id))
        .order_by(WarehouseGame.game_date.desc().nullslast(), WarehouseGame.game_id.desc())
    )
    if opponent_abbreviation:
        opponent = _fetch_team(db, opponent_abbreviation)
        query = query.filter((WarehouseGame.home_team_id == opponent.id) | (WarehouseGame.away_team_id == opponent.id))
    return query.all()


def build_follow_through_report(db: Session, payload: FollowThroughRequest) -> FollowThroughResponse:
    team = _fetch_team(db, payload.team)
    opponent = _fetch_team(db, payload.opponent) if payload.opponent else None
    watermark = _season_watermark(db, payload.season)
    cache_key = "follow_through:{0}:{1}:{2}:{3}:{4}:{5}".format(
        payload.source_type,
        payload.source_id,
        team.abbreviation,
        opponent.abbreviation if opponent else "none",
        payload.season,
        watermark,
    )
    cached = CacheManager.get(cache_key)
    if cached:
        return FollowThroughResponse(**cached)

    games = _candidate_games(db, team, payload.season, opponent.abbreviation if opponent else None)
    if not games:
        return FollowThroughResponse(
            source_type=payload.source_type,
            source_id=payload.source_id,
            team_abbreviation=team.abbreviation,
            opponent_abbreviation=opponent.abbreviation if opponent else None,
            season=payload.season,
            window=payload.window,
            games=[],
            warnings=["No eligible games were found for follow-through."],
        )

    player_games: Dict[int, set[str]] = defaultdict(set)
    if payload.player_ids:
        rows = (
            db.query(GamePlayerStat)
            .filter(
                GamePlayerStat.season == payload.season,
                GamePlayerStat.player_id.in_(payload.player_ids),
            )
            .all()
        )
        for row in rows:
            player_games[row.player_id].add(row.game_id)

    team_style = build_team_style_profile(db=db, abbr=team.abbreviation, season=payload.season, window=payload.window, opponent_abbr=payload.opponent)
    team_pace = next((row.team_value for row in team_style.current_profile if row.metric_id == "pace"), None)
    target_game_ids = {game.game_id for game in games[: max(payload.window, 5)]}
    recent_game_ids = list(target_game_ids)

    candidate_rows: List[FollowThroughGame] = []
    for index, game in enumerate(games[: max(payload.window, 5)]):
        opponent_id = game.away_team_id if game.home_team_id == team.id else game.home_team_id
        opponent_team = db.query(Team).filter(Team.id == opponent_id).first() if opponent_id else None
        recency_score = max(0.0, 1.0 - (index * 0.15))
        opponent_match = 1.0 if opponent and opponent_team and opponent_team.id == opponent.id else 0.0
        player_overlap = 0.0
        if payload.player_ids:
            matched = sum(1 for player_id in payload.player_ids if game.game_id in player_games.get(player_id, set()))
            player_overlap = matched / float(len(payload.player_ids))
        source_bonus = 0.15 if payload.source_type in {"matchup_flag", "decision", "scouting", "prep-queue"} else 0.10 if payload.source_type == "trend_card" else 0.05
        if opponent_match > 0:
            source_bonus += 0.10
        if game.home_score is not None and game.away_score is not None:
            margin = abs((game.home_score or 0) - (game.away_score or 0))
        else:
            margin = None
        margin_bonus = 0.1 if margin is not None and margin <= 10 else 0.0
        relevance = 100.0 * ((0.35 * recency_score) + (0.30 * opponent_match) + (0.20 * player_overlap) + source_bonus + margin_bonus)
        supporting_metrics = [
            "recent game",
            "opponent match" if opponent_match else "style context",
        ]
        if player_overlap > 0:
            supporting_metrics.append("player overlap")
        why_parts = []
        if opponent_match:
            why_parts.append("same opponent")
        if player_overlap > 0:
            why_parts.append("selected players appear in this game")
        if not why_parts:
            why_parts.append("recent game with a relevant style frame")
        if team_pace is not None:
            supporting_metrics.append("team pace {0}".format(_safe_round(team_pace, 1)))
        deep_link_params = {
            "source": payload.source_type,
            "source_id": payload.source_id,
            "team": team.abbreviation,
            "season": payload.season,
            "linkage_quality": payload.context.get("linkage_quality", "timeline"),
        }
        if payload.context.get("source_surface"):
            deep_link_params["source_surface"] = payload.context["source_surface"]
        if payload.context.get("source_label"):
            deep_link_params["source_label"] = payload.context["source_label"]
        if payload.context.get("reason"):
            deep_link_params["reason"] = payload.context["reason"]
        if payload.context.get("return_to"):
            deep_link_params["return_to"] = payload.context["return_to"]
        deep_link_url = "/games/{0}?{1}".format(
            game.game_id,
            urlencode(deep_link_params),
        )
        candidate_rows.append(
            FollowThroughGame(
                game_id=game.game_id,
                game_date=game.game_date.isoformat() if game.game_date else None,
                opponent_abbreviation=opponent_team.abbreviation if opponent_team else None,
                result=("W" if (game.home_score or 0) > (game.away_score or 0) else "L") if game.home_score is not None and game.away_score is not None else None,
                why_this_game=", ".join(why_parts).capitalize(),
                relevance_score=_safe_round(relevance, 2) or 0.0,
                supporting_metrics=supporting_metrics,
                deep_link_url=deep_link_url,
            )
        )

    candidate_rows.sort(key=lambda item: item.relevance_score, reverse=True)
    warnings: List[str] = []
    if not candidate_rows:
        warnings.append("No games met the follow-through relevance threshold.")
    response = FollowThroughResponse(
        source_type=payload.source_type,
        source_id=payload.source_id,
        team_abbreviation=team.abbreviation,
        opponent_abbreviation=opponent.abbreviation if opponent else None,
        season=payload.season,
        window=payload.window,
        games=candidate_rows[:5],
        warnings=warnings,
    )
    CacheManager.set(cache_key, response.model_dump(), 900)
    return response


@router.get("/lineup-impact", response_model=LineupImpactResponse)
def get_lineup_impact(
    team: str = Query(...),
    season: str = Query("2025-26"),
    opponent: Optional[str] = Query(None),
    window: int = Query(10, ge=1, le=30),
    min_possessions: int = Query(25, ge=1),
    db: Session = Depends(get_db),
):
    return build_lineup_impact_report(
        db=db,
        team_abbr=team,
        season=season,
        opponent_abbr=opponent,
        window_games=window,
        min_possessions=min_possessions,
    )


@router.get("/play-type-ev", response_model=PlayTypeEVResponse)
def get_play_type_ev(
    team: str = Query(...),
    season: str = Query("2025-26"),
    opponent: Optional[str] = Query(None),
    window: int = Query(10, ge=1, le=30),
    db: Session = Depends(get_db),
):
    return build_play_type_ev_report(
        db=db,
        team_abbr=team,
        season=season,
        opponent_abbr=opponent,
        window_games=window,
    )


@router.get("/matchup-flags", response_model=MatchupFlagsResponse)
def get_matchup_flags(
    team: str = Query(...),
    opponent: str = Query(...),
    season: str = Query("2025-26"),
    db: Session = Depends(get_db),
):
    return build_matchup_flags_report(
        db=db,
        team_abbr=team,
        opponent_abbr=opponent,
        season=season,
    )


@follow_router.post("/games", response_model=FollowThroughResponse)
def follow_through_games(
    payload: FollowThroughRequest,
    db: Session = Depends(get_db),
):
    return build_follow_through_report(db=db, payload=payload)
