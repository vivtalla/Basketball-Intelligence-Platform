from typing import Dict, List, Literal, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import LineupStats, Player, Team, TeamSeasonStat
from models.lineups import (
    LineupArchetype,
    LineupLeaderboardEntry,
    LineupLeaderboardResult,
)

_SHRINK_PRIOR = 150.0

_SORT_FIELDS = {
    "net_rating": "net_rating",
    "ortg": "ortg",
    "drtg": "drtg",
    "plus_minus": "plus_minus",
    "possessions": "possessions",
    "minutes": "minutes",
}


def _lineup_confidence(possessions: Optional[int]) -> Literal["high", "medium", "low"]:
    if possessions is None:
        return "low"
    if possessions >= 200:
        return "high"
    if possessions >= 80:
        return "medium"
    return "low"


def _classify_lineup(
    net_vs_baseline: Optional[float],
    ortg_delta: Optional[float],
    drtg_delta: Optional[float],
) -> LineupArchetype:
    """
    ortg_delta = lineup_ortg - team_off_rating  (positive = better offense)
    drtg_delta = team_def_rating - lineup_drtg  (positive = better defense)
    """
    if net_vs_baseline is None:
        return "Unclassified"
    if net_vs_baseline >= 5:
        return "Elite"
    if net_vs_baseline <= -4:
        return "Negative"
    if ortg_delta is not None and drtg_delta is not None:
        if ortg_delta >= 4 and drtg_delta < -2:
            return "Offensive Wall"
        if drtg_delta >= 4 and ortg_delta < 1:
            return "Defensive Wall"
    return "Balanced"


def _shrink(
    net_rating: Optional[float],
    team_net: Optional[float],
    possessions: Optional[int],
) -> Optional[float]:
    if net_rating is None:
        return None
    if team_net is None or possessions is None or possessions <= 0:
        return round(net_rating, 2)
    w = possessions / (possessions + _SHRINK_PRIOR)
    return round(net_rating * w + team_net * (1.0 - w), 2)


def _parse_player_ids(lineup_key: str) -> List[int]:
    return [int(x) for x in lineup_key.split("-") if x]


def _build_entry(
    row: LineupStats,
    name_map: Dict[int, str],
    team_abbr_map: Dict[int, str],
    team_baseline: Dict[int, Tuple[Optional[float], Optional[float], Optional[float]]],
) -> LineupLeaderboardEntry:
    player_ids = _parse_player_ids(row.lineup_key)
    player_names = [name_map.get(pid, str(pid)) for pid in player_ids]
    abbr = team_abbr_map.get(row.team_id) if row.team_id else None

    t_net, t_off, t_def = team_baseline.get(row.team_id, (None, None, None)) if row.team_id else (None, None, None)

    net_vs = None
    if row.net_rating is not None and t_net is not None:
        net_vs = round(row.net_rating - t_net, 2)

    ortg_delta = None
    if row.ortg is not None and t_off is not None:
        ortg_delta = round(row.ortg - t_off, 2)

    drtg_delta = None
    if row.drtg is not None and t_def is not None:
        drtg_delta = round(t_def - row.drtg, 2)

    shrunk = _shrink(row.net_rating, t_net, row.possessions)
    confidence = _lineup_confidence(row.possessions)
    archetype = _classify_lineup(net_vs, ortg_delta, drtg_delta)

    return LineupLeaderboardEntry(
        lineup_key=row.lineup_key,
        player_ids=player_ids,
        player_names=player_names,
        team_id=row.team_id,
        team_abbreviation=abbr,
        season=row.season,
        minutes=round(row.minutes, 1) if row.minutes is not None else None,
        possessions=row.possessions,
        net_rating=round(row.net_rating, 2) if row.net_rating is not None else None,
        ortg=round(row.ortg, 2) if row.ortg is not None else None,
        drtg=round(row.drtg, 2) if row.drtg is not None else None,
        plus_minus=round(row.plus_minus, 1) if row.plus_minus is not None else None,
        shrunk_net_rating=shrunk,
        team_net_baseline=round(t_net, 2) if t_net is not None else None,
        net_vs_baseline=net_vs,
        confidence=confidence,
        archetype=archetype,
    )


def build_lineup_leaderboard(
    db: Session,
    season: str,
    season_type: str = "Regular Season",
    team_id: Optional[int] = None,
    min_possessions: int = 100,
    sort_by: str = "net_rating",
    sort_dir: str = "desc",
    limit: int = 50,
) -> LineupLeaderboardResult:
    is_playoff = season_type == "Playoffs"

    q = db.query(LineupStats).filter(
        LineupStats.season == season,
        LineupStats.is_playoff == is_playoff,
        LineupStats.possessions >= min_possessions,
        LineupStats.net_rating.isnot(None),
    )
    if team_id is not None:
        q = q.filter(LineupStats.team_id == team_id)

    rows: List[LineupStats] = q.all()

    # Batch: collect all player_ids and team_ids
    all_player_ids: List[int] = []
    team_ids: List[int] = []
    for row in rows:
        all_player_ids.extend(_parse_player_ids(row.lineup_key))
        if row.team_id is not None:
            team_ids.append(row.team_id)

    unique_pids = list(set(all_player_ids))
    unique_tids = list(set(team_ids))

    name_map: Dict[int, str] = {}
    if unique_pids:
        players = db.query(Player).filter(Player.id.in_(unique_pids)).all()
        name_map = {p.id: p.full_name for p in players}

    team_abbr_map: Dict[int, str] = {}
    # Dict[team_id] → (net_rating, off_rating, def_rating)
    team_baseline: Dict[int, Tuple[Optional[float], Optional[float], Optional[float]]] = {}
    if unique_tids:
        tss_rows = (
            db.query(TeamSeasonStat, Team)
            .join(Team, TeamSeasonStat.team_id == Team.id)
            .filter(
                TeamSeasonStat.team_id.in_(unique_tids),
                TeamSeasonStat.season == season,
                TeamSeasonStat.is_playoff == is_playoff,
            )
            .all()
        )
        for tss, team in tss_rows:
            team_abbr_map[tss.team_id] = team.abbreviation
            team_baseline[tss.team_id] = (tss.net_rating, tss.off_rating, tss.def_rating)

    entries = [_build_entry(row, name_map, team_abbr_map, team_baseline) for row in rows]

    # Sort
    reverse = sort_dir != "asc"
    attr = _SORT_FIELDS.get(sort_by, "net_rating")

    def _sort_key(e: LineupLeaderboardEntry) -> float:
        val = getattr(e, attr, None)
        if val is None:
            return float("-inf") if reverse else float("inf")
        return val

    entries.sort(key=_sort_key, reverse=reverse)
    entries = entries[:limit]

    return LineupLeaderboardResult(season=season, total=len(entries), lineups=entries)
