from __future__ import annotations

from collections import defaultdict
from statistics import mean, pstdev
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlencode

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from data.cache import CacheManager
from db.models import (
    GamePlayerStat,
    GameTeamStat,
    LineupStats,
    Player,
    PlayerClutchStat,
    PlayerGravityStat,
    PlayerHustleStat,
    PlayerOnOff,
    PlayerPlayTypeStat,
    PlayerShotChart,
    PlayerTrackingStat,
    PlayByPlayEvent,
    SeasonStat,
    Team,
    TeamSeasonStat,
    WarehouseGame,
)
from models.trends import (
    ReplayLaunchTarget,
    TrendCard,
    TrendCardsResponse,
    TrendDriverContribution,
    TrendFoundationSignal,
    TrendMethodology,
    TrendOverview,
    TrendPlayerDetail,
    TrendPlayerRow,
    TrendSeriesPoint,
)
from routers.styles import build_team_style_profile
from services.shot_intelligence_service import METHODOLOGY_VERSION as SHOT_QUALITY_VERSION
from services.shot_intelligence_service import _expected_baseline, _load_baselines, _points


TREND_METHODOLOGY_VERSION = "trend_intelligence_v1"

SIGNAL_LABELS = {
    "scoring": "Scoring form",
    "efficiency": "Efficiency",
    "role": "Role load",
    "impact": "On/off impact",
    "lineup": "Lineup fit",
    "clutch": "Clutch context",
    "shot_quality": "Shot quality",
    "play_type": "Play-type pressure",
    "tracking": "Tracking context",
    "hustle": "Hustle activity",
    "gravity": "Gravity",
}

OPPORTUNITY_SIGNAL_MAP = {
    "efficiency_load_gap": {"efficiency", "role"},
    "team_impact_swing": {"impact"},
    "lineup_synergy_lift": {"lineup"},
    "role_fit_gap": {"role", "shot_quality", "play_type"},
    "cohort_percentile": {"scoring", "efficiency"},
}

TREND_REPLAY_RULES: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "shot-profile-drift": {
        "action_types": ("3pt",),
        "action_families": (),
        "description_terms": ("three", "3-pt", "3pt"),
    },
    "efficiency-swing": {
        "action_types": ("2pt", "3pt"),
        "action_families": ("jump_shot", "rim_pressure", "spot_up"),
        "description_terms": (),
    },
    "turnover-pressure": {
        "action_types": ("turnover",),
        "action_families": ("live_ball_turnover", "dead_ball_turnover"),
        "description_terms": ("turnover",),
    },
    "foul-trend": {
        "action_types": ("foul",),
        "action_families": ("shooting_foul", "take_foul", "personal_foul"),
        "description_terms": ("foul",),
    },
    "pace-and-scoring": {
        "action_types": (),
        "action_families": (),
        "description_terms": (),
    },
    "rotation-drift": {
        "action_types": ("substitution",),
        "action_families": ("substitution",),
        "description_terms": ("substitution", "enters", "checks in"),
    },
    "clutch-context": {
        "action_types": ("2pt", "3pt", "turnover", "freethrow"),
        "action_families": (),
        "description_terms": (),
    },
}


def _round(value: Optional[float], digits: int = 2) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), digits)


def _avg(values: Iterable[Optional[float]]) -> Optional[float]:
    clean = [float(value) for value in values if value is not None]
    if not clean:
        return None
    return sum(clean) / float(len(clean))


def _sum(values: Iterable[Optional[float]]) -> float:
    return sum(float(value or 0.0) for value in values)


def _clamp(value: float, floor: float, ceiling: float) -> float:
    return max(floor, min(ceiling, value))


def _estimate_possessions_from_team(row: GameTeamStat) -> Optional[float]:
    possessions = float(row.fga or 0) - float(row.oreb or 0) + float(row.tov or 0) + (0.44 * float(row.fta or 0))
    if possessions <= 0:
        return None
    return possessions


def _ts_pct(points: Optional[float], fga: Optional[float], fta: Optional[float]) -> Optional[float]:
    denom = 2.0 * (float(fga or 0.0) + 0.44 * float(fta or 0.0))
    if denom <= 0:
        return None
    return float(points or 0.0) / denom


def _three_point_rate(fg3a: Optional[float], fga: Optional[float]) -> Optional[float]:
    attempts = float(fga or 0.0)
    if attempts <= 0:
        return None
    return float(fg3a or 0.0) / attempts


def _turnover_rate(tov: Optional[float], fga: Optional[float], fta: Optional[float]) -> Optional[float]:
    possessions = float(fga or 0.0) + 0.44 * float(fta or 0.0) + float(tov or 0.0)
    if possessions <= 0:
        return None
    return float(tov or 0.0) / possessions


def _fetch_team(db: Session, abbr: str) -> Team:
    team = db.query(Team).filter(Team.abbreviation == abbr.upper()).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team '{0}' not found.".format(abbr))
    return team


def _season_watermark(db: Session, season: str) -> str:
    marks = [
        db.query(func.max(GameTeamStat.updated_at)).filter(GameTeamStat.season == season).scalar(),
        db.query(func.max(GamePlayerStat.updated_at)).filter(GamePlayerStat.season == season).scalar(),
        db.query(func.max(SeasonStat.updated_at)).filter(SeasonStat.season == season).scalar(),
    ]
    latest = max((mark for mark in marks if mark is not None), default=None)
    return latest.isoformat() if latest else "none"


def _team_rows(db: Session, team_id: int, season: str) -> List[GameTeamStat]:
    return (
        db.query(GameTeamStat)
        .join(WarehouseGame, WarehouseGame.game_id == GameTeamStat.game_id)
        .filter(GameTeamStat.season == season, GameTeamStat.team_id == team_id)
        .order_by(WarehouseGame.game_date.desc().nullslast(), GameTeamStat.game_id.desc())
        .all()
    )


