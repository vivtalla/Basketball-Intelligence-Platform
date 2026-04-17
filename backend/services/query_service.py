from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy.orm import Session

from db.models import GameTeamStat, Player, PlayerGameLog, SeasonStat, Team, TeamSeasonStat, WarehouseGame
from models.query import (
    QueryAnswerCard,
    QueryAskRequest,
    QueryAskResponse,
    QueryFilter,
    QueryIntent,
    QueryMetricMetadata,
    QueryResultRow,
)
from services.query_metric_registry import (
    EntityType,
    METRICS_BY_KEY,
    QueryMetricDefinition,
    all_metrics,
    display_to_stored_value,
    format_metric_value,
    matching_metric_aliases,
    metric_to_metadata,
    normalize_query_text,
    resolve_metric,
)
from services.sync_service import canonical_player_name


DEFAULT_SUGGESTIONS = [
    "Who leads the NBA in points per game this season?",
    "Best teams by net rating in 2025-26",
    "Players with at least 25 ppg and 60 ts%",
    "Lowest defensive rating by a team this season",
    "How has Shai played recently?",
]

QUERY_EXAMPLES = [
    {
        "category": "Player Leaders",
        "prompt": "Who leads the NBA in points per game this season?",
        "description": "Ranks players by a season metric using the latest synced season by default.",
    },
    {
        "category": "Team Rankings",
        "prompt": "Best teams by net rating in 2025-26",
        "description": "Ranks teams from official team season stats.",
    },
    {
        "category": "Filters",
        "prompt": "Players with at least 25 ppg and 60 ts%",
        "description": "Combines stat thresholds with a transparent leaderboard table.",
    },
    {
        "category": "Defense",
        "prompt": "Lowest defensive rating by a team this season",
        "description": "Understands lower-is-better defensive metrics.",
    },
    {
        "category": "Recent Form",
        "prompt": "How has Shai played recently?",
        "description": "Pulls recent player game logs from the local warehouse.",
    },
]


@dataclass
class ParsedQuery:
    question: str
    normalized: str
    season: str
    limit: int
    entity_type: Optional[EntityType]
    intent_type: str
    metric: Optional[QueryMetricDefinition]
    sort_direction: Optional[str]
    filters: list[QueryFilter]
    player: Optional[Player] = None
    team: Optional[Team] = None
    compare_players: tuple[Player, Player] | None = None
    confidence: float = 0.3


def get_query_examples() -> list[dict]:
    return QUERY_EXAMPLES


def get_query_metrics() -> list[dict]:
    return [metric_to_metadata(metric) for metric in all_metrics()]


def answer_query(db: Session, payload: QueryAskRequest) -> QueryAskResponse:
    parsed = _parse_query(db, payload)

    if parsed.intent_type == "player_recent" and parsed.player:
        return _answer_player_recent(db, parsed)
    if parsed.intent_type == "team_recent" and parsed.team:
        return _answer_team_recent(db, parsed)
    if parsed.intent_type == "player_lookup" and parsed.player:
        return _answer_player_lookup(db, parsed)
    if parsed.intent_type == "team_lookup" and parsed.team:
        return _answer_team_lookup(db, parsed)
    if parsed.intent_type == "compare_players" and parsed.compare_players:
        return _answer_compare_players(parsed)
    if parsed.intent_type == "ranking" and parsed.metric and parsed.entity_type == "player":
        return _answer_player_ranking(db, parsed)
    if parsed.intent_type == "ranking" and parsed.metric and parsed.entity_type == "team":
        return _answer_team_ranking(db, parsed)
    return _clarification_response(parsed)


