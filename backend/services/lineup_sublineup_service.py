import itertools
from collections import defaultdict
from typing import DefaultDict, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import LineupStats, Player, Team, TeamSeasonStat
from models.lineups import LineupLeaderboardEntry, SublineupsResult
from services.lineup_leaderboard_service import (
    _build_entry,
    _lineup_confidence,
    _parse_player_ids,
)

_PRE_FILTER_POSS = 25
_MAX_RESULTS = 20


def build_sublineups(
    db: Session,
    team_id: int,
    season: str,
    is_playoff: bool = False,
    size: int = 5,
    min_possessions: int = 50,
) -> SublineupsResult:
    if size == 5:
        return _build_five_man(db, team_id, season, is_playoff, min_possessions)
    return _build_sub(db, team_id, season, is_playoff, size, min_possessions)


def _build_five_man(
    db: Session,
    team_id: int,
    season: str,
    is_playoff: bool,
    min_possessions: int,
) -> SublineupsResult:
    from services.lineup_leaderboard_service import build_lineup_leaderboard

    result = build_lineup_leaderboard(
        db,
        season=season,
        season_type="Playoffs" if is_playoff else "Regular Season",
        team_id=team_id,
        min_possessions=min_possessions,
        sort_by="net_rating",
        sort_dir="desc",
        limit=_MAX_RESULTS,
    )

    team_abbr = result.lineups[0].team_abbreviation if result.lineups else ""
    return SublineupsResult(
        team_id=team_id,
        team_abbreviation=team_abbr or "",
        season=season,
        size=5,
        lineups=result.lineups,
    )


def _build_sub(
    db: Session,
    team_id: int,
    season: str,
    is_playoff: bool,
    size: int,
    min_possessions: int,
) -> SublineupsResult:
    five_man_rows: List[LineupStats] = (
        db.query(LineupStats)
        .filter(
            LineupStats.team_id == team_id,
            LineupStats.season == season,
            LineupStats.is_playoff == is_playoff,
            LineupStats.possessions >= _PRE_FILTER_POSS,
        )
        .all()
    )

    # Aggregate sub-combinations across all 5-man lineups
    combo_poss: DefaultDict[str, int] = defaultdict(int)
    combo_nr_weighted: DefaultDict[str, float] = defaultdict(float)
    combo_minutes: DefaultDict[str, float] = defaultdict(float)

    for row in five_man_rows:
        player_ids = _parse_player_ids(row.lineup_key)
        if len(player_ids) < size:
            continue
        poss = row.possessions or 0
        mins = row.minutes or 0.0
        for combo in itertools.combinations(sorted(player_ids), size):
            key = "-".join(str(p) for p in combo)
            combo_poss[key] += poss
            if row.net_rating is not None:
                combo_nr_weighted[key] += row.net_rating * poss
            combo_minutes[key] += mins

    # Build synthetic LineupStats-like objects and filter
    results: List[Tuple[str, int, float, float]] = []
    for key, total_poss in combo_poss.items():
        if total_poss < min_possessions:
            continue
        avg_nr = combo_nr_weighted[key] / total_poss if total_poss > 0 else 0.0
        results.append((key, total_poss, avg_nr, combo_minutes[key]))

    results.sort(key=lambda x: x[2], reverse=True)
    results = results[:_MAX_RESULTS]

    if not results:
        team_abbr = _get_team_abbr(db, team_id, season, is_playoff)
        return SublineupsResult(
            team_id=team_id,
            team_abbreviation=team_abbr,
            season=season,
            size=size,
            lineups=[],
        )

    # Resolve player names and team info
    all_pids: List[int] = []
    for key, _, _, _ in results:
        all_pids.extend(_parse_player_ids(key))
    unique_pids = list(set(all_pids))

    name_map: Dict[int, str] = {}
    if unique_pids:
        players = db.query(Player).filter(Player.id.in_(unique_pids)).all()
        name_map = {p.id: p.full_name for p in players}

    team_abbr_map: Dict[int, str] = {}
    team_baseline: Dict[int, Tuple[Optional[float], Optional[float], Optional[float]]] = {}
    tss_rows = (
        db.query(TeamSeasonStat, Team)
        .join(Team, TeamSeasonStat.team_id == Team.id)
        .filter(
            TeamSeasonStat.team_id == team_id,
            TeamSeasonStat.season == season,
            TeamSeasonStat.is_playoff == is_playoff,
        )
        .first()
    )
    team_abbr = ""
    if tss_rows:
        tss, team = tss_rows
        team_abbr = team.abbreviation
        team_abbr_map[tss.team_id] = team.abbreviation
        team_baseline[tss.team_id] = (tss.net_rating, tss.off_rating, tss.def_rating)

    # Build entries using synthetic LineupStats-like data via a simple struct
    entries: List[LineupLeaderboardEntry] = []
    t_net, t_off, t_def = team_baseline.get(team_id, (None, None, None))
    abbr = team_abbr_map.get(team_id, "")

    for key, total_poss, avg_nr, total_mins in results:
        player_ids = _parse_player_ids(key)
        player_names = [name_map.get(pid, str(pid)) for pid in player_ids]

        net_vs = round(avg_nr - t_net, 2) if t_net is not None else None
        shrunk = None
        if total_poss > 0 and t_net is not None:
            from services.lineup_leaderboard_service import _shrink
            shrunk = _shrink(avg_nr, t_net, total_poss)

        ortg_delta = None
        drtg_delta = None
        from services.lineup_leaderboard_service import _classify_lineup
        archetype = _classify_lineup(net_vs, ortg_delta, drtg_delta)
        confidence = _lineup_confidence(total_poss)

        entries.append(
            LineupLeaderboardEntry(
                lineup_key=key,
                player_ids=player_ids,
                player_names=player_names,
                team_id=team_id,
                team_abbreviation=abbr,
                season=season,
                minutes=round(total_mins, 1),
                possessions=total_poss,
                net_rating=round(avg_nr, 2),
                ortg=None,
                drtg=None,
                plus_minus=None,
                shrunk_net_rating=shrunk,
                team_net_baseline=round(t_net, 2) if t_net is not None else None,
                net_vs_baseline=net_vs,
                confidence=confidence,
                archetype=archetype,
            )
        )

    return SublineupsResult(
        team_id=team_id,
        team_abbreviation=team_abbr,
        season=season,
        size=size,
        lineups=entries,
    )


def _get_team_abbr(db: Session, team_id: int, season: str, is_playoff: bool) -> str:
    row = (
        db.query(TeamSeasonStat, Team)
        .join(Team, TeamSeasonStat.team_id == Team.id)
        .filter(
            TeamSeasonStat.team_id == team_id,
            TeamSeasonStat.season == season,
            TeamSeasonStat.is_playoff == is_playoff,
        )
        .first()
    )
    if row:
        _, team = row
        return team.abbreviation
    team = db.query(Team).filter(Team.id == team_id).first()
    return team.abbreviation if team else ""