def _games_by_id(db: Session, game_ids: Sequence[str]) -> Dict[str, WarehouseGame]:
    if not game_ids:
        return {}
    return {row.game_id: row for row in db.query(WarehouseGame).filter(WarehouseGame.game_id.in_(list(game_ids))).all()}


def _opponent_rows_by_game(db: Session, team_id: int, game_ids: Sequence[str]) -> Dict[str, GameTeamStat]:
    if not game_ids:
        return {}
    rows = (
        db.query(GameTeamStat)
        .filter(GameTeamStat.game_id.in_(list(game_ids)), GameTeamStat.team_id != team_id)
        .all()
    )
    return {row.game_id: row for row in rows}


def _team_profile(row: GameTeamStat, opponent: Optional[GameTeamStat]) -> Dict[str, Optional[float]]:
    possessions = _estimate_possessions_from_team(row)
    opp_points = float(opponent.pts or 0.0) if opponent else None
    return {
        "pts": float(row.pts or 0.0),
        "opp_pts": opp_points,
        "net_rating": ((float(row.pts or 0.0) - opp_points) / possessions * 100.0) if possessions and opp_points is not None else None,
        "pace": possessions,
        "three_point_rate": _three_point_rate(row.fg3a, row.fga),
        "ts_pct": _ts_pct(row.pts, row.fga, row.fta),
        "turnover_rate": _turnover_rate(row.tov, row.fga, row.fta),
        "ftr": (float(row.fta or 0.0) / float(row.fga or 0.0)) if row.fga else None,
        "oreb": float(row.oreb or 0.0),
        "ast": float(row.ast or 0.0),
        "won": 1.0 if row.won else 0.0 if row.won is not None else None,
    }


def _avg_profile(rows: Sequence[GameTeamStat], opponents: Dict[str, GameTeamStat]) -> Dict[str, Optional[float]]:
    profiles = [_team_profile(row, opponents.get(row.game_id)) for row in rows]
    keys = {
        "pts",
        "opp_pts",
        "net_rating",
        "pace",
        "three_point_rate",
        "ts_pct",
        "turnover_rate",
        "ftr",
        "oreb",
        "ast",
        "won",
    }
    return {key: _avg(profile.get(key) for profile in profiles) for key in keys}


def _delta_direction(delta: Optional[float], threshold: float = 0.01, lower_is_better: bool = False) -> str:
    if delta is None or abs(delta) < threshold:
        return "flat"
    good_delta = -delta if lower_is_better else delta
    return "up" if good_delta > 0 else "down"


def _significance(delta: Optional[float], high: float, medium: float) -> str:
    magnitude = abs(float(delta or 0.0))
    if magnitude >= high:
        return "high"
    if magnitude >= medium:
        return "medium"
    return "low"


def _series_for_metric(
    rows: Sequence[GameTeamStat],
    games: Dict[str, WarehouseGame],
    opponents: Dict[str, GameTeamStat],
    metric: str,
) -> List[TrendSeriesPoint]:
    points: List[TrendSeriesPoint] = []
    for row in list(rows)[::-1][-8:]:
        game = games.get(row.game_id)
        opponent = opponents.get(row.game_id)
        profile = _team_profile(row, opponent)
        label = game.game_date.isoformat() if game and game.game_date else row.game_id[-4:]
        points.append(TrendSeriesPoint(label=label, value=_round(profile.get(metric), 3)))
    return points


def _record(rows: Sequence[GameTeamStat]) -> Optional[str]:
    if not rows:
        return None
    wins = sum(1 for row in rows if row.won)
    return "{0}-{1}".format(wins, len(rows) - wins)


def _event_identifier(event: PlayByPlayEvent) -> str:
    if event.source_event_id:
        return str(event.source_event_id)
    return str(event.id)


def _opponent_abbreviation(team_id: int, game: WarehouseGame) -> Optional[str]:
    if game.home_team_id == team_id:
        return game.away_team_abbreviation
    if game.away_team_id == team_id:
        return game.home_team_abbreviation
    return None


def _event_matches_replay_rule(
    event: PlayByPlayEvent,
    action_types: Tuple[str, ...],
    action_families: Tuple[str, ...],
    description_terms: Tuple[str, ...],
) -> bool:
    if action_types and (event.action_type or "").lower() not in action_types:
        return False
    if action_families and (event.action_family or "").lower() not in action_families:
        return False
    if description_terms:
        haystack = " ".join(
            filter(
                None,
                [
                    event.description or "",
                    event.action_type or "",
                    event.action_family or "",
                    event.sub_type or "",
                ],
            )
        ).lower()
        if not any(term in haystack for term in description_terms):
            return False
    return True


def _build_replay_target_for_recent_games(
    db: Session,
    team: Team,
    season: str,
    recent_rows: Sequence[GameTeamStat],
    source_surface: str,
    source_id: str,
    source_label: str,
    return_to: str,
    reason_prefix: str,
    action_types: Tuple[str, ...] = (),
    action_families: Tuple[str, ...] = (),
    description_terms: Tuple[str, ...] = (),
) -> Optional[ReplayLaunchTarget]:
    for row in list(recent_rows)[:5]:
        game = db.query(WarehouseGame).filter(WarehouseGame.game_id == row.game_id).first()
        if game is None:
            continue
        opponent = _opponent_abbreviation(team.id, game)
        game_date = game.game_date.isoformat() if game.game_date else None
        reason = "{0} review against {1} on {2}.".format(
            reason_prefix,
            opponent or "the recent opponent",
            game_date or "a recent game",
        )
        events = (
            db.query(PlayByPlayEvent)
            .filter(PlayByPlayEvent.game_id == game.game_id, PlayByPlayEvent.team_id == team.id)
            .order_by(PlayByPlayEvent.order_index.desc())
            .all()
        )
        should_match_events = bool(action_types or action_families or description_terms)
        matched_event = (
            next(
                (
                    candidate
                    for candidate in events
                    if _event_matches_replay_rule(
                        candidate,
                        action_types=action_types,
                        action_families=action_families,
                        description_terms=description_terms,
                    )
                ),
                None,
            )
            if should_match_events
            else None
        )
        linkage_quality = "derived" if matched_event is not None else "timeline"
        params = {
            "source": source_surface,
            "source_surface": source_surface,
            "source_id": source_id,
            "source_label": source_label,
            "reason": reason,
            "return_to": return_to,
            "linkage_quality": linkage_quality,
            "team": team.abbreviation,
            "season": season,
        }
        focus_event_id = None
        focused_action_number = None
        if matched_event is not None:
            focus_event_id = _event_identifier(matched_event)
            focused_action_number = matched_event.action_number or matched_event.order_index
            params["focus_event_id"] = focus_event_id
            if focused_action_number is not None:
                params["focus_action_number"] = str(focused_action_number)
        deep_link_url = "/games/{0}?{1}".format(game.game_id, urlencode(params))
        return ReplayLaunchTarget(
            source_surface=source_surface,
            source_label=source_label,
            reason=reason,
            target_game_id=game.game_id,
            target_game_date=game_date,
            target_opponent_abbreviation=opponent,
            focus_event_id=focus_event_id,
            focused_action_number=focused_action_number,
            linkage_quality=linkage_quality,
            deep_link_url=deep_link_url,
        )
    return None


