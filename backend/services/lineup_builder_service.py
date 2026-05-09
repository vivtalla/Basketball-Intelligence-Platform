from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from db.models import LineupStats, Player, Team, TeamSeasonStat
from models.lineups import (
    LineupBuilderResult,
    LineupLeaderboardEntry,
    PlayerRemovalImpact,
)
from services.lineup_leaderboard_service import (
    _build_entry,
    _lineup_confidence,
    _parse_player_ids,
    _shrink,
)

_SMALL_SAMPLE_POSS = 80
_OVERFETCH_MULT = 3
_MAX_CLOSEST = 3


def _overlap_score(submitted: Set[int], candidate_key: str) -> int:
    candidate_ids = set(_parse_player_ids(candidate_key))
    return len(submitted & candidate_ids)


def _build_name_team_maps(
    db: Session,
    player_ids: List[int],
    team_ids: List[int],
    season: str,
    is_playoff: bool,
) -> Tuple[Dict[int, str], Dict[int, str], Dict[int, Tuple[Optional[float], Optional[float], Optional[float]]]]:
    name_map: Dict[int, str] = {}
    if player_ids:
        players = db.query(Player).filter(Player.id.in_(player_ids)).all()
        name_map = {p.id: p.full_name for p in players}

    team_abbr_map: Dict[int, str] = {}
    team_baseline: Dict[int, Tuple[Optional[float], Optional[float], Optional[float]]] = {}
    unique_tids = list(set(t for t in team_ids if t is not None))
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

    return name_map, team_abbr_map, team_baseline


def _row_to_entry(
    row: LineupStats,
    name_map: Dict[int, str],
    team_abbr_map: Dict[int, str],
    team_baseline: Dict[int, Tuple[Optional[float], Optional[float], Optional[float]]],
) -> LineupLeaderboardEntry:
    return _build_entry(row, name_map, team_abbr_map, team_baseline)


def _compute_removal_impacts(
    db: Session,
    submitted_ids: List[int],
    name_map: Dict[int, str],
    season: str,
    is_playoff: bool,
    reference_nr: Optional[float],
) -> List[PlayerRemovalImpact]:
    impacts: List[PlayerRemovalImpact] = []
    for pid in submitted_ids:
        remaining = [x for x in submitted_ids if x != pid]
        if not remaining:
            continue

        # Find all lineups containing ALL remaining players
        # Use LIKE for first remaining player, then post-parse intersect
        q = db.query(LineupStats).filter(
            LineupStats.season == season,
            LineupStats.is_playoff == is_playoff,
            LineupStats.possessions.isnot(None),
        )
        for rid in remaining:
            q = q.filter(LineupStats.lineup_key.like("%{0}%".format(rid)))

        candidates: List[LineupStats] = q.limit(len(remaining) * _OVERFETCH_MULT * 20).all()

        remaining_set = set(remaining)
        qualifying: List[LineupStats] = []
        for c in candidates:
            ids_in_lineup = set(_parse_player_ids(c.lineup_key))
            # Must contain all remaining players and NOT contain the removed player
            if remaining_set.issubset(ids_in_lineup) and pid not in ids_in_lineup:
                qualifying.append(c)

        avg_nr: Optional[float] = None
        delta: Optional[float] = None
        if qualifying:
            nr_vals = [r.net_rating for r in qualifying if r.net_rating is not None]
            if nr_vals:
                avg_nr = round(sum(nr_vals) / len(nr_vals), 2)
                if reference_nr is not None:
                    delta = round(avg_nr - reference_nr, 2)

        note = ""
        if not qualifying:
            note = "No qualifying lineups found without this player."
        elif len(qualifying) < 3:
            note = "Limited sample ({0} lineup{1}) without this player.".format(
                len(qualifying), "s" if len(qualifying) != 1 else ""
            )

        player_name = name_map.get(pid, str(pid))
        impacts.append(
            PlayerRemovalImpact(
                player_id=pid,
                player_name=player_name,
                lineups_without_count=len(qualifying),
                avg_net_rating_without=avg_nr,
                delta_vs_full=delta,
                note=note,
            )
        )
    return impacts


