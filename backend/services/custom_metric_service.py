from __future__ import annotations

import statistics
from typing import Dict, List, Optional, Sequence, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import Player, SeasonStat
from models.leaderboard import (
    CustomMetricAnomaly,
    CustomMetricNarrative,
    CustomMetricPlayerRanking,
    CustomMetricRequest,
    CustomMetricResponse,
)


STAT_LABELS = {
    "pts_pg": "Points Per Game",
    "reb_pg": "Rebounds Per Game",
    "ast_pg": "Assists Per Game",
    "stl_pg": "Steals Per Game",
    "blk_pg": "Blocks Per Game",
    "tov_pg": "Turnovers Per Game",
    "fg_pct": "Field Goal Percentage",
    "fg3_pct": "Three-Point Percentage",
    "ft_pct": "Free Throw Percentage",
    "min_pg": "Minutes Per Game",
    "ts_pct": "True Shooting Percentage",
    "efg_pct": "Effective Field Goal Percentage",
    "usg_pct": "Usage Rate",
    "per": "PER",
    "bpm": "BPM",
    "ws": "Win Shares",
    "vorp": "VORP",
    "off_rating": "Offensive Rating",
    "def_rating": "Defensive Rating",
    "net_rating": "Net Rating",
    "pie": "PIE",
    "darko": "DARKO",
    "obpm": "OBPM",
    "dbpm": "DBPM",
    "ftr": "Free Throw Rate",
    "par3": "3-Point Attempt Rate",
    "ast_tov": "Assist to Turnover Ratio",
    "oreb_pct": "Offensive Rebound Percentage",
    "epm": "EPM",
    "rapm": "RAPM",
    "lebron": "LEBRON",
    "raptor": "RAPTOR",
    "pipm": "PIPM",
}

INVERSE_STATS = {"tov_pg", "def_rating"}
PER_GAME_STATS = {"pts_pg", "reb_pg", "ast_pg", "stl_pg", "blk_pg", "tov_pg", "min_pg"}
RATE_STATS = {
    "fg_pct",
    "fg3_pct",
    "ft_pct",
    "ts_pct",
    "efg_pct",
    "usg_pct",
    "ftr",
    "par3",
    "ast_tov",
    "oreb_pct",
}
IMPACT_STATS = {
    "per",
    "bpm",
    "ws",
    "vorp",
    "off_rating",
    "def_rating",
    "net_rating",
    "pie",
    "darko",
    "obpm",
    "dbpm",
    "epm",
    "rapm",
    "lebron",
    "raptor",
    "pipm",
}


def _normalize_weights(config: CustomMetricRequest, warnings: List[str]) -> List[Tuple[str, str, float, bool]]:
    if not config.components:
        raise HTTPException(status_code=422, detail="At least one component is required.")

    total_weight = sum(component.weight for component in config.components)
    if total_weight <= 0:
        raise HTTPException(status_code=422, detail="Component weights must sum to a positive value.")

    if abs(total_weight - 1.0) > 1e-6:
        warnings.append(
            "Weights did not sum to 1.0, so they were normalized proportionally before scoring."
        )

    normalized = []
    for component in config.components:
        if component.stat_id not in STAT_LABELS or not hasattr(SeasonStat, component.stat_id):
            raise HTTPException(
                status_code=422,
                detail="Unsupported stat '{0}' in metric configuration.".format(component.stat_id),
            )
        normalized.append(
            (
                component.stat_id,
                component.label or STAT_LABELS[component.stat_id],
                component.weight / total_weight,
                bool(component.inverse or component.stat_id in INVERSE_STATS),
            )
        )

    if len(normalized) == 1 or max(weight for _, _, weight, _ in normalized) >= 0.85:
        warnings.append(
            "This metric is heavily concentrated in one component, so the ranking may be weight-sensitive."
        )

    stat_ids = {stat_id for stat_id, _, _, _ in normalized}
    if stat_ids & PER_GAME_STATS and stat_ids & (RATE_STATS | IMPACT_STATS):
        warnings.append(
            "You are mixing per-game volume stats with rate or impact stats. The platform z-score normalizes them, but interpret the blend carefully."
        )

    return normalized