def _build_team_cards(
    db: Session,
    team: Team,
    season: str,
    window_games: int,
    team_rows: Sequence[GameTeamStat],
    recent_rows: Sequence[GameTeamStat],
    baseline_rows: Sequence[GameTeamStat],
    games: Dict[str, WarehouseGame],
    opponents: Dict[str, GameTeamStat],
    movers: Sequence[TrendPlayerRow],
) -> List[TrendCard]:
    recent = _avg_profile(recent_rows, opponents)
    baseline = _avg_profile(baseline_rows or team_rows, opponents)
    team_season = (
        db.query(TeamSeasonStat)
        .filter(TeamSeasonStat.team_id == team.id, TeamSeasonStat.season == season, TeamSeasonStat.is_playoff == False)  # noqa: E712
        .first()
    )
    style_recent: Dict[str, Optional[float]] = {}
    style_current: Dict[str, Optional[float]] = {}
    try:
        style_report = build_team_style_profile(db=db, abbr=team.abbreviation, season=season, window=window_games)
        style_recent = {
            row.metric_id: row.recent_value if row.recent_value is not None else row.team_value
            for row in style_report.recent_drift
        }
        style_current = {row.metric_id: row.team_value for row in style_report.current_profile}
    except Exception:
        style_recent = {}
        style_current = {}

    def _related(*signals: str) -> List[int]:
        wanted = set(signals)
        return [row.player_id for row in movers if row.primary_signal in wanted][:4]

    shot_recent = style_recent.get("three_point_rate", recent.get("three_point_rate"))
    shot_base = style_current.get("three_point_rate", baseline.get("three_point_rate"))
    shot_delta = None if shot_recent is None or shot_base is None else shot_recent - shot_base
    efficiency_recent = style_recent.get("ts_pct", recent.get("ts_pct"))
    efficiency_base = style_current.get("ts_pct", baseline.get("ts_pct") or (team_season.ts_pct if team_season else None))
    efficiency_delta = None if efficiency_recent is None or efficiency_base is None else efficiency_recent - efficiency_base
    turnover_recent = style_recent.get("turnover_rate", recent.get("turnover_rate"))
    turnover_base = style_current.get("turnover_rate", baseline.get("turnover_rate"))
    turnover_delta = None if turnover_recent is None or turnover_base is None else turnover_recent - turnover_base
    ftr_recent = style_recent.get("ftr", recent.get("ftr"))
    ftr_base = style_current.get("ftr", baseline.get("ftr"))
    ftr_delta = None if ftr_recent is None or ftr_base is None else ftr_recent - ftr_base
    pace_recent = style_recent.get("pace", recent.get("pace"))
    pace_base = style_current.get("pace", baseline.get("pace") or (team_season.pace if team_season else None))
    pace_delta = None if pace_recent is None or pace_base is None else pace_recent - pace_base
    pts_delta = None if recent.get("pts") is None or baseline.get("pts") is None else recent["pts"] - baseline["pts"]  # type: ignore[operator]

    rotation_players = (
        db.query(GamePlayerStat)
        .filter(
            GamePlayerStat.game_id.in_([row.game_id for row in recent_rows]),
            GamePlayerStat.team_id == team.id,
        )
        .all()
        if recent_rows
        else []
    )
    starter_sets: List[set[int]] = []
    by_game: Dict[str, List[GamePlayerStat]] = defaultdict(list)
    for row in rotation_players:
        by_game[row.game_id].append(row)
    for rows in by_game.values():
        starter_sets.append({row.player_id for row in rows if row.is_starter})
    similarities: List[float] = []
    for prev, cur in zip(starter_sets[:-1], starter_sets[1:]):
        if prev or cur:
            similarities.append(len(prev.intersection(cur)) / float(len(prev.union(cur)) or 1))
    rotation_similarity = _avg(similarities)
    minute_values = [float(row.min or 0.0) for row in rotation_players if row.min is not None]
    minute_volatility = pstdev(minute_values) if len(minute_values) >= 2 else None

    clutch_rows = (
        db.query(PlayerClutchStat)
        .filter(PlayerClutchStat.team_id == team.id, PlayerClutchStat.season == season)
        .all()
    )
    clutch_net = _avg(row.clutch_net_rating for row in clutch_rows)
    if clutch_net is None:
        season_clutch = (
            db.query(SeasonStat)
            .filter(SeasonStat.team_abbreviation == team.abbreviation, SeasonStat.season == season, SeasonStat.is_playoff == False)  # noqa: E712
            .all()
        )
        clutch_net = _avg(row.clutch_plus_minus for row in season_clutch)

    card_specs = [
        (
            "shot-profile-drift",
            "Shot Profile Drift",
            "shot_quality",
            shot_delta,
            False,
            0.035,
            0.015,
            "Three-point volume and shot diet are changing the team profile.",
            "three_point_rate",
            {
                "recent_three_point_rate": _round(shot_recent, 3),
                "baseline_three_point_rate": _round(shot_base, 3),
                "recent_ts_pct": _round(efficiency_recent, 3),
                "baseline_ts_pct": _round(efficiency_base, 3),
            },
            _related("shot_quality", "gravity", "play_type", "efficiency"),
        ),
        (
            "efficiency-swing",
            "Efficiency Swing",
            "efficiency",
            efficiency_delta,
            False,
            0.035,
            0.015,
            "Shot making and shot quality are separating from the season baseline.",
            "ts_pct",
            {
                "recent_ts_pct": _round(efficiency_recent, 3),
                "baseline_ts_pct": _round(efficiency_base, 3),
                "recent_net_rating": _round(recent.get("net_rating"), 2),
                "baseline_net_rating": _round(baseline.get("net_rating"), 2),
            },
            _related("efficiency", "shot_quality", "scoring"),
        ),
        (
            "turnover-pressure",
            "Turnover Pressure",
            "play_type",
            turnover_delta,
            True,
            0.025,
            0.012,
            "Possessions are getting cleaner or noisier in the recent window.",
            "turnover_rate",
            {
                "recent_turnover_rate": _round(turnover_recent, 3),
                "baseline_turnover_rate": _round(turnover_base, 3),
                "recent_off_rating_proxy": _round(recent.get("pts"), 2),
                "baseline_off_rating_proxy": _round(baseline.get("pts"), 2),
            },
            _related("play_type", "role", "tracking"),
        ),
        (
            "foul-trend",
            "Foul Trend",
            "role",
            ftr_delta,
            False,
            0.035,
            0.015,
            "Free-throw pressure is either building or fading in the recent window.",
            "ftr",
            {
                "recent_ftr": _round(ftr_recent, 3),
                "baseline_ftr": _round(ftr_base, 3),
                "recent_ts_pct": _round(efficiency_recent, 3),
                "baseline_ts_pct": _round(efficiency_base, 3),
            },
            _related("role", "scoring", "efficiency"),
        ),
        (
            "pace-and-scoring",
            "Pace And Scoring",
            "scoring",
            pace_delta,
            False,
            4.0,
            1.5,
            "Tempo and scoring load are drifting together.",
            "pace",
            {
                "recent_pace": _round(pace_recent, 1),
                "baseline_pace": _round(pace_base, 1),
                "recent_pts": _round(recent.get("pts"), 1),
                "baseline_pts": _round(baseline.get("pts"), 1),
                "pts_delta": _round(pts_delta, 1),
            },
            _related("scoring", "role", "tracking"),
        ),
        (
            "rotation-drift",
            "Rotation Pressure",
            "lineup",
            None if rotation_similarity is None else 1.0 - rotation_similarity,
            True,
            0.45,
            0.25,
            "Starter continuity and minute distribution are moving underneath the team trend.",
            "net_rating",
            {
                "starter_similarity": _round(rotation_similarity, 3),
                "minute_volatility": _round(minute_volatility, 2),
                "recent_games": float(len(by_game)),
            },
            _related("lineup", "role", "impact"),
        ),
        (
            "clutch-context",
            "Clutch Context",
            "clutch",
            clutch_net,
            False,
            8.0,
            3.0,
            "Late-game support is included where clutch rows or PBP-derived clutch stats exist.",
            "net_rating",
            {
                "team_clutch_net_rating": _round(clutch_net, 2),
                "clutch_players": float(len(clutch_rows)),
            },
            _related("clutch", "impact"),
        ),
    ]

    return_to = "/insights?tab=trends&team={0}&season={1}".format(team.abbreviation, season)
    cards: List[TrendCard] = []
    for card_id, title, signal, delta, lower_is_better, high, medium, summary_base, series_metric, stats, related_ids in card_specs:
        direction = _delta_direction(delta, threshold=medium / 2.0 if medium > 0 else 0.01, lower_is_better=lower_is_better)
        if card_id == "rotation-pressure" and delta is not None:
            direction = "down" if delta >= medium else "up"
        if card_id == "clutch-context" and delta is not None:
            direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
        magnitude = abs(float(delta or 0.0)) if delta is not None else None
        signal_word = "rising" if direction == "up" else "falling" if direction == "down" else "stable"
        replay_rule = TREND_REPLAY_RULES.get(card_id, {})
        cards.append(
            TrendCard(
                card_id=card_id,
                title=title,
                scope="team",
                driver_signal=signal,
                direction=direction,  # type: ignore[arg-type]
                magnitude=_round(magnitude, 3),
                significance=_significance(delta, high=high, medium=medium),  # type: ignore[arg-type]
                summary="{0} Current read: {1}.".format(summary_base, signal_word),
                series=_series_for_metric(recent_rows, games, opponents, series_metric),
                supporting_stats=stats,
                drilldowns=[
                    "/teams/{0}".format(team.abbreviation),
                    "/compare?mode=teams&team_a={0}&team_b={0}&season={1}".format(team.abbreviation, season),
                ],
                related_player_ids=related_ids,
                replay_target=_build_replay_target_for_recent_games(
                    db=db,
                    team=team,
                    season=season,
                    recent_rows=recent_rows,
                    source_surface="insights-trends",
                    source_id="{0}:{1}".format(team.abbreviation, card_id),
                    source_label=title,
                    return_to=return_to,
                    reason_prefix=title,
                    action_types=replay_rule.get("action_types", ()),
                    action_families=replay_rule.get("action_families", ()),
                    description_terms=replay_rule.get("description_terms", ()),
                ),
            )
        )
    return cards