def _parse_query(db: Session, payload: QueryAskRequest) -> ParsedQuery:
    question = payload.question.strip()
    normalized = normalize_query_text(question)
    season = payload.season or _extract_season(normalized) or _latest_season(db)
    limit = payload.limit or _extract_limit(normalized) or 10
    limit = max(1, min(limit, 50))
    entity_type = _infer_entity_type(normalized)

    player = _find_player(db, question)
    team = _find_team(db, question)
    compare_players = _find_compare_players(db, question)

    if compare_players:
        return ParsedQuery(
            question=question,
            normalized=normalized,
            season=season,
            limit=2,
            entity_type="player",
            intent_type="compare_players",
            metric=None,
            sort_direction=None,
            filters=[],
            compare_players=compare_players,
            confidence=0.85,
        )

    if _is_recent_query(normalized):
        if player:
            return ParsedQuery(
                question=question,
                normalized=normalized,
                season=season,
                limit=10,
                entity_type="player",
                intent_type="player_recent",
                metric=None,
                sort_direction=None,
                filters=[],
                player=player,
                confidence=0.8,
            )
        if team:
            return ParsedQuery(
                question=question,
                normalized=normalized,
                season=season,
                limit=10,
                entity_type="team",
                intent_type="team_recent",
                metric=None,
                sort_direction=None,
                filters=[],
                team=team,
                confidence=0.8,
            )

    metric = resolve_metric(normalized, entity_type=entity_type) or resolve_metric(normalized)
    if metric and entity_type is None:
        entity_type = _default_entity_for_metric(metric, normalized)
    filters = _parse_filters(normalized, entity_type=entity_type)
    if filters and metric is None:
        metric = METRICS_BY_KEY.get(filters[0].metric_key)
        entity_type = entity_type or _default_entity_for_metric(metric, normalized) if metric else entity_type

    if metric and entity_type:
        sort_direction = _sort_direction(normalized, metric)
        return ParsedQuery(
            question=question,
            normalized=normalized,
            season=season,
            limit=limit,
            entity_type=entity_type,
            intent_type="ranking",
            metric=metric,
            sort_direction=sort_direction,
            filters=filters,
            confidence=0.8 if metric else 0.45,
        )

    if player:
        return ParsedQuery(
            question=question,
            normalized=normalized,
            season=season,
            limit=1,
            entity_type="player",
            intent_type="player_lookup",
            metric=None,
            sort_direction=None,
            filters=[],
            player=player,
            confidence=0.7,
        )
    if team:
        return ParsedQuery(
            question=question,
            normalized=normalized,
            season=season,
            limit=1,
            entity_type="team",
            intent_type="team_lookup",
            metric=None,
            sort_direction=None,
            filters=[],
            team=team,
            confidence=0.7,
        )

    return ParsedQuery(
        question=question,
        normalized=normalized,
        season=season,
        limit=limit,
        entity_type=entity_type,
        intent_type="unknown",
        metric=metric,
        sort_direction=None,
        filters=filters,
        confidence=0.2,
    )


def _latest_season(db: Session) -> str:
    seasons = [
        row[0]
        for row in db.query(SeasonStat.season)
        .filter(SeasonStat.is_playoff == False)  # noqa: E712
        .distinct()
        .all()
    ]
    seasons += [
        row[0]
        for row in db.query(TeamSeasonStat.season)
        .filter(TeamSeasonStat.is_playoff == False)  # noqa: E712
        .distinct()
        .all()
    ]
    return sorted({season for season in seasons if season}, reverse=True)[0] if seasons else "2025-26"


def _extract_season(normalized: str) -> Optional[str]:
    match = re.search(r"\b(20\d{2})\s*[-/]\s*(\d{2})\b", normalized)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    return None


def _extract_limit(normalized: str) -> Optional[int]:
    for pattern in (r"\btop\s+(\d{1,2})\b", r"\bbottom\s+(\d{1,2})\b", r"\bfirst\s+(\d{1,2})\b"):
        match = re.search(pattern, normalized)
        if match:
            return int(match.group(1))
    return None


def _infer_entity_type(normalized: str) -> Optional[EntityType]:
    if re.search(r"\b(team|teams|standings|east|west|conference)\b", normalized):
        return "team"
    if re.search(r"\b(player|players|nba leaders|who leads|who had|rookie|guard|forward|center)\b", normalized):
        return "player"
    return None


def _default_entity_for_metric(metric: QueryMetricDefinition, normalized: str) -> EntityType:
    if metric.supports("team") and not metric.supports("player"):
        return "team"
    if metric.supports("player") and not metric.supports("team"):
        return "player"
    if re.search(r"\b(team|teams|standings|conference)\b", normalized):
        return "team"
    return "player"


def _sort_direction(normalized: str, metric: QueryMetricDefinition) -> str:
    if re.search(r"\b(lowest|worst|bottom|fewest)\b", normalized) or re.search(r"(?<!at )\bleast\b", normalized):
        return "asc"
    if re.search(r"\b(best|top|highest|most|leaders?|leads?)\b", normalized):
        return "desc" if metric.higher_is_better else "asc"
    return "desc" if metric.higher_is_better else "asc"


