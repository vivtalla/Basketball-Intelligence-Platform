from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Dict, List, Literal, Optional, Tuple
from urllib.parse import urlencode

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from data.cache import CacheManager
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
from services.compare_service import build_team_comparison_report
from services.style_feature_service import build_style_matchup_snapshot, build_style_metric_snapshot
from services.team_rotation_service import build_team_rotation_report

ConfidenceLevel = Literal["high", "medium", "low"]
SeverityLevel = Literal["high", "medium", "low"]

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


def _parse_lineup_key(lineup_key: str) -> List[int]:
    player_ids: List[int] = []
    for token in lineup_key.split("-"):
        token = token.strip()
        if not token:
            continue
        try:
            player_ids.append(int(token))
        except ValueError:
            continue
    return player_ids


def _lineup_name_lookup(db: Session, lineup_rows: List[LineupStats]) -> Dict[str, Tuple[List[int], List[str]]]:
    lineup_ids = {row.lineup_key: _parse_lineup_key(row.lineup_key) for row in lineup_rows}
    unique_player_ids = sorted({player_id for player_ids in lineup_ids.values() for player_id in player_ids})
    if not unique_player_ids:
        return {lineup_key: ([], []) for lineup_key in lineup_ids}

    roster = db.query(Player).filter(Player.id.in_(unique_player_ids)).all()
    name_map = {player.id: player.full_name for player in roster}
    return {
        lineup_key: (
            player_ids,
            [name_map.get(player_id, str(player_id)) for player_id in player_ids],
        )
        for lineup_key, player_ids in lineup_ids.items()
    }


def _infer_action_family(event: PlayByPlayEvent, fallback: str = "misc") -> str:
    desc = (event.description or "").lower()
    clock = event.clock or ""

    if event.action_type == "freethrow":
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
        return fallback
    if event.action_type == "2pt":
        return "rim_pressure"
    if event.action_type == "3pt":
        return "spot_up"
    return fallback


def _lineup_confidence(possessions: Optional[int]) -> ConfidenceLevel:
    if (possessions or 0) >= 200:
        return "high"
    if (possessions or 0) >= 80:
        return "medium"
    return "low"


def _report_confidence(lineup_rows: List[LineupStats], row_payloads: List[LineupImpactRow]) -> ConfidenceLevel:
    if len(lineup_rows) >= 10 and (lineup_rows[0].possessions or 0) >= 150:
        return "high"
    if len(lineup_rows) >= 5:
        return "medium"
    if row_payloads:
        return "low"
    return "low"


def _severity_from_threshold(value: Optional[float], medium: float, high: float, higher_is_better: bool = True) -> SeverityLevel:
    if value is None:
        return "low"
    gap = float(value)
    if not higher_is_better:
        gap = -gap
    if gap >= high:
        return "high"
    if gap >= medium:
        return "medium"
    return "low"