def _player_rows_by_player(db: Session, team: Team, season: str) -> Dict[int, List[GamePlayerStat]]:
    rows = (
        db.query(GamePlayerStat)
        .filter(GamePlayerStat.team_id == team.id, GamePlayerStat.season == season)
        .order_by(GamePlayerStat.game_date.desc().nullslast(), GamePlayerStat.game_id.desc())
        .all()
    )
    grouped: Dict[int, List[GamePlayerStat]] = defaultdict(list)
    for row in rows:
        grouped[row.player_id].append(row)
    return grouped


def _season_rows_by_player(db: Session, team: Team, season: str) -> Dict[int, SeasonStat]:
    rows = (
        db.query(SeasonStat)
        .filter(SeasonStat.team_abbreviation == team.abbreviation, SeasonStat.season == season, SeasonStat.is_playoff == False)  # noqa: E712
        .all()
    )
    return {row.player_id: row for row in rows}


def _player_maps(db: Session, player_ids: Sequence[int], season: str) -> Dict[str, Dict[int, Any]]:
    if not player_ids:
        return {
            "players": {},
            "on_off": {},
            "clutch": {},
            "gravity": {},
            "hustle": {},
            "tracking": {},
            "play_type": {},
            "shot": {},
        }
    players = {row.id: row for row in db.query(Player).filter(Player.id.in_(list(player_ids))).all()}
    on_off = {
        row.player_id: row
        for row in db.query(PlayerOnOff).filter(PlayerOnOff.player_id.in_(list(player_ids)), PlayerOnOff.season == season).all()
    }
    clutch = {
        row.player_id: row
        for row in db.query(PlayerClutchStat).filter(PlayerClutchStat.player_id.in_(list(player_ids)), PlayerClutchStat.season == season).all()
    }
    gravity = {
        row.player_id: row
        for row in db.query(PlayerGravityStat).filter(PlayerGravityStat.player_id.in_(list(player_ids)), PlayerGravityStat.season == season).all()
    }
    hustle = {
        row.player_id: row
        for row in db.query(PlayerHustleStat).filter(PlayerHustleStat.player_id.in_(list(player_ids)), PlayerHustleStat.season == season).all()
    }
    shot = {
        row.player_id: row
        for row in db.query(PlayerShotChart).filter(PlayerShotChart.player_id.in_(list(player_ids)), PlayerShotChart.season == season).all()
    }
    tracking_rows = (
        db.query(PlayerTrackingStat)
        .filter(PlayerTrackingStat.player_id.in_(list(player_ids)), PlayerTrackingStat.season == season)
        .all()
    )
    tracking: Dict[int, List[PlayerTrackingStat]] = defaultdict(list)
    for row in tracking_rows:
        tracking[row.player_id].append(row)
    play_rows = (
        db.query(PlayerPlayTypeStat)
        .filter(PlayerPlayTypeStat.player_id.in_(list(player_ids)), PlayerPlayTypeStat.season == season)
        .all()
    )
    play_type: Dict[int, List[PlayerPlayTypeStat]] = defaultdict(list)
    for row in play_rows:
        play_type[row.player_id].append(row)
    return {
        "players": players,
        "on_off": on_off,
        "clutch": clutch,
        "gravity": gravity,
        "hustle": hustle,
        "tracking": tracking,
        "play_type": play_type,
        "shot": shot,
    }