def build_lineup_builder_result(
    db: Session,
    player_ids: List[int],
    season: str,
    season_type: str = "Regular Season",
) -> LineupBuilderResult:
    is_playoff = season_type == "Playoffs"
    sorted_ids = sorted(player_ids)
    exact_key = "-".join(str(p) for p in sorted_ids)

    # Exact match
    exact_row: Optional[LineupStats] = (
        db.query(LineupStats)
        .filter(
            LineupStats.lineup_key == exact_key,
            LineupStats.season == season,
            LineupStats.is_playoff == is_playoff,
        )
        .first()
    )

    # Candidates for partial match
    submitted_set: Set[int] = set(sorted_ids)
    all_rows: List[LineupStats] = (
        db.query(LineupStats)
        .filter(
            LineupStats.season == season,
            LineupStats.is_playoff == is_playoff,
            LineupStats.net_rating.isnot(None),
        )
        .all()
    )

    # Score by overlap, exclude exact match, pick top _MAX_CLOSEST
    scored: List[Tuple[int, LineupStats]] = []
    for row in all_rows:
        if row.lineup_key == exact_key:
            continue
        score = _overlap_score(submitted_set, row.lineup_key)
        if score > 0:
            scored.append((score, row))
    scored.sort(key=lambda x: (x[0], x[1].net_rating or 0.0), reverse=True)
    closest_rows = [r for _, r in scored[:_MAX_CLOSEST]]

    # Gather all player ids and team ids for batch name/team lookups
    all_pids: List[int] = list(sorted_ids)
    all_tids: List[int] = []
    candidate_rows = ([exact_row] if exact_row else []) + closest_rows
    for cr in candidate_rows:
        all_pids.extend(_parse_player_ids(cr.lineup_key))
        if cr.team_id is not None:
            all_tids.append(cr.team_id)
    unique_pids = list(set(all_pids))

    name_map, team_abbr_map, team_baseline = _build_name_team_maps(
        db, unique_pids, all_tids, season, is_playoff
    )

    submitted_names = [name_map.get(pid, str(pid)) for pid in sorted_ids]

    exact_entry: Optional[LineupLeaderboardEntry] = None
    if exact_row:
        exact_entry = _row_to_entry(exact_row, name_map, team_abbr_map, team_baseline)

    closest_entries = [
        _row_to_entry(r, name_map, team_abbr_map, team_baseline) for r in closest_rows
    ]

    if exact_entry:
        match_quality = "exact"
        reference_nr = exact_entry.net_rating
    elif closest_entries:
        match_quality = "partial"
        reference_nr = closest_entries[0].net_rating
    else:
        match_quality = "none"
        reference_nr = None

    removal_impacts = _compute_removal_impacts(
        db, sorted_ids, name_map, season, is_playoff, reference_nr
    )

    warnings: List[str] = []
    if exact_entry and exact_entry.possessions is not None and exact_entry.possessions < _SMALL_SAMPLE_POSS:
        warnings.append(
            "Exact match has only {0} possessions — net rating is highly variable. "
            "Shrunk estimate is more reliable.".format(exact_entry.possessions)
        )
    if match_quality == "partial":
        warnings.append(
            "No exact 5-man lineup found. Showing closest overlapping lineups from the database."
        )
    if match_quality == "none":
        warnings.append("No lineups found in the database containing these players for this season.")

    return LineupBuilderResult(
        submitted_player_ids=sorted_ids,
        submitted_player_names=submitted_names,
        exact_match=exact_entry,
        closest_matches=closest_entries,
        player_removal_impacts=removal_impacts,
        match_quality=match_quality,
        warnings=warnings,
    )