def _aspect_for_stat(stat_id: str) -> str:
    if stat_id in {"pts_pg", "fg_pct", "fg3_pct", "ft_pct", "ts_pct", "efg_pct"}:
        return "scoring"
    if stat_id in {"ast_pg", "usg_pct", "ast_tov", "off_rating"}:
        return "creation"
    if stat_id in {"reb_pg", "oreb_pct"}:
        return "rebounding"
    if stat_id in {"stl_pg", "blk_pg", "dbpm", "def_rating"}:
        return "defense"
    if stat_id in {"bpm", "per", "ws", "vorp", "pie", "epm", "rapm", "lebron", "raptor", "pipm"}:
        return "impact"
    return "efficiency"


def _generate_metric_label(metric_name: Optional[str], components: Sequence[Tuple[str, str, float, bool]]) -> str:
    if metric_name and metric_name.strip():
        return metric_name.strip()

    weighted_aspects: Dict[str, float] = {}
    for stat_id, _, weight, _ in components:
        aspect = _aspect_for_stat(stat_id)
        weighted_aspects[aspect] = weighted_aspects.get(aspect, 0.0) + weight

    leaders = sorted(weighted_aspects.items(), key=lambda item: item[1], reverse=True)
    top_aspects = [aspect for aspect, _ in leaders[:2]]
    if {"scoring", "creation"} <= set(top_aspects):
        return "Creation Scoring Index"
    if {"scoring", "defense"} <= set(top_aspects):
        return "Two-Way Pressure Index"
    if {"rebounding", "scoring"} <= set(top_aspects):
        return "Paint Dominance Score"
    if top_aspects == ["impact", "efficiency"]:
        return "Impact Efficiency Rating"
    if not top_aspects:
        return "Custom Composite Index"
    return "{0} {1} Composite".format(top_aspects[0].title(), top_aspects[-1].title())


def _generate_interpretation(metric_label: str, components: Sequence[Tuple[str, str, float, bool]]) -> str:
    weighted_aspects: Dict[str, float] = {}
    for stat_id, _, weight, _ in components:
        aspect = _aspect_for_stat(stat_id)
        weighted_aspects[aspect] = weighted_aspects.get(aspect, 0.0) + weight

    leaders = sorted(weighted_aspects.items(), key=lambda item: item[1], reverse=True)
    top_aspects = [aspect for aspect, _ in leaders[:2]]
    aspect_phrase = " and ".join(top_aspects) if top_aspects else "overall production"
    return (
        "{0} measures how strongly a player stands out in {1} once every component is normalized against the active pool. "
        "It rewards players whose profile stays consistently above the pool across the weighted categories rather than relying on one raw box-score total."
    ).format(metric_label, aspect_phrase)


def _fetch_pool_rows(
    db: Session,
    season: str,
    player_pool: str,
    team_abbreviation: Optional[str],
    position: Optional[str],
) -> List[Tuple[SeasonStat, Player]]:
    query = (
        db.query(SeasonStat, Player)
        .join(Player, SeasonStat.player_id == Player.id)
        .filter(
            SeasonStat.season == season,
            SeasonStat.is_playoff == False,  # noqa: E712
            SeasonStat.gp > 0,
        )
    )

    if player_pool == "team_filter":
        if not team_abbreviation:
            raise HTTPException(status_code=422, detail="team_abbreviation is required for team_filter pools.")
        query = query.filter(SeasonStat.team_abbreviation == team_abbreviation)
    elif player_pool == "position_filter":
        if not position:
            raise HTTPException(status_code=422, detail="position is required for position_filter pools.")
        query = query.filter(Player.position.isnot(None), Player.position.ilike("%{0}%".format(position)))
    elif player_pool != "all":
        raise HTTPException(status_code=422, detail="Unsupported player_pool '{0}'.".format(player_pool))

    rows = query.all()
    best_rows: Dict[int, Tuple[SeasonStat, Player]] = {}
    for season_row, player in rows:
        existing = best_rows.get(player.id)
        if existing is None or (season_row.gp or 0) > (existing[0].gp or 0):
            best_rows[player.id] = (season_row, player)
    return list(best_rows.values())


def _stat_zscores(values: Sequence[float]) -> List[float]:
    if len(values) < 2:
        return [0.0 for _ in values]
    mean_value = statistics.mean(values)
    std_value = statistics.stdev(values)
    if not std_value:
        return [0.0 for _ in values]
    return [(value - mean_value) / std_value for value in values]