def _lineup_context_by_player(db: Session, team: Team, season: str, player_ids: Sequence[int]) -> Dict[int, Dict[str, Optional[float]]]:
    result: Dict[int, Dict[str, Optional[float]]] = {
        player_id: {"best_lineup_net": None, "best_lineup_minutes": None} for player_id in player_ids
    }
    rows = (
        db.query(LineupStats)
        .filter(LineupStats.team_id == team.id, LineupStats.season == season, LineupStats.minutes.isnot(None))
        .all()
    )
    wanted = set(player_ids)
    for row in rows:
        ids: List[int] = []
        for token in (row.lineup_key or "").split("-"):
            try:
                ids.append(int(token))
            except ValueError:
                continue
        for player_id in wanted.intersection(ids):
            current = result[player_id]
            current_minutes = current.get("best_lineup_minutes") or 0.0
            row_minutes = float(row.minutes or 0.0)
            row_net = row.net_rating
            if row_net is not None and row_minutes >= current_minutes:
                current["best_lineup_net"] = float(row_net)
                current["best_lineup_minutes"] = row_minutes
    return result


def _aggregate_player_window(rows: Sequence[GamePlayerStat]) -> Dict[str, Optional[float]]:
    games = len(rows)
    if games == 0:
        return {
            "games": 0,
            "pts_pg": None,
            "ts_pct": None,
            "minutes_pg": None,
            "plus_minus_pg": None,
            "fg3a_rate": None,
            "tov_pg": None,
        }
    pts = _sum(row.pts for row in rows)
    fga = _sum(row.fga for row in rows)
    fta = _sum(row.fta for row in rows)
    return {
        "games": float(games),
        "pts_pg": pts / games,
        "ts_pct": _ts_pct(pts, fga, fta),
        "minutes_pg": _sum(row.min for row in rows) / games,
        "plus_minus_pg": _sum(row.plus_minus for row in rows) / games,
        "fg3a_rate": _three_point_rate(_sum(row.fg3a for row in rows), fga),
        "tov_pg": _sum(row.tov for row in rows) / games,
    }


def _shot_quality_delta(db: Session, row: Optional[PlayerShotChart], season: str) -> Tuple[Optional[float], str]:
    if row is None or not row.shots:
        return None, "missing"
    try:
        store = _load_baselines(db, season, row.season_type or "Regular Season")
        points = 0.0
        expected = 0.0
        for shot in row.shots or []:
            points += _points(shot)
            baseline, _ = _expected_baseline(shot, row.season_type or "Regular Season", store)
            expected += baseline.pps
        attempts = len(row.shots or [])
        if attempts == 0:
            return None, "missing"
        return (points - expected) / attempts, "ready"
    except Exception:
        return None, "partial"