def _is_recent_query(normalized: str) -> bool:
    return bool(re.search(r"\b(recent|recently|last 10|last ten|l10|last few|form)\b", normalized))


def _parse_filters(normalized: str, entity_type: Optional[EntityType]) -> list[QueryFilter]:
    filters: list[QueryFilter] = []
    matches = matching_metric_aliases(normalized, entity_type=entity_type)
    for metric, alias in matches:
        alias_pattern = re.escape(normalize_query_text(alias))
        alias_token = rf"(?<![a-z0-9]){alias_pattern}(?![a-z0-9])"
        patterns = [
            rf"\bat\s+least\s+(\d+(?:\.\d+)?)\s+{alias_token}",
            rf"\bminimum\s+(\d+(?:\.\d+)?)\s+{alias_token}",
            rf"\b(\d+(?:\.\d+)?)\s+{alias_token}",
            rf"{alias_token}\s+(?:of\s+)?(?:at\s+least\s+)?(\d+(?:\.\d+)?)\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if not match:
                continue
            display_value = float(match.group(1))
            stored = display_to_stored_value(metric, display_value)
            if any(existing.metric_key == metric.key for existing in filters):
                break
            filters.append(
                QueryFilter(
                    metric_key=metric.key,
                    label=metric.label,
                    operator="gte",
                    value=stored,
                    formatted_value=format_metric_value(metric, stored),
                )
            )
            break
    return filters[:4]


def _find_player(db: Session, question: str) -> Optional[Player]:
    normalized = normalize_query_text(question)
    rows = db.query(Player).all()
    scored: list[tuple[int, Player]] = []
    for player in rows:
        full_name = canonical_player_name(player.full_name, player.first_name or "", player.last_name or "")
        name = normalize_query_text(full_name)
        first = normalize_query_text(player.first_name or "")
        last = normalize_query_text(player.last_name or "")
        score = 0
        if name and name in normalized:
            score += 100 + len(name)
        if first and re.search(rf"(?<![a-z0-9]){re.escape(first)}(?![a-z0-9])", normalized):
            score += 35 + len(first)
        if last and re.search(rf"(?<![a-z0-9]){re.escape(last)}(?![a-z0-9])", normalized):
            score += 25 + len(last)
        if score:
            if player.is_active:
                score += 5
            scored.append((score, player))
    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]


def _find_team(db: Session, question: str) -> Optional[Team]:
    normalized = normalize_query_text(question)
    teams = db.query(Team).all()
    scored: list[tuple[int, Team]] = []
    for team in teams:
        abbr = normalize_query_text(team.abbreviation or "")
        city = normalize_query_text(team.city or "")
        name = normalize_query_text(team.name or "")
        full = normalize_query_text(f"{team.city or ''} {team.name or ''}")
        score = 0
        for candidate, points in ((abbr, 80), (full, 70), (name, 40), (city, 20)):
            if candidate and re.search(rf"(?<![a-z0-9]){re.escape(candidate)}(?![a-z0-9])", normalized):
                score = max(score, points + len(candidate))
        if score:
            scored.append((score, team))
    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]


def _find_compare_players(db: Session, question: str) -> tuple[Player, Player] | None:
    normalized = normalize_query_text(question)
    if not re.search(r"\b(compare|vs|versus)\b", normalized):
        return None
    players = []
    for player in db.query(Player).all():
        full_name = canonical_player_name(player.full_name, player.first_name or "", player.last_name or "")
        name = normalize_query_text(full_name)
        first = normalize_query_text(player.first_name or "")
        last = normalize_query_text(player.last_name or "")
        if name and name in normalized:
            players.append(player)
        elif first and last and first in normalized and last in normalized:
            players.append(player)
    unique: list[Player] = []
    seen: set[int] = set()
    for player in players:
        if player.id not in seen:
            unique.append(player)
            seen.add(player.id)
    return (unique[0], unique[1]) if len(unique) >= 2 else None


