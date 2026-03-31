from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import GamePlayerStat, GameTeamStat, Player
from models.insights import TrajectoryPlayerRow, TrajectoryResponse


TRAJECTORY_WEIGHTS = {
    "ts_pct": 0.25,
    "pts": 0.20,
    "usg_pct": 0.20,
    "ast": 0.15,
    "tov_pct": -0.10,
    "reb": 0.10,
}


def _estimate_possessions(fga: Optional[float], oreb: Optional[float], tov: Optional[float], fta: Optional[float]) -> Optional[float]:
    if fga is None or oreb is None or tov is None or fta is None:
        return None
    possessions = float(fga) - float(oreb) + float(tov) + (0.44 * float(fta))
    if possessions <= 0:
        return None
    return possessions


def _aggregate_split(rows: Sequence[GamePlayerStat], team_rows: Dict[Tuple[str, str], GameTeamStat]) -> Dict[str, Optional[float]]:
    if not rows:
        return {
            "games": 0,
            "minutes": None,
            "pts": None,
            "reb": None,
            "ast": None,
            "stl": None,
            "blk": None,
            "ts_pct": None,
            "usg_pct": None,
            "tov_pct": None,
            "plus_minus": None,
        }

    games = float(len(rows))
    sum_minutes = sum(float(row.min or 0.0) for row in rows)
    sum_pts = sum(float(row.pts or 0.0) for row in rows)
    sum_reb = sum(float(row.reb or 0.0) for row in rows)
    sum_ast = sum(float(row.ast or 0.0) for row in rows)
    sum_stl = sum(float(row.stl or 0.0) for row in rows)
    sum_blk = sum(float(row.blk or 0.0) for row in rows)
    sum_pm = sum(float(row.plus_minus or 0.0) for row in rows)
    sum_fga = sum(float(row.fga or 0.0) for row in rows)
    sum_fta = sum(float(row.fta or 0.0) for row in rows)
    sum_tov = sum(float(row.tov or 0.0) for row in rows)

    total_team_possessions = 0.0
    total_usage_numerator = 0.0
    for row in rows:
        team_row = team_rows.get((row.game_id, row.team_abbreviation or ""))
        team_possessions = None
        if team_row is not None:
            team_possessions = _estimate_possessions(
                team_row.fga,
                team_row.oreb,
                team_row.tov,
                team_row.fta,
            )
        usage_numerator = float(row.fga or 0.0) + (0.44 * float(row.fta or 0.0)) + float(row.tov or 0.0)
        if team_possessions:
            total_team_possessions += team_possessions
            total_usage_numerator += usage_numerator

    ts_pct = None
    ts_denominator = 2 * (sum_fga + (0.44 * sum_fta))
    if ts_denominator > 0:
        ts_pct = sum_pts / ts_denominator

    usg_pct = None
    if sum_minutes > 0 and total_team_possessions > 0:
        usg_pct = (total_usage_numerator / total_team_possessions) * 100.0

    tov_pct = None
    tov_denominator = sum_fga + (0.44 * sum_fta) + sum_tov
    if tov_denominator > 0:
        tov_pct = (sum_tov / tov_denominator) * 100.0

    return {
        "games": int(games),
        "minutes": sum_minutes / games,
        "pts": sum_pts / games,
        "reb": sum_reb / games,
        "ast": sum_ast / games,
        "stl": sum_stl / games,
        "blk": sum_blk / games,
        "ts_pct": ts_pct,
        "usg_pct": usg_pct,
        "tov_pct": tov_pct,
        "plus_minus": sum_pm / games,
    }


def _delta(recent: Dict[str, Optional[float]], baseline: Dict[str, Optional[float]], key: str) -> Optional[float]:
    recent_value = recent.get(key)
    baseline_value = baseline.get(key)
    if recent_value is None or baseline_value is None:
        return None
    return recent_value - baseline_value