def _top_play_type_signal(rows: Sequence[PlayerPlayTypeStat]) -> Tuple[Optional[float], str]:
    if not rows:
        return None, "missing"
    viable = [row for row in rows if row.possessions and row.possessions >= 10 and row.ppp is not None]
    if not viable:
        return None, "partial"
    top = max(viable, key=lambda row: float(row.possessions or 0.0))
    return float(top.ppp or 0.0) - 1.0, "ready"


def _tracking_signal(rows: Sequence[PlayerTrackingStat]) -> Tuple[Optional[float], str]:
    if not rows:
        return None, "missing"
    touches = _sum(row.touches for row in rows)
    drives = _sum(row.drives for row in rows)
    catch_shoot = _sum(row.catch_shoot_fga for row in rows)
    passes = _sum(row.passes_made for row in rows)
    minutes = _sum(row.minutes for row in rows) or 1.0
    signal = ((touches * 0.015) + (drives * 0.06) + (catch_shoot * 0.08) + (passes * 0.01)) / max(1.0, minutes / 10.0)
    return signal, "ready"


def _hustle_signal(row: Optional[PlayerHustleStat]) -> Tuple[Optional[float], str]:
    if row is None:
        return None, "missing"
    minutes = float(row.minutes or 1.0)
    signal = (
        float(row.deflections or 0.0)
        + float(row.screen_assists or 0.0)
        + float(row.loose_balls_recovered or 0.0)
        + float(row.box_outs or 0.0) * 0.5
    ) / max(1.0, minutes / 10.0)
    return signal, "ready"


def _contribution(signal: str, value: Optional[float], contribution: float, note: str) -> TrendDriverContribution:
    return TrendDriverContribution(
        signal=signal,
        label=SIGNAL_LABELS.get(signal, signal.replace("_", " ").title()),
        value=_round(value, 3),
        contribution=_round(contribution, 3) or 0.0,
        note=note,
    )


def _trend_label(score: float) -> str:
    if score >= 1.0:
        return "Surging"
    if score >= 0.35:
        return "Rising"
    if score <= -1.0:
        return "Sliding"
    if score <= -0.35:
        return "Cooling"
    return "Stable"