def _lineup_row_payload(
    row: LineupStats,
    lineup_names: Dict[str, Tuple[List[int], List[str]]],
    team_baseline_net: Optional[float],
    team_pace: Optional[float],
    minute_delta: float,
) -> LineupImpactRow:
    player_ids, player_names = lineup_names.get(row.lineup_key, ([], []))
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
        confidence=_lineup_confidence(row.possessions),
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

    style_snapshot = build_style_metric_snapshot(db=db, team_abbr=team.abbreviation, season=season, window_games=window_games)
    team_baseline_net = style_snapshot.get("net_rating")
    team_pace = style_snapshot.get("pace")

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

    lineup_names = _lineup_name_lookup(db, lineup_rows)
    row_payloads = [
        _lineup_row_payload(
            row=row,
            lineup_names=lineup_names,
            team_baseline_net=team_baseline_net,
            team_pace=team_pace,
            minute_delta=5.0,
        )
        for row in lineup_rows
    ]

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

    confidence = _report_confidence(lineup_rows, row_payloads)
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
        confidence=confidence,
        warnings=warnings,
    )
    CacheManager.set(cache_key, response.model_dump(), 900)
    return response


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

    recent_game_ids = [row.game_id for row, _ in game_rows[:window_games]] if window_games else [row.game_id for row, _ in game_rows]
    events = (
        db.query(PlayByPlayEvent)
        .filter(
            PlayByPlayEvent.season == season,
            PlayByPlayEvent.game_id.in_(recent_game_ids),
            PlayByPlayEvent.team_id == team.id,
        )
        .order_by(PlayByPlayEvent.game_id.asc(), PlayByPlayEvent.order_index.asc())
        .all()
    )

    family_stats: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {"usage": 0.0, "points": 0.0, "turnovers": 0.0, "fouls": 0.0, "oreb": 0.0}
    )
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

    median_ev = statistics.median(ev_values) if ev_values else 0.0
    overused_flags: List[PlayTypeFlag] = []
    underused_flags: List[PlayTypeFlag] = []
    for row in rows:
        if row.usage_share is None or row.ev_score is None:
            continue
        if row.usage_share >= 0.18 and row.ev_score < median_ev:
            severity: SeverityLevel = "high" if row.usage_share >= 0.28 else "medium"
            overused_flags.append(
                PlayTypeFlag(
                    action_family=row.action_family,
                    label=row.label,
                    reason="This action is absorbing too much usage relative to its value.",
                    severity=severity,
                    confidence="medium",
                    evidence=[
                        "{0} usage share".format(row.usage_share),
                        "{0} EV score".format(row.ev_score),
                    ],
                )
            )
        if row.usage_share <= 0.12 and row.ev_score > median_ev:
            severity = "high" if row.ev_score >= (median_ev + 0.15) else "medium"
            underused_flags.append(
                PlayTypeFlag(
                    action_family=row.action_family,
                    label=row.label,
                    reason="This action is returning more value than its current usage suggests.",
                    severity=severity,
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
    team_style = build_style_matchup_snapshot(
        db=db,
        team_abbr=team.abbreviation,
        opponent_abbr=opponent.abbreviation,
        season=season,
        window_games=10,
    )
    team_rotation = build_team_rotation_report(db=db, team=team, season=season)
    opponent_rotation = build_team_rotation_report(db=db, team=opponent, season=season)

    team_rows = team_style
    style_rows = {row.stat_id: row for row in comparison.rows}
    flags: List[MatchupFlag] = []

    def add_flag(
        flag_id: str,
        title: str,
        summary: str,
        severity: SeverityLevel,
        confidence: ConfidenceLevel,
        evidence: List[MatchupFlagEvidence],
        drilldowns: List[str],
    ) -> None:
        flags.append(
            MatchupFlag(
                flag_id=flag_id,
                title=title,
                summary=summary,
                severity=severity,
                confidence=confidence,
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

    if pace_row and pace_row["entity_a_value"] is not None and pace_row["entity_b_value"] is not None and abs(pace_row["entity_a_value"] - pace_row["entity_b_value"]) >= 1.5:
        faster = "team_a" if pace_row["entity_a_value"] > pace_row["entity_b_value"] else "team_b"
        leader = team if faster == "team_a" else opponent
        severity = "high" if abs(pace_row["entity_a_value"] - pace_row["entity_b_value"]) >= 3.0 else "medium"
        add_flag(
            "pace_edge",
            "Pace edge",
            "{0} can pull the game toward its preferred tempo.".format(leader.abbreviation),
            severity,
            "high",
            [
                MatchupFlagEvidence(
                    metric_id="pace",
                    label="Estimated pace",
                    team_value=pace_row["entity_a_value"],
                    opponent_value=pace_row["entity_b_value"],
                    league_reference=pace_row["entity_a_value"],
                    note="Pace is a clean style proxy in this matchup.",
                )
            ],
            [
                "/compare?mode=teams&team_a={0}&team_b={1}&season={2}".format(team.abbreviation, opponent.abbreviation, season),
                "/teams/{0}".format(team.abbreviation),
            ],
        )

    if three_row and three_row["entity_a_value"] is not None and three_row["entity_b_value"] is not None and abs(three_row["entity_a_value"] - three_row["entity_b_value"]) >= 0.04:
        leader = team if three_row["entity_a_value"] > three_row["entity_b_value"] else opponent
        add_flag(
            "spacing_edge",
            "Spacing and shot-volume edge",
            "{0} brings the cleaner three-point profile into the matchup.".format(leader.abbreviation),
            "medium",
            "high",
            [
                MatchupFlagEvidence(
                    metric_id="three_point_rate",
                    label="3PA rate",
                    team_value=three_row["entity_a_value"],
                    opponent_value=three_row["entity_b_value"],
                    league_reference=None,
                    note="Shot profile mismatch is visible in the current style profiles.",
                ),
                MatchupFlagEvidence(
                    metric_id="ts_pct",
                    label="True shooting",
                    team_value=ts_row["entity_a_value"] if ts_row else None,
                    opponent_value=ts_row["entity_b_value"] if ts_row else None,
                    league_reference=None,
                    note="Efficiency context supports the spacing read.",
                ),
            ],
            [
                "/compare?mode=teams&team_a={0}&team_b={1}&season={2}".format(team.abbreviation, opponent.abbreviation, season),
                "/pre-read?team={0}&opponent={1}&season={2}".format(team.abbreviation, opponent.abbreviation, season),
            ],
        )

    if tov_row and tov_row["entity_a_value"] is not None and tov_row["entity_b_value"] is not None and abs(tov_row["entity_a_value"] - tov_row["entity_b_value"]) >= 0.03:
        cleaner = team if tov_row["entity_a_value"] < tov_row["entity_b_value"] else opponent
        add_flag(
            "turnover_edge",
            "Turnover control edge",
            "{0} protects the ball more cleanly.".format(cleaner.abbreviation),
            "medium",
            "high",
            [
                MatchupFlagEvidence(
                    metric_id="turnover_rate",
                    label="Turnover rate",
                    team_value=tov_row["entity_a_value"],
                    opponent_value=tov_row["entity_b_value"],
                    league_reference=None,
                    note="Possession security is a clear swing factor here.",
                )
            ],
            [
                "/compare?mode=teams&team_a={0}&team_b={1}&season={2}".format(team.abbreviation, opponent.abbreviation, season),
                "/games?team={0}&opponent={1}&season={2}".format(team.abbreviation, opponent.abbreviation, season),
            ],
        )

    if oreb_row and oreb_row["entity_a_value"] is not None and oreb_row["entity_b_value"] is not None and abs(oreb_row["entity_a_value"] - oreb_row["entity_b_value"]) >= 0.03:
        glass = team if oreb_row["entity_a_value"] > oreb_row["entity_b_value"] else opponent
        add_flag(
            "glass_edge",
            "Glass edge",
            "{0} has the better offensive-rebounding base.".format(glass.abbreviation),
            "medium",
            "medium",
            [
                MatchupFlagEvidence(
                    metric_id="oreb_rate",
                    label="Offensive rebound rate",
                    team_value=oreb_row["entity_a_value"],
                    opponent_value=oreb_row["entity_b_value"],
                    league_reference=None,
                    note="Second-chance pressure should matter in this matchup.",
                ),
            ],
            [
                "/compare?mode=teams&team_a={0}&team_b={1}&season={2}".format(team.abbreviation, opponent.abbreviation, season),
                "/pre-read?team={0}&opponent={1}&season={2}".format(team.abbreviation, opponent.abbreviation, season),
            ],
        )

    if ftr_row and ftr_row["entity_a_value"] is not None and ftr_row["entity_b_value"] is not None and abs(ftr_row["entity_a_value"] - ftr_row["entity_b_value"]) >= 0.03:
        pressure = team if ftr_row["entity_a_value"] > ftr_row["entity_b_value"] else opponent
        add_flag(
            "foul_pressure_edge",
            "Foul pressure edge",
            "{0} should create more free-throw pressure.".format(pressure.abbreviation),
            "medium",
            "medium",
            [
                MatchupFlagEvidence(
                    metric_id="ftr",
                    label="Free throw rate",
                    team_value=ftr_row["entity_a_value"],
                    opponent_value=ftr_row["entity_b_value"],
                    league_reference=None,
                    note="Free-throw pressure is a practical coaching lever.",
                ),
            ],
            [
                "/compare?mode=teams&team_a={0}&team_b={1}&season={2}".format(team.abbreviation, opponent.abbreviation, season),
                "/pre-read?team={0}&opponent={1}&season={2}".format(team.abbreviation, opponent.abbreviation, season),
            ],
        )

    if team_rotation.starter_stability and opponent_rotation.starter_stability and team_rotation.starter_stability != opponent_rotation.starter_stability:
        stable_team = team if "stable" in team_rotation.starter_stability.lower() else opponent
        add_flag(
            "rotation_stability_edge",
            "Rotation stability edge",
            "{0} has the steadier recent rotation shape.".format(stable_team.abbreviation),
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
                )
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
    if net_row is not None and net_row.edge == "even":
        warnings.append("Overall profile edge is still close enough that the flags should stay bounded.")

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
    limit: int,
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
    return query.limit(max(limit, 1)).all()


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

    candidate_limit = max(payload.window, 5)
    games = _candidate_games(db, team, payload.season, opponent.abbreviation if opponent else None, limit=candidate_limit)
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
        game_ids = [game.game_id for game in games]
        rows = (
            db.query(GamePlayerStat)
            .filter(
                GamePlayerStat.season == payload.season,
                GamePlayerStat.player_id.in_(payload.player_ids),
                GamePlayerStat.game_id.in_(game_ids),
            )
            .all()
        )
        for row in rows:
            player_games[row.player_id].add(row.game_id)

    style_snapshot = build_style_metric_snapshot(
        db=db,
        team_abbr=team.abbreviation,
        season=payload.season,
        window_games=payload.window,
    )
    team_pace = style_snapshot.get("pace")
    opponent_ids = {
        opponent_id
        for game in games
        for opponent_id in [game.away_team_id if game.home_team_id == team.id else game.home_team_id]
        if opponent_id is not None
    }
    opponent_teams = db.query(Team).filter(Team.id.in_(opponent_ids)).all() if opponent_ids else []
    opponent_lookup = {opponent_team.id: opponent_team for opponent_team in opponent_teams}

    candidate_rows: List[FollowThroughGame] = []
    for index, game in enumerate(games):
        opponent_id = game.away_team_id if game.home_team_id == team.id else game.home_team_id
        opponent_team = opponent_lookup.get(opponent_id) if opponent_id else None
        recency_score = max(0.0, 1.0 - (index * 0.15))
        opponent_match = 1.0 if opponent and opponent_team and opponent_team.id == opponent.id else 0.0
        player_overlap = 0.0
        if payload.player_ids:
            matched = sum(1 for player_id in payload.player_ids if game.game_id in player_games.get(player_id, set()))
            player_overlap = matched / float(len(payload.player_ids))
        source_bonus = 0.15 if payload.source_type in {"matchup_flag", "decision", "scouting", "prep-queue"} else 0.10 if payload.source_type == "trend_card" else 0.05
        if opponent_match > 0:
            source_bonus += 0.10
        margin = None
        if game.home_score is not None and game.away_score is not None:
            margin = abs((game.home_score or 0) - (game.away_score or 0))
        margin_bonus = 0.1 if margin is not None and margin <= 10 else 0.0
        relevance = 100.0 * ((0.35 * recency_score) + (0.30 * opponent_match) + (0.20 * player_overlap) + source_bonus + margin_bonus)

        supporting_metrics = [
            "recent game",
            "opponent match" if opponent_match else "style context",
        ]
        if player_overlap > 0:
            supporting_metrics.append("player overlap")
        if team_pace is not None:
            supporting_metrics.append("team pace {0}".format(_safe_round(team_pace, 1)))

        why_parts = []
        if opponent_match:
            why_parts.append("same opponent")
        if player_overlap > 0:
            why_parts.append("selected players appear in this game")
        if not why_parts:
            why_parts.append("recent game with a relevant style frame")

        deep_link_params = {
            "source": payload.source_type,
            "source_id": payload.source_id,
            "team": team.abbreviation,
            "season": payload.season,
            "linkage_quality": payload.context.get("linkage_quality", "timeline"),
        }
        for field in ["source_surface", "source_label", "reason", "return_to", "focus_event_id", "focus_action_number"]:
            if payload.context.get(field):
                deep_link_params[field] = payload.context[field]

        candidate_rows.append(
            FollowThroughGame(
                game_id=game.game_id,
                game_date=game.game_date.isoformat() if game.game_date else None,
                opponent_abbreviation=opponent_team.abbreviation if opponent_team else None,
                result=("W" if (game.home_score or 0) > (game.away_score or 0) else "L") if game.home_score is not None and game.away_score is not None else None,
                why_this_game=", ".join(why_parts).capitalize(),
                relevance_score=_safe_round(relevance, 2) or 0.0,
                supporting_metrics=supporting_metrics,
                deep_link_url="/games/{0}?{1}".format(game.game_id, urlencode(deep_link_params)),
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
