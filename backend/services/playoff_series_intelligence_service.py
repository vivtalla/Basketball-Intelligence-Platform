"""Series-level playoff intelligence for the Playoff Command Center.

The service intentionally composes existing playoff rows only. It does not
mutate bracket state, run new sync jobs, or require a schema migration.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import (
    GameLog,
    LineupStats,
    Player,
    PlayoffSeries,
    SeasonStat,
    Team,
    TeamSeasonStat,
    TeamShootingSplitStat,
)
from models.methodology import AnalysisMetadata, DriverBreakdown, SampleContext
from models.playoffs import (
    PlayoffAdjustmentSignal,
    PlayoffGameMargin,
    PlayoffLineupEntry,
    PlayoffMetricEdge,
    PlayoffSeriesIntelligenceResponse,
    PlayoffSeriesDataCoverage,
    PlayoffSeriesPulse,
    PlayoffSeriesTeamRef,
    PlayoffShotDietEntry,
    PlayoffStarBurdenEntry,
    PlayoffTacticalEdge,
)


METHODOLOGY_VERSION = "playoff_series_intelligence_v1"
RECOMMENDED_COMPLETED_GAMES = 4
MIN_LINEUP_POSSESSIONS = 25


def _safe_float(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _rate(numerator: float, denominator: float) -> Optional[float]:
    if denominator <= 0:
        return None
    return numerator / denominator


def _team_map(db: Session, team_ids: List[int]) -> Dict[int, Team]:
    if not team_ids:
        return {}
    rows = db.query(Team).filter(Team.id.in_(team_ids)).all()
    return {team.id: team for team in rows}


def _team_abbr(team: Optional[Team]) -> Optional[str]:
    return team.abbreviation if team is not None else None


def _winner(game: GameLog) -> Optional[int]:
    if game.home_score is None or game.away_score is None:
        return None
    if game.home_score > game.away_score:
        return game.home_team_id
    if game.away_score > game.home_score:
        return game.away_team_id
    return None


def _series_games(db: Session, series_id: str) -> List[GameLog]:
    return (
        db.query(GameLog)
        .filter(GameLog.series_id == series_id)
        .order_by(GameLog.series_game_num.asc(), GameLog.game_date.asc(), GameLog.game_id.asc())
        .all()
    )


def _team_season_stat(
    db: Session, team_id: Optional[int], season: str, is_playoff: bool
) -> Optional[TeamSeasonStat]:
    if team_id is None:
        return None
    return (
        db.query(TeamSeasonStat)
        .filter(
            TeamSeasonStat.team_id == team_id,
            TeamSeasonStat.season == season,
            TeamSeasonStat.is_playoff == is_playoff,
        )
        .first()
    )


def _team_player_rows(
    db: Session, team_abbr: Optional[str], season: str, is_playoff: bool
) -> List[SeasonStat]:
    if not team_abbr:
        return []
    return (
        db.query(SeasonStat)
        .filter(
            SeasonStat.season == season,
            SeasonStat.team_abbreviation == team_abbr,
            SeasonStat.is_playoff == is_playoff,
        )
        .all()
    )


def _team_player_aggregate(rows: List[SeasonStat]) -> Dict[str, Optional[float]]:
    fga = sum(float(row.fga or 0) for row in rows)
    fta = sum(float(row.fta or 0) for row in rows)
    fg3a = sum(float(row.fg3a or 0) for row in rows)
    pts = sum(float(row.pts or 0) for row in rows)
    usage_weight = sum(float(row.min_total or 0) for row in rows if row.usg_pct is not None)
    weighted_usage = sum(float(row.usg_pct or 0) * float(row.min_total or 0) for row in rows)
    return {
        "ftr": _rate(fta, fga),
        "par3": _rate(fg3a, fga),
        "points": pts if pts > 0 else None,
        "usage": _rate(weighted_usage, usage_weight),
    }


def _metric_value(
    key: str,
    team_stat: Optional[TeamSeasonStat],
    aggregate: Dict[str, Optional[float]],
) -> Optional[float]:
    if key in aggregate:
        return aggregate[key]
    if team_stat is None:
        return None
    return _safe_float(getattr(team_stat, key, None))


def _edge_team(
    top_value: Optional[float],
    bottom_value: Optional[float],
    top_abbr: Optional[str],
    bottom_abbr: Optional[str],
    higher_is_better: Optional[bool],
) -> Tuple[Optional[str], Optional[float]]:
    if higher_is_better is None or top_value is None or bottom_value is None:
        return None, None
    diff = top_value - bottom_value
    if diff == 0:
        return None, 0.0
    top_has_edge = diff > 0 if higher_is_better else diff < 0
    return (top_abbr if top_has_edge else bottom_abbr), abs(diff)


def _build_metric_edges(
    db: Session,
    season: str,
    top_team: Optional[Team],
    bottom_team: Optional[Team],
) -> List[PlayoffMetricEdge]:
    top_playoff = _team_season_stat(db, top_team.id if top_team else None, season, True)
    bottom_playoff = _team_season_stat(db, bottom_team.id if bottom_team else None, season, True)
    top_regular = _team_season_stat(db, top_team.id if top_team else None, season, False)
    bottom_regular = _team_season_stat(db, bottom_team.id if bottom_team else None, season, False)
    top_po_agg = _team_player_aggregate(_team_player_rows(db, _team_abbr(top_team), season, True))
    bottom_po_agg = _team_player_aggregate(_team_player_rows(db, _team_abbr(bottom_team), season, True))
    top_reg_agg = _team_player_aggregate(_team_player_rows(db, _team_abbr(top_team), season, False))
    bottom_reg_agg = _team_player_aggregate(_team_player_rows(db, _team_abbr(bottom_team), season, False))

    specs = [
        ("net_rating", "Net rating", "rating", True),
        ("efg_pct", "eFG%", "pct", True),
        ("tov_pct", "TOV%", "pct", False),
        ("oreb_pct", "OREB%", "pct", True),
        ("ftr", "Free throw rate", "pct", True),
        ("par3", "3-point attempt rate", "pct", True),
        ("pace", "Pace", "number", None),
        ("ts_pct", "TS%", "pct", True),
    ]

    metrics: List[PlayoffMetricEdge] = []
    for key, label, unit, higher_is_better in specs:
        top_value = _metric_value(key, top_playoff, top_po_agg)
        bottom_value = _metric_value(key, bottom_playoff, bottom_po_agg)
        top_regular_value = _metric_value(key, top_regular, top_reg_agg)
        bottom_regular_value = _metric_value(key, bottom_regular, bottom_reg_agg)
        edge_abbr, edge_amount = _edge_team(
            top_value, bottom_value, _team_abbr(top_team), _team_abbr(bottom_team), higher_is_better
        )
        metrics.append(
            PlayoffMetricEdge(
                key=key,
                label=label,
                unit=unit,
                higher_is_better=higher_is_better,
                top_value=top_value,
                bottom_value=bottom_value,
                top_regular_value=top_regular_value,
                bottom_regular_value=bottom_regular_value,
                top_delta_vs_regular=(
                    top_value - top_regular_value
                    if top_value is not None and top_regular_value is not None
                    else None
                ),
                bottom_delta_vs_regular=(
                    bottom_value - bottom_regular_value
                    if bottom_value is not None and bottom_regular_value is not None
                    else None
                ),
                edge_team_abbr=edge_abbr,
                edge_amount=edge_amount,
            )
        )
    return metrics


def _position_bucket(position: Optional[str]) -> Optional[str]:
    if not position:
        return None
    value = position.upper()
    if "C" in value:
        return "C"
    if "F" in value:
        return "F"
    if "G" in value:
        return "G"
    return None


def _player_lookup(db: Session, player_ids: List[int]) -> Dict[int, Player]:
    if not player_ids:
        return {}
    rows = db.query(Player).filter(Player.id.in_(player_ids)).all()
    return {row.id: row for row in rows}


def _star_burden_for_team(
    db: Session,
    season: str,
    team_abbr: Optional[str],
    limit: int = 5,
) -> List[PlayoffStarBurdenEntry]:
    rows = _team_player_rows(db, team_abbr, season, True)
    if not team_abbr or not rows:
        return []
    players = _player_lookup(db, [row.player_id for row in rows])
    total_points = sum(float(row.pts or 0) for row in rows)
    total_usage = sum(float(row.usg_pct or 0) for row in rows if row.usg_pct is not None)
    sorted_rows = sorted(
        rows,
        key=lambda row: (
            float(row.usg_pct or 0),
            float(row.pts_pg or 0),
            float(row.min_pg or 0),
        ),
        reverse=True,
    )
    entries: List[PlayoffStarBurdenEntry] = []
    for row in sorted_rows[:limit]:
        player = players.get(row.player_id)
        name = player.full_name if player is not None else str(row.player_id)
        position = player.position if player is not None else None
        entries.append(
            PlayoffStarBurdenEntry(
                player_id=row.player_id,
                player_name=name,
                team_abbreviation=team_abbr,
                position=position,
                position_bucket=_position_bucket(position),
                gp=int(row.gp or 0),
                min_pg=_safe_float(row.min_pg),
                usg_pct=_safe_float(row.usg_pct),
                pts_pg=_safe_float(row.pts_pg),
                ts_pct=_safe_float(row.ts_pct),
                bpm=_safe_float(row.bpm),
                share_team_points=_rate(float(row.pts or 0), total_points) if total_points > 0 else None,
                share_team_usage=_rate(float(row.usg_pct or 0), total_usage) if total_usage > 0 else None,
            )
        )
    return entries


def _shooting_split_rows(
    db: Session, team_id: Optional[int], season: str
) -> List[TeamShootingSplitStat]:
    if team_id is None:
        return []
    return (
        db.query(TeamShootingSplitStat)
        .filter(
            TeamShootingSplitStat.team_id == team_id,
            TeamShootingSplitStat.season == season,
            TeamShootingSplitStat.is_playoff == True,  # noqa: E712
        )
        .all()
    )


def _share_for_tokens(rows: List[TeamShootingSplitStat], total_fga: float, tokens: List[str]) -> Optional[float]:
    if total_fga <= 0:
        return None
    matched = 0.0
    for row in rows:
        text = "{} {}".format(row.split_value or "", row.label or "").lower()
        if any(token in text for token in tokens):
            matched += float(row.fga or 0)
    return _rate(matched, total_fga)


def _assisted_rate(rows: List[TeamShootingSplitStat]) -> Optional[float]:
    weighted = 0.0
    fgm = 0.0
    for row in rows:
        if row.pct_ast_fgm is None:
            continue
        makes = float(row.fgm or 0)
        if makes <= 0:
            continue
        weighted += float(row.pct_ast_fgm) * makes
        fgm += makes
    return _rate(weighted, fgm)


def _shot_diet_for_team(
    db: Session,
    season: str,
    team: Optional[Team],
    aggregate: Dict[str, Optional[float]],
) -> PlayoffShotDietEntry:
    abbr = _team_abbr(team) or "TBD"
    rows = _shooting_split_rows(db, team.id if team is not None else None, season)
    shot_rows = [
        row for row in rows
        if "shot" in (row.split_family or "").lower() or "dashboard" in (row.split_family or "").lower()
    ]
    total_fga = sum(float(row.fga or 0) for row in shot_rows)
    notes: List[str] = []
    if total_fga <= 0:
        notes.append("No playoff team shooting-split rows yet; showing roster-derived FTr/3PAr only.")
    return PlayoffShotDietEntry(
        team_abbreviation=abbr,
        rim_frequency=_share_for_tokens(shot_rows, total_fga, ["restricted"]),
        paint_frequency=_share_for_tokens(shot_rows, total_fga, ["paint"]),
        three_point_frequency=aggregate.get("par3"),
        corner_three_frequency=_share_for_tokens(shot_rows, total_fga, ["corner 3", "corner three"]),
        above_break_three_frequency=_share_for_tokens(shot_rows, total_fga, ["above the break"]),
        ftr=aggregate.get("ftr"),
        par3=aggregate.get("par3"),
        assisted_fg_rate=_assisted_rate(rows),
        notes=notes,
    )


def _lineup_names(db: Session, lineup_key: str) -> List[str]:
    ids: List[int] = []
    for piece in lineup_key.split("-"):
        try:
            ids.append(int(piece))
        except ValueError:
            continue
    players = _player_lookup(db, ids)
    return [players[player_id].full_name if player_id in players else str(player_id) for player_id in ids]


def _lineup_entries_for_team(
    db: Session,
    season: str,
    team: Optional[Team],
) -> Tuple[List[PlayoffLineupEntry], List[PlayoffLineupEntry]]:
    if team is None:
        return [], []
    rows = (
        db.query(LineupStats)
        .filter(
            LineupStats.season == season,
            LineupStats.team_id == team.id,
            LineupStats.is_playoff == True,  # noqa: E712
        )
        .all()
    )
    eligible = [row for row in rows if row.net_rating is not None]
    eligible.sort(key=lambda row: float(row.net_rating or 0), reverse=True)

    def serialize(row: LineupStats, label: str) -> PlayoffLineupEntry:
        return PlayoffLineupEntry(
            team_abbreviation=team.abbreviation,
            lineup_key=row.lineup_key,
            player_names=_lineup_names(db, row.lineup_key),
            minutes=_safe_float(row.minutes),
            possessions=int(row.possessions or 0) if row.possessions is not None else None,
            net_rating=_safe_float(row.net_rating),
            ortg=_safe_float(row.ortg),
            drtg=_safe_float(row.drtg),
            label=label,
        )

    best = [serialize(row, "best") for row in eligible[:2]]
    worst_source = list(reversed(eligible[-2:])) if len(eligible) > 2 else []
    worst = [serialize(row, "pressure point") for row in worst_source]
    return best, worst


def _series_pulse(
    series: PlayoffSeries,
    games: List[GameLog],
    team_lookup: Dict[int, Team],
) -> PlayoffSeriesPulse:
    top_team = team_lookup.get(series.top_seed_team_id)
    bottom_team = team_lookup.get(series.bottom_seed_team_id)
    top_abbr = _team_abbr(top_team) or "Top seed"
    bottom_abbr = _team_abbr(bottom_team) or "Bottom seed"
    top_wins = int(series.top_wins or 0)
    bottom_wins = int(series.bottom_wins or 0)
    completed = [
        game for game in games
        if game.home_score is not None and game.away_score is not None
    ]

    leader: Optional[str] = None
    trailer: Optional[str] = None
    if top_wins > bottom_wins:
        leader, trailer = top_abbr, bottom_abbr
    elif bottom_wins > top_wins:
        leader, trailer = bottom_abbr, top_abbr

    next_game = len(completed) + 1 if series.status != "closed" and len(completed) < 7 else None
    max_wins = max(top_wins, bottom_wins)
    min_wins = min(top_wins, bottom_wins)
    is_elimination = series.status == "active" and max_wins == 3 and min_wins < 3
    is_swing = series.status == "active" and top_wins == bottom_wins and next_game is not None

    if series.status == "closed":
        winner = leader or "Winner"
        summary = "{} closed the series {}-{}.".format(winner, max_wins, min_wins)
    elif leader:
        summary = "{} leads {} {}-{}.".format(leader, trailer, max_wins, min_wins)
    elif series.status == "scheduled":
        summary = "{} vs {} has not tipped yet.".format(top_abbr, bottom_abbr)
    else:
        summary = "Series tied {}-{} between {} and {}.".format(top_wins, bottom_wins, top_abbr, bottom_abbr)

    margins: List[PlayoffGameMargin] = []
    for game in completed:
        winner_id = _winner(game)
        winner_team = team_lookup.get(winner_id) if winner_id is not None else None
        margin = None
        if game.home_score is not None and game.away_score is not None:
            margin = abs(int(game.home_score) - int(game.away_score))
        margins.append(
            PlayoffGameMargin(
                game_num=game.series_game_num,
                winner_team_abbr=_team_abbr(winner_team),
                margin=margin,
            )
        )

    last_note = None
    if margins:
        last = margins[-1]
        if last.winner_team_abbr and last.margin is not None:
            last_note = "{} won Game {} by {}.".format(
                last.winner_team_abbr,
                last.game_num if last.game_num is not None else len(margins),
                last.margin,
            )

    return PlayoffSeriesPulse(
        summary=summary,
        next_game_number=next_game,
        leader_team_abbr=leader,
        trailing_team_abbr=trailer,
        is_elimination_game=is_elimination,
        is_swing_game=is_swing,
        completed_games=len(completed),
        margin_by_game=margins,
        last_game_note=last_note,
    )


def _tactical_edges(
    metrics: List[PlayoffMetricEdge],
    stars: List[PlayoffStarBurdenEntry],
    warnings: List[str],
) -> List[PlayoffTacticalEdge]:
    edges: List[PlayoffTacticalEdge] = []
    thresholds = {
        "net_rating": 3.0,
        "efg_pct": 0.02,
        "tov_pct": 0.015,
        "oreb_pct": 0.025,
        "ftr": 0.05,
        "par3": 0.06,
        "ts_pct": 0.02,
    }
    for metric in metrics:
        if not metric.edge_team_abbr or metric.edge_amount is None:
            continue
        threshold = thresholds.get(metric.key, 0.0)
        if metric.edge_amount < threshold:
            continue
        pretty_amount = metric.edge_amount * 100 if metric.unit == "pct" else metric.edge_amount
        suffix = "percentage points" if metric.unit == "pct" else "points"
        edges.append(
            PlayoffTacticalEdge(
                edge_type="four_factor",
                title="{} owns the {} edge".format(metric.edge_team_abbr, metric.label),
                team_abbreviation=metric.edge_team_abbr,
                summary="Current playoff sample shows a {:.1f} {} gap.".format(pretty_amount, suffix),
                metric_key=metric.key,
                impact_score=round(pretty_amount, 2),
            )
        )

    for star in stars[:4]:
        if star.share_team_points is not None and star.share_team_points >= 0.28:
            edges.append(
                PlayoffTacticalEdge(
                    edge_type="star_burden",
                    title="{} is carrying scoring burden".format(star.player_name),
                    team_abbreviation=star.team_abbreviation,
                    summary="{:.0f}% of team playoff points are flowing through him.".format(
                        star.share_team_points * 100
                    ),
                    metric_key="share_team_points",
                    impact_score=round(star.share_team_points * 100, 1),
                )
            )

    if not edges:
        edges.append(
            PlayoffTacticalEdge(
                edge_type="sample",
                title="No clean tactical edge yet",
                summary=warnings[0] if warnings else "The current sample is too even or too thin for a strong read.",
                impact_score=0.0,
            )
        )
    return edges[:6]


def _adjustment_signals(
    pulse: PlayoffSeriesPulse,
    metrics: List[PlayoffMetricEdge],
    best_lineups: List[PlayoffLineupEntry],
    worst_lineups: List[PlayoffLineupEntry],
) -> List[PlayoffAdjustmentSignal]:
    signals: List[PlayoffAdjustmentSignal] = []
    if pulse.is_elimination_game and pulse.leader_team_abbr:
        signals.append(
            PlayoffAdjustmentSignal(
                title="Elimination pressure",
                summary="Game {} can end the series; expect shorter rotations and matchup hunting.".format(
                    pulse.next_game_number or "next"
                ),
                team_abbreviation=pulse.leader_team_abbr,
                confidence="high",
            )
        )
    elif pulse.is_swing_game:
        signals.append(
            PlayoffAdjustmentSignal(
                title="Swing-game leverage",
                summary="Series is tied, so the next game likely changes the tactical baseline.",
                confidence="high",
            )
        )

    for metric in metrics:
        if metric.key in ("par3", "ftr") and metric.edge_team_abbr and metric.edge_amount is not None:
            if metric.edge_amount >= (0.06 if metric.key == "par3" else 0.05):
                signals.append(
                    PlayoffAdjustmentSignal(
                        title="Shot diet lever: {}".format(metric.label),
                        summary="{} has the clearer {} separation so far.".format(
                            metric.edge_team_abbr, metric.label
                        ),
                        team_abbreviation=metric.edge_team_abbr,
                        confidence="medium",
                    )
                )

    if best_lineups:
        lineup = best_lineups[0]
        signals.append(
            PlayoffAdjustmentSignal(
                title="Lineup to protect",
                summary="{}'s best logged group is +{:.1f} net in {} possessions.".format(
                    lineup.team_abbreviation or "A team",
                    lineup.net_rating or 0.0,
                    lineup.possessions or 0,
                ),
                team_abbreviation=lineup.team_abbreviation,
                confidence="medium" if (lineup.possessions or 0) >= MIN_LINEUP_POSSESSIONS else "low",
            )
        )
    if worst_lineups:
        lineup = worst_lineups[0]
        signals.append(
            PlayoffAdjustmentSignal(
                title="Lineup pressure point",
                summary="{} has a logged group at {:.1f} net; sample and matchup context matter.".format(
                    lineup.team_abbreviation or "A team",
                    lineup.net_rating or 0.0,
                ),
                team_abbreviation=lineup.team_abbreviation,
                confidence="low",
            )
        )
    return signals[:5]


def _coverage_and_warnings(
    completed_games: int,
    playoff_team_stats: bool,
    regular_team_baselines: bool,
    playoff_player_stats: bool,
    playoff_lineups: bool,
    shot_profile_splits: bool,
) -> PlayoffSeriesDataCoverage:
    warnings: List[str] = []
    if completed_games < RECOMMENDED_COMPLETED_GAMES:
        warnings.append(
            "Only {} completed playoff games; tactical reads are directional until Game 4+.".format(
                completed_games
            )
        )
    if not playoff_team_stats:
        warnings.append("Missing playoff team dashboard rows for at least one team.")
    if not regular_team_baselines:
        warnings.append("Regular-season team baselines are incomplete, so deltas may be blank.")
    if not playoff_player_stats:
        warnings.append("Missing playoff player season rows for at least one roster.")
    if not playoff_lineups:
        warnings.append("No playoff lineup rows found yet; lineup chess is hidden or low confidence.")
    if not shot_profile_splits:
        warnings.append("Team shooting-split rows are incomplete; shot diet pressure may use roster-derived proxies.")
    return PlayoffSeriesDataCoverage(
        completed_games=completed_games,
        playoff_team_stats=playoff_team_stats,
        regular_team_baselines=regular_team_baselines,
        playoff_player_stats=playoff_player_stats,
        playoff_lineups=playoff_lineups,
        shot_profile_splits=shot_profile_splits,
        warnings=warnings,
    )


def _metadata(
    coverage: PlayoffSeriesDataCoverage,
    metrics: List[PlayoffMetricEdge],
    stars: List[PlayoffStarBurdenEntry],
) -> AnalysisMetadata:
    reliability = min(100.0, coverage.completed_games / float(RECOMMENDED_COMPLETED_GAMES) * 40.0)
    if coverage.playoff_team_stats:
        reliability += 20.0
    if coverage.regular_team_baselines:
        reliability += 10.0
    if coverage.playoff_player_stats:
        reliability += 15.0
    if coverage.playoff_lineups:
        reliability += 10.0
    if coverage.shot_profile_splits:
        reliability += 5.0
    reliability = min(100.0, reliability)
    confidence = "high" if reliability >= 75 else "medium" if reliability >= 50 else "low"
    metric_count = len([metric for metric in metrics if metric.top_value is not None and metric.bottom_value is not None])
    notes = list(coverage.warnings[:2])
    if not notes:
        notes.append("Playoff sample clears the first command-center reliability gate.")
    return AnalysisMetadata(
        methodology_version=METHODOLOGY_VERSION,
        reliability_score=round(reliability, 1),
        confidence=confidence,
        sample_context=SampleContext(
            sample_size=coverage.completed_games,
            effective_sample_size=coverage.completed_games,
            population_size=metric_count,
            minimum_recommended=RECOMMENDED_COMPLETED_GAMES,
            notes=notes,
        ),
        driver_breakdown=[
            DriverBreakdown(
                key="games",
                label="Completed games",
                value=float(coverage.completed_games),
                weight=0.40,
                contribution=min(40.0, coverage.completed_games / float(RECOMMENDED_COMPLETED_GAMES) * 40.0),
                explanation="More completed games stabilize series-specific reads.",
            ),
            DriverBreakdown(
                key="team_stats",
                label="Team stat coverage",
                value=1.0 if coverage.playoff_team_stats else 0.0,
                weight=0.20,
                contribution=20.0 if coverage.playoff_team_stats else 0.0,
                explanation="Four Factors require playoff team dashboard rows.",
            ),
            DriverBreakdown(
                key="player_stats",
                label="Player stat coverage",
                value=float(len(stars)),
                weight=0.15,
                contribution=15.0 if coverage.playoff_player_stats else 0.0,
                explanation="Star burden needs playoff player season rows.",
            ),
        ],
        limitations=[
            "Descriptive playoff read, not a betting model or adjusted plus-minus model.",
            "Lineup and shot-diet sections are sample-sensitive early in a series.",
            "No live in-game websocket or salary/trade feasibility modeling.",
        ],
        validation_notes=[
            "Current version is deterministic and auditable from stored playoff rows.",
            "Regular-season baselines are shown only as context; they do not overwrite playoff values.",
        ],
    )


def build_playoff_series_intelligence(
    db: Session, series_id: str
) -> Optional[PlayoffSeriesIntelligenceResponse]:
    series = db.query(PlayoffSeries).filter(PlayoffSeries.series_id == series_id).first()
    if series is None:
        return None

    team_lookup = _team_map(
        db,
        [
            team_id
            for team_id in [series.top_seed_team_id, series.bottom_seed_team_id]
            if team_id is not None
        ],
    )
    top_team = team_lookup.get(series.top_seed_team_id)
    bottom_team = team_lookup.get(series.bottom_seed_team_id)
    top_abbr = _team_abbr(top_team)
    bottom_abbr = _team_abbr(bottom_team)
    games = _series_games(db, series_id)
    pulse = _series_pulse(series, games, team_lookup)

    metrics = _build_metric_edges(db, series.season, top_team, bottom_team)
    top_rows = _team_player_rows(db, top_abbr, series.season, True)
    bottom_rows = _team_player_rows(db, bottom_abbr, series.season, True)
    top_agg = _team_player_aggregate(top_rows)
    bottom_agg = _team_player_aggregate(bottom_rows)

    star_burden = (
        _star_burden_for_team(db, series.season, top_abbr)
        + _star_burden_for_team(db, series.season, bottom_abbr)
    )
    star_burden.sort(
        key=lambda entry: (
            entry.usg_pct or 0.0,
            entry.pts_pg or 0.0,
            entry.min_pg or 0.0,
        ),
        reverse=True,
    )

    shot_diet = [
        _shot_diet_for_team(db, series.season, top_team, top_agg),
        _shot_diet_for_team(db, series.season, bottom_team, bottom_agg),
    ]

    top_best, top_worst = _lineup_entries_for_team(db, series.season, top_team)
    bottom_best, bottom_worst = _lineup_entries_for_team(db, series.season, bottom_team)
    best_lineups = top_best + bottom_best
    worst_lineups = top_worst + bottom_worst

    playoff_team_stats = all(
        _team_season_stat(db, team.id if team is not None else None, series.season, True) is not None
        for team in [top_team, bottom_team]
    )
    regular_team_baselines = all(
        _team_season_stat(db, team.id if team is not None else None, series.season, False) is not None
        for team in [top_team, bottom_team]
    )
    playoff_player_stats = bool(top_rows) and bool(bottom_rows)
    playoff_lineups = bool(best_lineups or worst_lineups)
    shot_profile_splits = bool(_shooting_split_rows(db, series.top_seed_team_id, series.season)) and bool(
        _shooting_split_rows(db, series.bottom_seed_team_id, series.season)
    )

    coverage = _coverage_and_warnings(
        pulse.completed_games,
        playoff_team_stats,
        regular_team_baselines,
        playoff_player_stats,
        playoff_lineups,
        shot_profile_splits,
    )
    warnings = list(coverage.warnings)
    for lineup in best_lineups + worst_lineups:
        if lineup.possessions is not None and lineup.possessions < MIN_LINEUP_POSSESSIONS:
            warnings.append(
                "{} lineup sample is below {} possessions.".format(
                    lineup.team_abbreviation or "A", MIN_LINEUP_POSSESSIONS
                )
            )
            break

    tactical_edges = _tactical_edges(metrics, star_burden, warnings)
    adjustment_signals = _adjustment_signals(pulse, metrics, best_lineups, worst_lineups)
    metadata = _metadata(coverage, metrics, star_burden)

    return PlayoffSeriesIntelligenceResponse(
        series_id=series.series_id,
        season=series.season,
        round=int(series.round or 0),
        top_team=PlayoffSeriesTeamRef(
            team_id=series.top_seed_team_id,
            abbreviation=top_abbr,
            seed=series.top_seed,
            wins=int(series.top_wins or 0),
        ),
        bottom_team=PlayoffSeriesTeamRef(
            team_id=series.bottom_seed_team_id,
            abbreviation=bottom_abbr,
            seed=series.bottom_seed,
            wins=int(series.bottom_wins or 0),
        ),
        pulse=pulse,
        data_coverage=coverage,
        four_factors=metrics,
        star_burden=star_burden[:10],
        shot_diet=shot_diet,
        best_lineups=best_lineups,
        worst_lineups=worst_lineups,
        tactical_edges=tactical_edges,
        adjustment_signals=adjustment_signals,
        warnings=warnings,
        analysis_metadata=metadata,
    )