def build_custom_metric_report(db: Session, config: CustomMetricRequest) -> CustomMetricResponse:
    warnings: List[str] = []
    normalized_components = _normalize_weights(config, warnings)
    pool_rows = _fetch_pool_rows(
        db=db,
        season=config.season,
        player_pool=config.player_pool,
        team_abbreviation=config.team_abbreviation,
        position=config.position,
    )

    excluded_players: List[str] = []
    eligible_rows: List[Tuple[SeasonStat, Player]] = []
    for season_row, player in pool_rows:
        missing = []
        for stat_id, _, _, _ in normalized_components:
            value = getattr(season_row, stat_id, None)
            if value is None:
                missing.append(stat_id)
        if missing:
            excluded_players.append(
                "{0} — missing {1}".format(player.full_name, ", ".join(sorted(missing)))
            )
            continue
        eligible_rows.append((season_row, player))

    if excluded_players:
        warnings.append(
            "Excluded players with unavailable stats: {0}.".format("; ".join(excluded_players[:12]))
        )
        if len(excluded_players) > 12:
            warnings.append(
                "{0} additional players were also excluded for missing component stats.".format(
                    len(excluded_players) - 12
                )
            )

    if len(eligible_rows) < 5:
        raise HTTPException(status_code=400, detail="Insufficient player pool for meaningful ranking.")

    zscores_by_stat: Dict[str, Dict[int, float]] = {}
    for stat_id, _, _, inverse in normalized_components:
        stat_values = [float(getattr(season_row, stat_id)) for season_row, _ in eligible_rows]
        if inverse:
            stat_values = [-value for value in stat_values]
        zscores = _stat_zscores(stat_values)
        zscores_by_stat[stat_id] = {
            player.id: zscore
            for (_, player), zscore in zip(eligible_rows, zscores)
        }

    metric_label = _generate_metric_label(config.metric_name, normalized_components)
    rankings: List[CustomMetricPlayerRanking] = []
    anomalies: List[CustomMetricAnomaly] = []
    sortable_rows = []

    for season_row, player in eligible_rows:
        contributions: Dict[str, float] = {}
        abs_total = 0.0
        total = 0.0
        for stat_id, _, weight, _ in normalized_components:
            contribution = zscores_by_stat[stat_id][player.id] * weight
            rounded = round(contribution, 2)
            contributions[stat_id] = rounded
            total += contribution
            abs_total += abs(contribution)

        dominant_stat = None
        dominant_pct = 0.0
        if abs_total > 0:
            dominant_stat, dominant_value = max(
                contributions.items(),
                key=lambda item: abs(item[1]),
            )
            dominant_pct = round((abs(dominant_value) / abs_total) * 100, 1)
            if dominant_pct > 60.0:
                anomalies.append(
                    CustomMetricAnomaly(
                        player_name=player.full_name,
                        dominant_stat=dominant_stat,
                        contribution_pct=dominant_pct,
                    )
                )

        sortable_rows.append(
            {
                "player_name": player.full_name,
                "team": season_row.team_abbreviation,
                "score": round(total, 2),
                "contributions": contributions,
            }
        )

    sortable_rows.sort(key=lambda row: row["score"], reverse=True)
    for index, row in enumerate(sortable_rows, start=1):
        rankings.append(
            CustomMetricPlayerRanking(
                rank=index,
                player_name=row["player_name"],
                team=row["team"],
                composite_score=row["score"],
                component_breakdown=row["contributions"],
            )
        )

    narratives: List[CustomMetricNarrative] = []
    for ranking in rankings[:3]:
        ordered_components = sorted(
            ranking.component_breakdown.items(),
            key=lambda item: abs(item[1]),
            reverse=True,
        )
        primary = ordered_components[0][0] if ordered_components else normalized_components[0][0]
        secondary = ordered_components[1][0] if len(ordered_components) > 1 else primary
        narratives.append(
            CustomMetricNarrative(
                player_name=ranking.player_name,
                narrative=(
                    "{0} rises here because {1} and {2} both grade well above the active pool once the weighted z-scores are blended."
                ).format(
                    ranking.player_name,
                    STAT_LABELS.get(primary, primary),
                    STAT_LABELS.get(secondary, secondary),
                ),
            )
        )

    return CustomMetricResponse(
        metric_label=metric_label,
        metric_interpretation=_generate_interpretation(metric_label, normalized_components),
        player_rankings=rankings,
        top_player_narratives=narratives,
        anomalies=anomalies,
        validation_warnings=warnings,
    )
