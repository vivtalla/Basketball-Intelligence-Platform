from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Literal, Optional


MetricFormat = Literal["number", "integer", "percent", "record"]
EntityType = Literal["player", "team"]


@dataclass(frozen=True)
class QueryMetricDefinition:
    key: str
    label: str
    description: str
    format: MetricFormat
    category: str
    aliases: tuple[str, ...]
    entity_types: tuple[EntityType, ...]
    higher_is_better: bool
    source: str

    def supports(self, entity_type: EntityType) -> bool:
        return entity_type in self.entity_types


def _aliases(*values: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value.lower() for value in values))


METRICS: tuple[QueryMetricDefinition, ...] = (
    QueryMetricDefinition(
        key="pts_pg",
        label="Points Per Game",
        description="Average points scored per game.",
        format="number",
        category="Scoring",
        aliases=_aliases("ppg", "points per game", "points a game", "scoring average"),
        entity_types=("player", "team"),
        higher_is_better=True,
        source="season_stats/team_season_stats",
    ),
    QueryMetricDefinition(
        key="pts",
        label="Points",
        description="Total points scored in the selected season.",
        format="integer",
        category="Scoring",
        aliases=_aliases("points", "total points", "pts"),
        entity_types=("player",),
        higher_is_better=True,
        source="season_stats",
    ),
    QueryMetricDefinition(
        key="reb_pg",
        label="Rebounds Per Game",
        description="Average rebounds per game.",
        format="number",
        category="Production",
        aliases=_aliases("rpg", "rebounds per game", "rebounds a game", "boards"),
        entity_types=("player", "team"),
        higher_is_better=True,
        source="season_stats/team_season_stats",
    ),
    QueryMetricDefinition(
        key="ast_pg",
        label="Assists Per Game",
        description="Average assists per game.",
        format="number",
        category="Creation",
        aliases=_aliases("apg", "assists per game", "assists a game"),
        entity_types=("player", "team"),
        higher_is_better=True,
        source="season_stats/team_season_stats",
    ),
    QueryMetricDefinition(
        key="tov_pg",
        label="Turnovers Per Game",
        description="Average turnovers per game.",
        format="number",
        category="Possessions",
        aliases=_aliases("turnovers per game", "turnovers a game", "tpg", "tov per game"),
        entity_types=("player", "team"),
        higher_is_better=False,
        source="season_stats/team_season_stats",
    ),
    QueryMetricDefinition(
        key="stl_pg",
        label="Steals Per Game",
        description="Average steals per game.",
        format="number",
        category="Defense",
        aliases=_aliases("spg", "steals per game", "steals a game"),
        entity_types=("player", "team"),
        higher_is_better=True,
        source="season_stats/team_season_stats",
    ),
    QueryMetricDefinition(
        key="blk_pg",
        label="Blocks Per Game",
        description="Average blocks per game.",
        format="number",
        category="Defense",
        aliases=_aliases("bpg", "blocks per game", "blocks a game"),
        entity_types=("player", "team"),
        higher_is_better=True,
        source="season_stats/team_season_stats",
    ),
    QueryMetricDefinition(
        key="fg_pct",
        label="Field Goal %",
        description="Field goals made divided by field goals attempted.",
        format="percent",
        category="Shooting",
        aliases=_aliases("field goal percentage", "field goal %", "fg%", "fg pct"),
        entity_types=("player", "team"),
        higher_is_better=True,
        source="season_stats/team_season_stats",
    ),
    QueryMetricDefinition(
        key="fg3_pct",
        label="3-Point %",
        description="Three-point field goals made divided by three-point attempts.",
        format="percent",
        category="Shooting",
        aliases=_aliases("three point percentage", "three-point percentage", "3 point percentage", "3p%", "3p pct", "three point %"),
        entity_types=("player", "team"),
        higher_is_better=True,
        source="season_stats/team_season_stats",
    ),
    QueryMetricDefinition(
        key="fg3m",
        label="3s Made",
        description="Total three-point field goals made.",
        format="integer",
        category="Shooting",
        aliases=_aliases("threes", "3s", "3pm", "three pointers", "3 pointers", "three-pointers made"),
        entity_types=("player",),
        higher_is_better=True,
        source="season_stats",
    ),
    QueryMetricDefinition(
        key="ft_pct",
        label="Free Throw %",
        description="Free throws made divided by free throw attempts.",
        format="percent",
        category="Shooting",
        aliases=_aliases("free throw percentage", "free throw %", "ft%", "ft pct"),
        entity_types=("player", "team"),
        higher_is_better=True,
        source="season_stats/team_season_stats",
    ),
    QueryMetricDefinition(
        key="ts_pct",
        label="True Shooting %",
        description="Shooting efficiency that accounts for twos, threes, and free throws.",
        format="percent",
        category="Shooting",
        aliases=_aliases("true shooting", "true shooting percentage", "true shooting %", "ts%", "ts pct"),
        entity_types=("player", "team"),
        higher_is_better=True,
        source="season_stats/team_season_stats",
    ),
    QueryMetricDefinition(
        key="efg_pct",
        label="Effective FG %",
        description="Field goal percentage adjusted for the extra value of three-pointers.",
        format="percent",
        category="Shooting",
        aliases=_aliases("effective field goal", "effective field goal percentage", "efg%", "efg pct"),
        entity_types=("player", "team"),
        higher_is_better=True,
        source="season_stats/team_season_stats",
    ),
    QueryMetricDefinition(
        key="usg_pct",
        label="Usage Rate",
        description="Estimated share of team possessions a player uses while on the floor.",
        format="percent",
        category="Role",
        aliases=_aliases("usage", "usage rate", "usage percentage", "usg%", "usg pct"),
        entity_types=("player",),
        higher_is_better=True,
        source="season_stats",
    ),
    QueryMetricDefinition(
        key="off_rating",
        label="Offensive Rating",
        description="Estimated points scored per 100 possessions.",
        format="number",
        category="Advanced",
        aliases=_aliases("offensive rating", "off rating", "ortg", "off rtg"),
        entity_types=("player", "team"),
        higher_is_better=True,
        source="season_stats/team_season_stats",
    ),
    QueryMetricDefinition(
        key="def_rating",
        label="Defensive Rating",
        description="Estimated points allowed per 100 possessions.",
        format="number",
        category="Advanced",
        aliases=_aliases("defensive rating", "def rating", "drtg", "def rtg"),
        entity_types=("player", "team"),
        higher_is_better=False,
        source="season_stats/team_season_stats",
    ),
    QueryMetricDefinition(
        key="net_rating",
        label="Net Rating",
        description="Offensive rating minus defensive rating.",
        format="number",
        category="Advanced",
        aliases=_aliases("net rating", "net rtg", "nrtg", "net"),
        entity_types=("player", "team"),
        higher_is_better=True,
        source="season_stats/team_season_stats",
    ),
    QueryMetricDefinition(
        key="pace",
        label="Pace",
        description="Estimated possessions per 48 minutes.",
        format="number",
        category="Advanced",
        aliases=_aliases("pace", "pace factor", "possessions per 48"),
        entity_types=("player", "team"),
        higher_is_better=True,
        source="season_stats/team_season_stats",
    ),
    QueryMetricDefinition(
        key="per",
        label="PER",
        description="Player Efficiency Rating, scaled around a league average of 15.",
        format="number",
        category="Advanced",
        aliases=_aliases("per", "player efficiency rating"),
        entity_types=("player",),
        higher_is_better=True,
        source="season_stats",
    ),
    QueryMetricDefinition(
        key="bpm",
        label="BPM",
        description="Box Plus/Minus, estimated impact per 100 possessions above league average.",
        format="number",
        category="Advanced",
        aliases=_aliases("bpm", "box plus minus", "box plus/minus"),
        entity_types=("player",),
        higher_is_better=True,
        source="season_stats",
    ),
    QueryMetricDefinition(
        key="ws",
        label="Win Shares",
        description="Estimated wins contributed based on box score production.",
        format="number",
        category="Advanced",
        aliases=_aliases("win shares", "ws"),
        entity_types=("player",),
        higher_is_better=True,
        source="season_stats",
    ),
    QueryMetricDefinition(
        key="vorp",
        label="VORP",
        description="Value Over Replacement Player, a BPM-based value estimate.",
        format="number",
        category="Advanced",
        aliases=_aliases("vorp", "value over replacement"),
        entity_types=("player",),
        higher_is_better=True,
        source="season_stats",
    ),
    QueryMetricDefinition(
        key="pie",
        label="PIE",
        description="Player or team impact estimate based on share of positive game events.",
        format="percent",
        category="Advanced",
        aliases=_aliases("pie", "player impact estimate"),
        entity_types=("player", "team"),
        higher_is_better=True,
        source="season_stats/team_season_stats",
    ),
    QueryMetricDefinition(
        key="plus_minus_pg",
        label="Point Differential",
        description="Average point margin per game.",
        format="number",
        category="Team",
        aliases=_aliases("point differential", "average margin", "margin", "plus minus", "diff"),
        entity_types=("team",),
        higher_is_better=True,
        source="team_season_stats",
    ),
    QueryMetricDefinition(
        key="wins",
        label="Wins",
        description="Team wins in the selected season.",
        format="integer",
        category="Team",
        aliases=_aliases("wins", "record"),
        entity_types=("team",),
        higher_is_better=True,
        source="team_season_stats",
    ),
)