def _answer_player_ranking(db: Session, parsed: ParsedQuery) -> QueryAskResponse:
    assert parsed.metric is not None
    metric = parsed.metric
    if not hasattr(SeasonStat, metric.key):
        return _clarification_response(parsed, warning=f"{metric.label} is not available for player leaderboards yet.")
    stat_col = getattr(SeasonStat, metric.key)
    query = (
        db.query(SeasonStat, Player)
        .join(Player, SeasonStat.player_id == Player.id)
        .filter(
            SeasonStat.season == parsed.season,
            SeasonStat.is_playoff == False,  # noqa: E712
            SeasonStat.gp >= 15,
            stat_col.isnot(None),
        )
    )
    for filter_item in parsed.filters:
        if hasattr(SeasonStat, filter_item.metric_key):
            filter_col = getattr(SeasonStat, filter_item.metric_key)
            query = query.filter(filter_col >= filter_item.value)
    order_col = stat_col.asc() if parsed.sort_direction == "asc" else stat_col.desc()
    raw_rows = query.order_by(order_col, SeasonStat.gp.desc()).limit(parsed.limit * 4).all()

    deduped: list[tuple[SeasonStat, Player]] = []
    seen: set[int] = set()
    for stat_row, player in raw_rows:
        if player.id in seen:
            continue
        seen.add(player.id)
        deduped.append((stat_row, player))
        if len(deduped) >= parsed.limit:
            break

    rows = [
        QueryResultRow(
            rank=index,
            entity_type="player",
            entity_id=str(player.id),
            name=canonical_player_name(player.full_name, player.first_name or "", player.last_name or ""),
            subtitle=f"{stat_row.team_abbreviation} - {stat_row.gp or 0} GP",
            team_abbreviation=stat_row.team_abbreviation,
            value=float(getattr(stat_row, metric.key)),
            formatted_value=format_metric_value(metric, float(getattr(stat_row, metric.key))),
            detail_url=f"/players/{player.id}",
            metrics={
                "gp": stat_row.gp,
                "pts_pg": stat_row.pts_pg,
                "reb_pg": stat_row.reb_pg,
                "ast_pg": stat_row.ast_pg,
                "ts_pct": stat_row.ts_pct,
                "net_rating": stat_row.net_rating,
            },
        )
        for index, (stat_row, player) in enumerate(deduped, start=1)
    ]
    title = _ranking_title(parsed, metric)
    if rows:
        top = rows[0]
        summary = f"{top.name} leads this result set at {top.formatted_value}."
        primary_value = top.formatted_value
        href = top.detail_url
    else:
        summary = "No players matched that query with the current synced data."
        primary_value = "No rows"
        href = None
    return _response(parsed, rows, title, summary, metric.label, primary_value, href)


def _answer_team_ranking(db: Session, parsed: ParsedQuery) -> QueryAskResponse:
    assert parsed.metric is not None
    metric = parsed.metric
    attr_name = "w" if metric.key == "wins" else metric.key
    if not hasattr(TeamSeasonStat, attr_name):
        return _clarification_response(parsed, warning=f"{metric.label} is not available for team rankings yet.")
    stat_col = getattr(TeamSeasonStat, attr_name)
    query = (
        db.query(TeamSeasonStat, Team)
        .join(Team, TeamSeasonStat.team_id == Team.id)
        .filter(
            TeamSeasonStat.season == parsed.season,
            TeamSeasonStat.is_playoff == False,  # noqa: E712
            stat_col.isnot(None),
        )
    )
    for filter_item in parsed.filters:
        filter_attr = "w" if filter_item.metric_key == "wins" else filter_item.metric_key
        if hasattr(TeamSeasonStat, filter_attr):
            query = query.filter(getattr(TeamSeasonStat, filter_attr) >= filter_item.value)
    order_col = stat_col.asc() if parsed.sort_direction == "asc" else stat_col.desc()
    raw_rows = query.order_by(order_col, TeamSeasonStat.w.desc()).limit(parsed.limit).all()
    rows = []
    for index, (team_stats, team) in enumerate(raw_rows, start=1):
        value = getattr(team_stats, attr_name)
        rows.append(
            QueryResultRow(
                rank=index,
                entity_type="team",
                entity_id=str(team.id),
                name=_team_display_name(team),
                subtitle=f"{team_stats.w or 0}-{team_stats.l or 0} - {team.conference or 'NBA'}",
                abbreviation=team.abbreviation,
                value=float(value) if value is not None else None,
                formatted_value=format_metric_value(metric, float(value)) if value is not None else "-",
                detail_url=f"/teams/{team.abbreviation}",
                metrics={
                    "wins": team_stats.w,
                    "losses": team_stats.l,
                    "pts_pg": team_stats.pts_pg,
                    "off_rating": team_stats.off_rating,
                    "def_rating": team_stats.def_rating,
                    "net_rating": team_stats.net_rating,
                    "pace": team_stats.pace,
                },
            )
        )
    title = _ranking_title(parsed, metric)
    if rows:
        top = rows[0]
        direction = "leads" if parsed.sort_direction == "desc" else "has the lowest mark in"
        summary = f"{top.name} {direction} this result set at {top.formatted_value}."
        primary_value = top.formatted_value
        href = top.detail_url
    else:
        summary = "No teams matched that query with the current synced data."
        primary_value = "No rows"
        href = None
    return _response(parsed, rows, title, summary, metric.label, primary_value, href)