def _zscore_map(values_by_player: Dict[int, float]) -> Dict[int, float]:
    values = list(values_by_player.values())
    if len(values) < 2:
        return {player_id: 0.0 for player_id in values_by_player}
    mean_value = statistics.mean(values)
    std_value = statistics.stdev(values)
    if not std_value:
        return {player_id: 0.0 for player_id in values_by_player}
    return {
        player_id: (value - mean_value) / std_value
        for player_id, value in values_by_player.items()
    }


def _trajectory_label(zscore: float) -> str:
    if zscore >= 1.5:
        return "Breaking Out"
    if zscore >= 0.5:
        return "Quietly Rising"
    if zscore <= -1.5:
        return "Collapsing"
    if zscore <= -0.5:
        return "Slumping"
    return "Stable"


def _narrative(player_name: str, label: str, top_drivers: Sequence[Tuple[str, float]]) -> str:
    first_driver = top_drivers[0][0] if top_drivers else "pts"
    second_driver = top_drivers[1][0] if len(top_drivers) > 1 else first_driver
    trend_word = "gaining momentum" if label in {"Breaking Out", "Quietly Rising"} else "losing ground"
    return (
        "{0} is {1} lately, with the clearest swing coming from {2} and {3}. "
        "This profile suggests a player who is {4} rather than simply riding one noisy box-score night."
    ).format(
        player_name,
        label.lower(),
        first_driver,
        second_driver,
        trend_word,
    )


def _opponent_from_matchup(matchup: Optional[str], team_abbreviation: str) -> Optional[str]:
    if not matchup:
        return None
    tokens = matchup.replace("vs.", "@").split("@")
    if len(tokens) != 2:
        return None
    left = tokens[0].strip().split(" ")[0]
    right = tokens[1].strip().split(" ")[0]
    if left == team_abbreviation:
        return right
    if right == team_abbreviation:
        return left
    return right