METRICS_BY_KEY = {metric.key: metric for metric in METRICS}


def normalize_query_text(value: str) -> str:
    normalized = value.lower()
    normalized = normalized.replace("three-point", "three point")
    normalized = normalized.replace("plus/minus", "plus minus")
    normalized = re.sub(r"[^a-z0-9%./+-]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def all_metrics() -> List[QueryMetricDefinition]:
    return list(METRICS)


def metric_to_metadata(metric: QueryMetricDefinition) -> dict:
    return {
        "key": metric.key,
        "label": metric.label,
        "description": metric.description,
        "format": metric.format,
        "category": metric.category,
        "aliases": list(metric.aliases),
        "entity_types": list(metric.entity_types),
        "higher_is_better": metric.higher_is_better,
        "source": metric.source,
    }


def format_metric_value(metric: QueryMetricDefinition, value: Optional[float]) -> str:
    if value is None:
        return "-"
    if metric.format == "percent":
        return f"{value * 100:.1f}%"
    if metric.format == "integer":
        return f"{round(value):,}"
    return f"{value:.1f}"


def display_to_stored_value(metric: QueryMetricDefinition, value: float) -> float:
    if metric.format == "percent" and value > 1:
        return value / 100
    return value


def resolve_metric(text: str, entity_type: Optional[EntityType] = None) -> Optional[QueryMetricDefinition]:
    normalized = normalize_query_text(text)
    candidates = _matching_metrics(normalized, entity_type=entity_type)
    return candidates[0] if candidates else None


def matching_metric_aliases(text: str, entity_type: Optional[EntityType] = None) -> list[tuple[QueryMetricDefinition, str]]:
    normalized = normalize_query_text(text)
    matches: list[tuple[QueryMetricDefinition, str]] = []
    for metric in METRICS:
        if entity_type and not metric.supports(entity_type):
            continue
        for alias in sorted(metric.aliases + (metric.label.lower(), metric.key), key=len, reverse=True):
            if _contains_alias(normalized, normalize_query_text(alias)):
                matches.append((metric, alias))
                break
    return sorted(matches, key=lambda item: len(item[1]), reverse=True)


def _matching_metrics(text: str, entity_type: Optional[EntityType]) -> list[QueryMetricDefinition]:
    matches = matching_metric_aliases(text, entity_type=entity_type)
    return [metric for metric, _ in matches]


def _contains_alias(text: str, alias: str) -> bool:
    if not alias:
        return False
    if re.search(r"[^\w\s]", alias):
        return alias in text
    return re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", text) is not None


def supported_metrics(entity_type: EntityType) -> Iterable[QueryMetricDefinition]:
    return (metric for metric in METRICS if metric.supports(entity_type))