def _answer_player_recent(db: Session, parsed: ParsedQuery) -> QueryAskResponse:
    assert parsed.player is not None
    rows = (
        db.query(PlayerGameLog)
        .filter(
            PlayerGameLog.player_id == parsed.player.id,
            PlayerGameLog.season == parsed.season,
            PlayerGameLog.season_type == "Regular Season",
        )
        .order_by(PlayerGameLog.game_date.desc(), PlayerGameLog.game_id.desc())
        .limit(10)
        .all()
    )
    result_rows: list[QueryResultRow] = []
    for index, game in enumerate(rows, start=1):
        result_rows.append(
            QueryResultRow(
                rank=index,
                entity_type="game",
                entity_id=game.game_id,
                name=game.matchup or game.game_id,
                subtitle=f"{game.game_date.isoformat() if game.game_date else 'Date TBD'} - {game.wl or '-'}",
                value=float(game.pts) if game.pts is not None else None,
                formatted_value=f"{game.pts or 0} PTS",
                detail_url=f"/games/{game.game_id}",
                metrics={
                    "pts": game.pts,
                    "reb": game.reb,
                    "ast": game.ast,
                    "min": game.min,
                    "plus_minus": game.plus_minus,
                },
            )
        )
    player_name = canonical_player_name(parsed.player.full_name, parsed.player.first_name or "", parsed.player.last_name or "")
    if rows:
        averages = {
            "pts": _average(row.pts for row in rows),
            "reb": _average(row.reb for row in rows),
            "ast": _average(row.ast for row in rows),
        }
        summary = (
            f"{player_name}'s last {len(rows)} synced games: "
            f"{averages['pts']:.1f} PPG, {averages['reb']:.1f} RPG, {averages['ast']:.1f} APG."
        )
        primary_value = f"{averages['pts']:.1f} PPG"
    else:
        summary = f"No recent game logs are synced for {player_name} in {parsed.season}."
        primary_value = "No games"
    return _response(
        parsed,
        result_rows,
        f"{player_name} Recent Form",
        summary,
        "Last 10",
        primary_value,
        f"/players/{parsed.player.id}",
        metric_keys=[],
    )


def _answer_team_recent(db: Session, parsed: ParsedQuery) -> QueryAskResponse:
    assert parsed.team is not None
    rows = (
        db.query(GameTeamStat, WarehouseGame)
        .join(WarehouseGame, WarehouseGame.game_id == GameTeamStat.game_id)
        .filter(
            GameTeamStat.team_id == parsed.team.id,
            GameTeamStat.season == parsed.season,
            GameTeamStat.won.isnot(None),
            WarehouseGame.status == "final",
        )
        .order_by(WarehouseGame.game_date.desc(), WarehouseGame.game_id.desc())
        .limit(10)
        .all()
    )
    result_rows: list[QueryResultRow] = []
    margins: list[float] = []
    wins = 0
    for index, (team_stat, game) in enumerate(rows, start=1):
        is_home = bool(team_stat.is_home)
        opponent = game.away_team_abbreviation if is_home else game.home_team_abbreviation
        opponent_score = game.away_score if is_home else game.home_score
        margin = None
        if team_stat.pts is not None and opponent_score is not None:
            margin = float(team_stat.pts) - float(opponent_score)
            margins.append(margin)
        if team_stat.won:
            wins += 1
        result_rows.append(
            QueryResultRow(
                rank=index,
                entity_type="game",
                entity_id=game.game_id,
                name=f"{parsed.team.abbreviation} {'vs' if is_home else 'at'} {opponent or 'TBD'}",
                subtitle=f"{game.game_date.isoformat() if game.game_date else 'Date TBD'} - {'W' if team_stat.won else 'L'}",
                value=margin,
                formatted_value=f"{margin:+.0f}" if margin is not None else "-",
                detail_url=f"/games/{game.game_id}",
                metrics={
                    "pts": team_stat.pts,
                    "reb": team_stat.reb,
                    "ast": team_stat.ast,
                    "plus_minus": margin,
                },
            )
        )
    team_name = _team_display_name(parsed.team)
    if rows:
        avg_margin = round(sum(margins) / len(margins), 1) if margins else 0.0
        summary = f"{team_name}'s last {len(rows)} synced games: {wins}-{len(rows) - wins}, {avg_margin:+.1f} average margin."
        primary_value = f"{avg_margin:+.1f}"
    else:
        summary = f"No recent final games are synced for {team_name} in {parsed.season}."
        primary_value = "No games"
    return _response(
        parsed,
        result_rows,
        f"{team_name} Recent Form",
        summary,
        "Avg margin",
        primary_value,
        f"/teams/{parsed.team.abbreviation}",
        metric_keys=[],
    )