def build_trajectory_report(
    db: Session,
    season: str,
    last_n_games: int,
    player_pool: str,
    min_minutes_per_game: float,
    team_abbreviation: Optional[str] = None,
    position: Optional[str] = None,
) -> TrajectoryResponse:
    if season != "2025-26":
        raise HTTPException(status_code=422, detail="Trajectory Tracker currently supports the 2025-26 season only.")
    if last_n_games < 3:
        raise HTTPException(status_code=422, detail="last_n_games must be at least 3.")

    warnings: List[str] = []
    excluded_players: List[str] = []

    players_query = db.query(Player)
    if player_pool == "position_filter":
        if not position:
            raise HTTPException(status_code=422, detail="position is required for position_filter pools.")
        players_query = players_query.filter(Player.position.isnot(None), Player.position.ilike("%{0}%".format(position)))
    elif player_pool not in {"all", "team_filter"}:
        raise HTTPException(status_code=422, detail="Unsupported player_pool '{0}'.".format(player_pool))

    players = players_query.all()
    player_ids = [player.id for player in players]

    rows_query = (
        db.query(GamePlayerStat, Player)
        .join(Player, GamePlayerStat.player_id == Player.id)
        .filter(GamePlayerStat.season == season)
    )
    if player_ids:
        rows_query = rows_query.filter(GamePlayerStat.player_id.in_(player_ids))
    if player_pool == "team_filter":
        if not team_abbreviation:
            raise HTTPException(status_code=422, detail="team_abbreviation is required for team_filter pools.")
        rows_query = rows_query.filter(GamePlayerStat.team_abbreviation == team_abbreviation)

    game_rows = rows_query.all()
    player_games: Dict[int, List[GamePlayerStat]] = defaultdict(list)
    player_lookup: Dict[int, Player] = {}
    active_teams = set()
    for game_row, player in game_rows:
        player_games[player.id].append(game_row)
        player_lookup[player.id] = player
        if game_row.team_abbreviation:
            active_teams.add(game_row.team_abbreviation)

    for rows in player_games.values():
        rows.sort(key=lambda row: (row.game_date, row.game_id), reverse=True)

    team_rows_query = db.query(GameTeamStat).filter(GameTeamStat.season == season)
    if active_teams:
        team_rows_query = team_rows_query.filter(GameTeamStat.team_abbreviation.in_(list(active_teams)))
    team_rows = team_rows_query.all()
    team_row_lookup: Dict[Tuple[str, str], GameTeamStat] = {
        (row.game_id, row.team_abbreviation or ""): row
        for row in team_rows
    }

    team_games_lookup: Dict[str, List[GameTeamStat]] = defaultdict(list)
    for team_row in team_rows:
        if team_row.team_abbreviation:
            team_games_lookup[team_row.team_abbreviation].append(team_row)
    for rows in team_games_lookup.values():
        rows.sort(key=lambda row: (row.game_id))

    opponent_allowed_points: Dict[str, List[float]] = defaultdict(list)
    opponent_possessions: Dict[str, List[float]] = defaultdict(list)
    by_game_id: Dict[str, List[GameTeamStat]] = defaultdict(list)
    for row in team_rows:
        by_game_id[row.game_id].append(row)

    for game_id, rows in by_game_id.items():
        if len(rows) != 2:
            continue
        first, second = rows[0], rows[1]
        first_possessions = _estimate_possessions(first.fga, first.oreb, first.tov, first.fta)
        second_possessions = _estimate_possessions(second.fga, second.oreb, second.tov, second.fta)
        if first.team_abbreviation and second.pts is not None and first_possessions:
            opponent_allowed_points[first.team_abbreviation].append(float(second.pts))
            opponent_possessions[first.team_abbreviation].append(first_possessions)
        if second.team_abbreviation and first.pts is not None and second_possessions:
            opponent_allowed_points[second.team_abbreviation].append(float(first.pts))
            opponent_possessions[second.team_abbreviation].append(second_possessions)

    team_def_ratings: Dict[str, float] = {}
    for team, points_allowed in opponent_allowed_points.items():
        possessions = sum(opponent_possessions[team])
        if possessions > 0:
            team_def_ratings[team] = (sum(points_allowed) / possessions) * 100.0

    sorted_defenses = sorted(team_def_ratings.items(), key=lambda item: item[1])
    top_five_defenses = {team for team, _ in sorted_defenses[:5]}
    bottom_five_defenses = {team for team, _ in sorted_defenses[-5:]}

    raw_scores: Dict[int, float] = {}
    candidate_rows = []

    for player_id, rows in player_games.items():
        total_games = len(rows)
        player = player_lookup[player_id]
        if total_games < last_n_games + 10:
            excluded_players.append("{0} — insufficient sample".format(player.full_name))
            continue
        if last_n_games > (total_games / 2.0):
            message = "Window too large relative to sample for {0}.".format(player.full_name)
            warnings.append(message)
            excluded_players.append("{0} — window too large relative to sample".format(player.full_name))
            continue

        recent_rows = rows[:last_n_games]
        baseline_rows = rows[last_n_games:]
        recent = _aggregate_split(recent_rows, team_row_lookup)
        baseline = _aggregate_split(baseline_rows, team_row_lookup)

        if recent["minutes"] is None or recent["minutes"] < min_minutes_per_game:
            excluded_players.append("{0} — below minutes threshold".format(player.full_name))
            continue

        deltas = {
            "pts": _delta(recent, baseline, "pts"),
            "reb": _delta(recent, baseline, "reb"),
            "ast": _delta(recent, baseline, "ast"),
            "stl": _delta(recent, baseline, "stl"),
            "blk": _delta(recent, baseline, "blk"),
            "ts_pct": _delta(recent, baseline, "ts_pct"),
            "usg_pct": _delta(recent, baseline, "usg_pct"),
            "tov_pct": _delta(recent, baseline, "tov_pct"),
            "plus_minus": _delta(recent, baseline, "plus_minus"),
        }

        raw_score = 0.0
        weight_total = 0.0
        for key, weight in TRAJECTORY_WEIGHTS.items():
            delta_value = deltas.get(key)
            if delta_value is None:
                continue
            raw_score += delta_value * weight
            weight_total += abs(weight)
        if weight_total <= 0:
            excluded_players.append("{0} — missing trajectory inputs".format(player.full_name))
            continue

        raw_score = raw_score / weight_total
        raw_scores[player_id] = raw_score

        context_flags: List[str] = []
        team_abbr = recent_rows[0].team_abbreviation or ""
        earliest_recent_game_id = recent_rows[-1].game_id
        latest_baseline_game_id = baseline_rows[0].game_id if baseline_rows else None
        if earliest_recent_game_id and latest_baseline_game_id and team_abbr:
            missed_games = 0
            for team_row in team_games_lookup.get(team_abbr, []):
                if latest_baseline_game_id < team_row.game_id < earliest_recent_game_id:
                    missed_games += 1
            if missed_games >= 3:
                context_flags.append("Injury return")

        if deltas.get("usg_pct") is not None and deltas["usg_pct"] > 4.0:
            context_flags.append("Role change")

        opponent_ratings = []
        for row in recent_rows:
            if not team_abbr:
                continue
            opponent = _opponent_from_matchup(row.matchup, team_abbr)
            if opponent and opponent in team_def_ratings:
                opponent_ratings.append(team_def_ratings[opponent])
        if opponent_ratings:
            opponent_average = sum(opponent_ratings) / len(opponent_ratings)
            elite_cutoff = max((team_def_ratings[team] for team in top_five_defenses), default=None)
            weak_cutoff = min((team_def_ratings[team] for team in bottom_five_defenses), default=None)
            if elite_cutoff is not None and opponent_average <= elite_cutoff:
                context_flags.append("Schedule flag: elite defenses")
            elif weak_cutoff is not None and opponent_average >= weak_cutoff:
                context_flags.append("Schedule flag: soft defenses")

        candidate_rows.append(
            {
                "player_name": player.full_name,
                "team": recent_rows[0].team_abbreviation or "",
                "player_id": player_id,
                "raw_score": raw_score,
                "deltas": deltas,
                "context_flags": context_flags,
            }
        )

    zscores = _zscore_map(raw_scores)
    breakout_candidates: List[TrajectoryPlayerRow] = []
    decline_candidates: List[TrajectoryPlayerRow] = []

    for candidate in candidate_rows:
        zscore = round(zscores.get(candidate["player_id"], 0.0), 2)
        deltas = {
            key: value
            for key, value in candidate["deltas"].items()
            if value is not None
        }
        top_drivers = sorted(deltas.items(), key=lambda item: abs(item[1]), reverse=True)[:2]
        label = _trajectory_label(zscore)
        row = TrajectoryPlayerRow(
            rank=0,
            player_name=candidate["player_name"],
            team=candidate["team"],
            trajectory_label=label,
            trajectory_score=zscore,
            key_stat_deltas={key: round(value, 2) for key, value in top_drivers},
            narrative=_narrative(candidate["player_name"], label, top_drivers),
            context_flags=candidate["context_flags"],
        )
        if zscore > 0:
            breakout_candidates.append(row)
        elif zscore < 0:
            decline_candidates.append(row)

    breakout_candidates.sort(key=lambda row: row.trajectory_score, reverse=True)
    decline_candidates.sort(key=lambda row: row.trajectory_score)

    breakout_leaders = [
        row.model_copy(update={"rank": index})
        for index, row in enumerate(breakout_candidates[:10], start=1)
    ]
    decline_watch = [
        row.model_copy(update={"rank": index})
        for index, row in enumerate(decline_candidates[:10], start=1)
    ]

    return TrajectoryResponse(
        window="Last {0} games".format(last_n_games),
        breakout_leaders=breakout_leaders,
        decline_watch=decline_watch,
        excluded_players=excluded_players,
        warnings=warnings,
    )