def _build_player_movers(
    db: Session,
    team: Team,
    season: str,
    window_games: int,
) -> Tuple[List[TrendPlayerRow], Dict[int, TrendPlayerDetail], List[str]]:
    game_rows = _player_rows_by_player(db, team, season)
    season_rows = _season_rows_by_player(db, team, season)
    player_ids = sorted(set(game_rows.keys()).union(season_rows.keys()))
    maps = _player_maps(db, player_ids, season)
    lineup_context = _lineup_context_by_player(db, team, season, player_ids)
    warnings: List[str] = []

    movers: List[TrendPlayerRow] = []
    details: Dict[int, TrendPlayerDetail] = {}
    shot_missing = 0
    gravity_missing = 0
    tracking_missing = 0
    play_type_missing = 0

    for player_id in player_ids:
        player = maps["players"].get(player_id)
        season_row = season_rows.get(player_id)
        rows = game_rows.get(player_id, [])
        recent_rows = rows[:window_games]
        prior_rows = rows[window_games : window_games * 2]
        recent = _aggregate_player_window(recent_rows)
        prior = _aggregate_player_window(prior_rows)
        baseline_pts = season_row.pts_pg if season_row else prior.get("pts_pg")
        baseline_ts = season_row.ts_pct if season_row else prior.get("ts_pct")
        baseline_minutes = season_row.min_pg if season_row else prior.get("minutes_pg")
        baseline_plus_minus = prior.get("plus_minus_pg")

        scoring_delta = None if recent.get("pts_pg") is None or baseline_pts is None else float(recent["pts_pg"]) - float(baseline_pts)
        efficiency_delta = None if recent.get("ts_pct") is None or baseline_ts is None else float(recent["ts_pct"]) - float(baseline_ts)
        role_delta = None if recent.get("minutes_pg") is None or baseline_minutes is None else float(recent["minutes_pg"]) - float(baseline_minutes)
        plus_minus_delta = None if recent.get("plus_minus_pg") is None or baseline_plus_minus is None else float(recent["plus_minus_pg"]) - float(baseline_plus_minus)

        on_off = maps["on_off"].get(player_id)
        clutch = maps["clutch"].get(player_id)
        gravity = maps["gravity"].get(player_id)
        hustle_value, hustle_status = _hustle_signal(maps["hustle"].get(player_id))
        tracking_value, tracking_status = _tracking_signal(maps["tracking"].get(player_id, []))
        play_type_value, play_type_status = _top_play_type_signal(maps["play_type"].get(player_id, []))
        shot_quality, shot_status = _shot_quality_delta(db, maps["shot"].get(player_id), season)
        lineup = lineup_context.get(player_id, {})

        if shot_status == "missing":
            shot_missing += 1
        if gravity is None:
            gravity_missing += 1
        if tracking_status == "missing":
            tracking_missing += 1
        if play_type_status == "missing":
            play_type_missing += 1

        components = [
            _contribution("scoring", scoring_delta, _clamp((scoring_delta or 0.0) / 5.0, -1.2, 1.2), "Recent scoring versus season baseline."),
            _contribution("efficiency", efficiency_delta, _clamp((efficiency_delta or 0.0) * 10.0, -1.2, 1.2), "Recent true-shooting movement."),
            _contribution("role", role_delta, _clamp((role_delta or 0.0) / 8.0, -0.9, 0.9), "Minute load movement."),
            _contribution("impact", on_off.on_off_net if on_off else plus_minus_delta, _clamp(((on_off.on_off_net if on_off else plus_minus_delta) or 0.0) / 12.0, -1.0, 1.0), "On/off when available; plus-minus trend as fallback."),
            _contribution("lineup", lineup.get("best_lineup_net"), _clamp((lineup.get("best_lineup_net") or 0.0) / 18.0, -0.8, 0.8), "Best qualifying lineup net rating."),
            _contribution("clutch", clutch.clutch_net_rating if clutch else (season_row.clutch_plus_minus if season_row else None), _clamp(((clutch.clutch_net_rating if clutch else (season_row.clutch_plus_minus if season_row else None)) or 0.0) / 15.0, -0.7, 0.7), "Official clutch row or PBP-derived clutch fallback."),
            _contribution("shot_quality", shot_quality, _clamp((shot_quality or 0.0) * 2.5, -0.8, 0.8), "{0} support from {1}.".format(SHOT_QUALITY_VERSION, "shot chart" if shot_status == "ready" else "partial shot chart")),
            _contribution("play_type", play_type_value, _clamp((play_type_value or 0.0) * 1.5, -0.6, 0.6), "Persisted play-type PPP versus neutral 1.0."),
            _contribution("tracking", tracking_value, _clamp((tracking_value or 0.0) / 2.0, -0.5, 0.5), "Touches, drives, passing, and catch-shoot tracking context."),
            _contribution("hustle", hustle_value, _clamp((hustle_value or 0.0) / 2.0, -0.4, 0.4), "Deflections, screen assists, loose balls, and box-outs."),
            _contribution("gravity", gravity.overall_gravity if gravity else None, _clamp(((gravity.overall_gravity if gravity else 50.0) - 50.0) / 25.0, -0.7, 0.7), "Official or CourtVue proxy gravity."),
        ]
        components.sort(key=lambda item: abs(item.contribution), reverse=True)
        score = sum(item.contribution for item in components)
        top = next((item for item in components if abs(item.contribution) > 0.001), components[0])
        coverage_ready = sum(
            [
                len(recent_rows) >= max(3, min(window_games, 5)),
                on_off is not None,
                clutch is not None or (season_row is not None and season_row.clutch_pts is not None),
                shot_status == "ready",
                gravity is not None,
                tracking_status == "ready",
                play_type_status == "ready",
                hustle_status == "ready",
            ]
        )
        confidence = "high" if coverage_ready >= 6 else "medium" if coverage_ready >= 3 else "low"
        row_warnings: List[str] = []
        if len(recent_rows) < min(window_games, 3):
            row_warnings.append("Recent game-log sample is thin.")
        if shot_status != "ready":
            row_warnings.append("Shot quality is {0}.".format(shot_status))
        if gravity is None:
            row_warnings.append("Gravity row missing.")

        mover = TrendPlayerRow(
            player_id=player_id,
            player_name=player.full_name if player else "Player {0}".format(player_id),
            team_abbreviation=team.abbreviation,
            position=player.position if player else None,
            trend_score=_round(score, 3) or 0.0,
            trend_label=_trend_label(score),
            primary_signal=top.signal,
            confidence=confidence,  # type: ignore[arg-type]
            recent_games=len(recent_rows),
            recent_pts_pg=_round(recent.get("pts_pg"), 1),
            baseline_pts_pg=_round(baseline_pts, 1),
            recent_ts_pct=_round(recent.get("ts_pct"), 3),
            baseline_ts_pct=_round(baseline_ts, 3),
            recent_minutes_pg=_round(recent.get("minutes_pg"), 1),
            baseline_minutes_pg=_round(baseline_minutes, 1),
            on_off_net=_round(on_off.on_off_net if on_off else None, 2),
            gravity_score=_round(gravity.overall_gravity if gravity else None, 1),
            shot_quality_delta=_round(shot_quality, 3),
            driver_contributions=components[:8],
            warnings=row_warnings,
        )
        movers.append(mover)

        foundation = [
            TrendFoundationSignal(signal="game_log", label="Recent Game Logs", value=float(len(recent_rows)), context="{0} games in the selected window.".format(len(recent_rows)), status="ready" if recent_rows else "missing"),
            TrendFoundationSignal(signal="season", label="Season Baseline", value=_round(baseline_pts, 1), context="Season stat row anchors scoring, efficiency, and role baselines.", status="ready" if season_row else "partial"),
            TrendFoundationSignal(signal="on_off", label="On/Off", value=_round(on_off.on_off_net if on_off else None, 2), context="Team performance swing with the player on court.", status="ready" if on_off else "missing"),
            TrendFoundationSignal(signal="lineup", label="Lineup Fit", value=_round(lineup.get("best_lineup_net"), 2), context="Best qualifying lineup net rating containing the player.", status="ready" if lineup.get("best_lineup_net") is not None else "missing"),
            TrendFoundationSignal(signal="clutch", label="Clutch", value=_round(clutch.clutch_net_rating if clutch else (season_row.clutch_plus_minus if season_row else None), 2), context="Official clutch dashboard row, falling back to PBP-derived clutch plus-minus.", status="ready" if clutch else "partial" if season_row and season_row.clutch_pts is not None else "missing"),
            TrendFoundationSignal(signal="shot_quality", label="Shot Quality", value=_round(shot_quality, 3), context="{0} shot quality over persisted shot chart attempts.".format(SHOT_QUALITY_VERSION), status=shot_status),  # type: ignore[arg-type]
            TrendFoundationSignal(signal="play_type", label="Play Type", value=_round(play_type_value, 3), context="Primary persisted play-type PPP versus 1.0.", status=play_type_status),  # type: ignore[arg-type]
            TrendFoundationSignal(signal="tracking", label="Tracking", value=_round(tracking_value, 3), context="Touches, drives, passing, and catch-shoot activity.", status=tracking_status),  # type: ignore[arg-type]
            TrendFoundationSignal(signal="hustle", label="Hustle", value=_round(hustle_value, 3), context="Deflections, screens, loose balls, and box-outs.", status=hustle_status),  # type: ignore[arg-type]
            TrendFoundationSignal(signal="gravity", label="Gravity", value=_round(gravity.overall_gravity if gravity else None, 1), context="Official or CourtVue proxy gravity.", status="ready" if gravity else "missing"),
        ]
        recent_series = [
            TrendSeriesPoint(
                label=(row.game_date.isoformat() if row.game_date else row.game_id[-4:]),
                value=float(row.pts or 0.0),
            )
            for row in list(recent_rows)[::-1]
        ]
        details[player_id] = TrendPlayerDetail(
            row=mover,
            foundation=foundation,
            recent_series=recent_series,
            drilldowns=[
                "/players/{0}".format(player_id),
                "/insights?tab=trajectory&team={0}&season={1}&player_id={2}".format(team.abbreviation, season, player_id),
                "/insights?tab=usage&team={0}&season={1}&player_id={2}".format(team.abbreviation, season, player_id),
            ],
        )

    movers.sort(key=lambda row: abs(row.trend_score), reverse=True)
    if player_ids and shot_missing >= len(player_ids) * 0.5:
        warnings.append("Shot-quality coverage is partial for this roster, so shot-quality movers are directional.")
    if player_ids and gravity_missing >= len(player_ids) * 0.5:
        warnings.append("Gravity coverage is partial for this roster.")
    if player_ids and tracking_missing >= len(player_ids) * 0.5:
        warnings.append("Tracking coverage is partial for this roster.")
    if player_ids and play_type_missing >= len(player_ids) * 0.5:
        warnings.append("Play-type coverage is partial for this roster.")
    return movers, details, warnings