def _answer_player_lookup(db: Session, parsed: ParsedQuery) -> QueryAskResponse:
    assert parsed.player is not None
    stat = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.player_id == parsed.player.id,
            SeasonStat.season == parsed.season,
            SeasonStat.is_playoff == False,  # noqa: E712
        )
        .order_by(SeasonStat.gp.desc())
        .first()
    )
    name = canonical_player_name(parsed.player.full_name, parsed.player.first_name or "", parsed.player.last_name or "")
    metrics: dict[str, Any] = {}
    summary = f"Open {name}'s profile for the full player dashboard."
    primary_value = parsed.player.position or "Player profile"
    if stat:
        metrics = {
            "pts_pg": stat.pts_pg,
            "reb_pg": stat.reb_pg,
            "ast_pg": stat.ast_pg,
            "ts_pct": stat.ts_pct,
        }
        summary = f"{name} is at {stat.pts_pg or 0:.1f} PPG, {stat.reb_pg or 0:.1f} RPG, and {stat.ast_pg or 0:.1f} APG in {parsed.season}."
        primary_value = f"{stat.pts_pg or 0:.1f} PPG"
    rows = [
        QueryResultRow(
            rank=1,
            entity_type="player",
            entity_id=str(parsed.player.id),
            name=name,
            subtitle=stat.team_abbreviation if stat else parsed.player.position,
            detail_url=f"/players/{parsed.player.id}",
            metrics=metrics,
        )
    ]
    return _response(parsed, rows, name, summary, "Profile", primary_value, f"/players/{parsed.player.id}", metric_keys=[])


def _answer_team_lookup(db: Session, parsed: ParsedQuery) -> QueryAskResponse:
    assert parsed.team is not None
    stat = (
        db.query(TeamSeasonStat)
        .filter(
            TeamSeasonStat.team_id == parsed.team.id,
            TeamSeasonStat.season == parsed.season,
            TeamSeasonStat.is_playoff == False,  # noqa: E712
        )
        .first()
    )
    name = _team_display_name(parsed.team)
    summary = f"Open {name}'s team page for roster, style, and matchup context."
    primary_value = parsed.team.abbreviation
    metrics: dict[str, Any] = {}
    if stat:
        summary = f"{name} is {stat.w or 0}-{stat.l or 0} with a {stat.net_rating or 0:.1f} net rating in {parsed.season}."
        primary_value = f"{stat.w or 0}-{stat.l or 0}"
        metrics = {
            "wins": stat.w,
            "losses": stat.l,
            "off_rating": stat.off_rating,
            "def_rating": stat.def_rating,
            "net_rating": stat.net_rating,
        }
    rows = [
        QueryResultRow(
            rank=1,
            entity_type="team",
            entity_id=str(parsed.team.id),
            name=name,
            abbreviation=parsed.team.abbreviation,
            detail_url=f"/teams/{parsed.team.abbreviation}",
            metrics=metrics,
        )
    ]
    return _response(parsed, rows, name, summary, "Team", primary_value, f"/teams/{parsed.team.abbreviation}", metric_keys=[])