def _filter_movers(rows: Sequence[TrendPlayerRow], signal: Optional[str]) -> List[TrendPlayerRow]:
    if not signal:
        return list(rows)
    normalized = signal.strip()
    if not normalized:
        return list(rows)
    allowed = OPPORTUNITY_SIGNAL_MAP.get(normalized, {normalized})
    filtered = [row for row in rows if row.primary_signal in allowed]
    return filtered if filtered else list(rows)


def _data_status(cards: Sequence[TrendCard], movers: Sequence[TrendPlayerRow], warnings: Sequence[str]) -> str:
    if not cards and not movers:
        return "missing"
    if not movers:
        return "limited"
    if warnings:
        return "partial"
    ready_count = sum(1 for row in movers if row.confidence == "high")
    if ready_count >= max(1, len(movers) // 3):
        return "ready"
    return "partial"


def build_trend_cards_report(
    db: Session,
    team_abbr: str,
    season: str,
    window_games: int,
    player_id: Optional[int] = None,
    signal: Optional[str] = None,
) -> TrendCardsResponse:
    team = _fetch_team(db, team_abbr)
    watermark = _season_watermark(db, season)
    cache_key = "trend_cards:{0}:{1}:{2}:{3}:{4}:{5}".format(
        team.abbreviation,
        season,
        window_games,
        player_id or "none",
        signal or "all",
        watermark,
    )
    cached = CacheManager.get(cache_key)
    if cached:
        return TrendCardsResponse(**cached)

    team_rows = _team_rows(db, team.id, season)
    if not team_rows:
        raise HTTPException(status_code=404, detail="No team game stats found for {0} in {1}.".format(team.abbreviation, season))

    game_ids = [row.game_id for row in team_rows]
    games = _games_by_id(db, game_ids)
    opponents = _opponent_rows_by_game(db, team.id, game_ids)
    recent_rows = team_rows[:window_games]
    baseline_rows = team_rows[window_games : window_games * 2] or team_rows[window_games:] or team_rows
    all_movers, detail_map, coverage_warnings = _build_player_movers(db, team, season, window_games)
    player_movers = _filter_movers(all_movers, signal)[:12]
    cards = _build_team_cards(
        db=db,
        team=team,
        season=season,
        window_games=window_games,
        team_rows=team_rows,
        recent_rows=recent_rows,
        baseline_rows=baseline_rows,
        games=games,
        opponents=opponents,
        movers=all_movers,
    )
    recent_profile = _avg_profile(recent_rows, opponents)
    baseline_profile = _avg_profile(baseline_rows, opponents)
    overview = TrendOverview(
        headline="{0} trend board: {1} recent games, {2} player movers.".format(
            team.abbreviation,
            len(recent_rows),
            len(all_movers),
        ),
        recent_record=_record(recent_rows),
        recent_net_rating=_round(recent_profile.get("net_rating"), 2),
        baseline_net_rating=_round(baseline_profile.get("net_rating"), 2),
        recent_ts_pct=_round(recent_profile.get("ts_pct"), 3),
        baseline_ts_pct=_round(baseline_profile.get("ts_pct"), 3),
        recent_pace=_round(recent_profile.get("pace"), 1),
        baseline_pace=_round(baseline_profile.get("pace"), 1),
        games_in_window=len(recent_rows),
        player_count=len(all_movers),
    )
    pinned_detail = detail_map.get(player_id) if player_id is not None else (detail_map.get(player_movers[0].player_id) if player_movers else None)
    warnings: List[str] = []
    warnings.extend(coverage_warnings)
    if len(team_rows) < window_games:
        warnings.append("Only {0} games were available for the selected trend window.".format(len(team_rows)))
    if signal and player_movers == list(all_movers)[:12]:
        warnings.append("No player movers matched signal '{0}', so the board is showing all movers.".format(signal))

    methodology = TrendMethodology(
        version=TREND_METHODOLOGY_VERSION,
        window_games=min(window_games, len(team_rows)),
        scoring_inputs=[
            "recent game logs",
            "season stats",
            "on/off",
            "lineup stats",
            "clutch",
            SHOT_QUALITY_VERSION,
            "play type",
            "tracking",
            "hustle",
            "gravity",
        ],
        coverage_notes=[
            "Signals degrade to partial or missing instead of triggering live sync.",
            "Player trend score is directional and intentionally decomposed by visible drivers.",
        ],
    )
    response = TrendCardsResponse(
        team_abbreviation=team.abbreviation,
        team_name=team.name,
        season=season,
        data_status=_data_status(cards, player_movers, warnings),  # type: ignore[arg-type]
        overview=overview,
        window_games=min(window_games, len(team_rows)),
        cards=cards,
        player_movers=player_movers,
        pinned_player=pinned_detail,
        methodology=methodology,
        warnings=warnings,
    )
    CacheManager.set(cache_key, response.model_dump(), 900)
    return response