def _answer_compare_players(parsed: ParsedQuery) -> QueryAskResponse:
    assert parsed.compare_players is not None
    player_a, player_b = parsed.compare_players
    name_a = canonical_player_name(player_a.full_name, player_a.first_name or "", player_a.last_name or "")
    name_b = canonical_player_name(player_b.full_name, player_b.first_name or "", player_b.last_name or "")
    href = f"/compare?playerA={player_a.id}&playerB={player_b.id}&season={parsed.season}"
    rows = [
        QueryResultRow(rank=1, entity_type="player", entity_id=str(player_a.id), name=name_a, detail_url=f"/players/{player_a.id}"),
        QueryResultRow(rank=2, entity_type="player", entity_id=str(player_b.id), name=name_b, detail_url=f"/players/{player_b.id}"),
    ]
    return _response(
        parsed,
        rows,
        f"Compare {name_a} and {name_b}",
        "I found both players. Open Compare for the side-by-side workspace.",
        "Compare",
        "Open",
        href,
        metric_keys=[],
    )


def _response(
    parsed: ParsedQuery,
    rows: list[QueryResultRow],
    title: str,
    summary: str,
    primary_label: Optional[str],
    primary_value: Optional[str],
    href: Optional[str],
    metric_keys: Optional[list[str]] = None,
) -> QueryAskResponse:
    intent = _intent(parsed)
    if metric_keys is None:
        metric_keys = [parsed.metric.key] if parsed.metric else []
        metric_keys += [filter_item.metric_key for filter_item in parsed.filters]
    metrics = [
        QueryMetricMetadata(**metric_to_metadata(METRICS_BY_KEY[key]))
        for key in dict.fromkeys(metric_keys)
        if key in METRICS_BY_KEY
    ]
    return QueryAskResponse(
        question=parsed.question,
        status="ready" if rows else "empty",
        answer=QueryAnswerCard(
            title=title,
            summary=summary,
            primary_label=primary_label,
            primary_value=primary_value,
            href=href,
        ),
        intent=intent,
        rows=rows,
        metrics=metrics,
        warnings=[] if rows else ["No local rows matched the interpreted query."],
        suggestions=_followups(parsed),
    )


def _clarification_response(parsed: ParsedQuery, warning: Optional[str] = None) -> QueryAskResponse:
    warnings = [warning] if warning else ["I could not confidently map that question to the current player or team metric registry."]
    return QueryAskResponse(
        question=parsed.question,
        status="needs_clarification",
        answer=QueryAnswerCard(
            title="Try a basketball metric question",
            summary="Ask for a player leaderboard, team ranking, threshold filter, recent form, or a player comparison.",
            primary_label="Examples",
            primary_value="5 starters",
            href="/ask",
        ),
        intent=_intent(parsed),
        rows=[],
        metrics=[],
        warnings=warnings,
        suggestions=DEFAULT_SUGGESTIONS,
    )


def _intent(parsed: ParsedQuery) -> QueryIntent:
    return QueryIntent(
        intent_type=parsed.intent_type,
        entity_type=parsed.entity_type,
        metric_key=parsed.metric.key if parsed.metric else None,
        metric_label=parsed.metric.label if parsed.metric else None,
        season=parsed.season,
        sort_direction=parsed.sort_direction,  # type: ignore[arg-type]
        limit=parsed.limit,
        confidence=parsed.confidence,
        normalized_question=parsed.normalized,
        filters=parsed.filters,
    )


def _ranking_title(parsed: ParsedQuery, metric: QueryMetricDefinition) -> str:
    entity_label = "Players" if parsed.entity_type == "player" else "Teams"
    direction = "Lowest" if parsed.sort_direction == "asc" else "Top"
    return f"{direction} {entity_label} by {metric.label}"


def _followups(parsed: ParsedQuery) -> list[str]:
    if parsed.entity_type == "team":
        return [
            f"Best teams by offensive rating in {parsed.season}",
            f"Lowest defensive rating by a team in {parsed.season}",
            f"Best teams by pace in {parsed.season}",
        ]
    return [
        f"Top 10 players in true shooting in {parsed.season}",
        f"Players with at least 25 ppg and 60 ts% in {parsed.season}",
        f"Top players by net rating in {parsed.season}",
    ]


def _average(values: Any) -> float:
    clean = [float(value) for value in values if value is not None]
    return round(sum(clean) / len(clean), 1) if clean else 0.0


def _team_display_name(team: Team) -> str:
    city = (team.city or "").strip()
    name = (team.name or "").strip()
    if city and name and not name.startswith(city):
        return f"{city} {name}"
    return name or city or team.abbreviation or "Team"
