from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Set

from sqlalchemy.orm import Session

from db.models import LineupStats, Player, PlayerGameLog, Team
from models.team import BenchAnalyticsResponse, BenchUnitRow


def _parse_lineup_ids(lineup_key: str) -> List[int]:
    if not lineup_key:
        return []
    ids: List[int] = []
    for tok in lineup_key.split("-"):
        tok = tok.strip()
        if not tok:
            continue
        try:
            ids.append(int(tok))
        except ValueError:
            continue
    return ids


def _identify_starters(
    db: Session, team_id: int, season: str, threshold: float = 0.5
) -> Set[int]:
    """A player is a starter if games_started / games_played >= threshold."""
    rows = (
        db.query(PlayerGameLog.player_id, PlayerGameLog.games_started)
        .filter(PlayerGameLog.season == season, PlayerGameLog.team_id == team_id)
        .all()
    )
    started: Dict[int, int] = defaultdict(int)
    played: Dict[int, int] = defaultdict(int)
    for player_id, gs in rows:
        played[player_id] += 1
        started[player_id] += int(gs or 0)
    return {
        pid for pid, gp in played.items() if gp > 0 and started[pid] / gp >= threshold
    }


def build_bench_analytics(
    db: Session,
    team_abbr: str,
    season: str,
    min_possessions: int = 20,
) -> BenchAnalyticsResponse:
    """Build bench vs starter analytics."""
    try:
        team = db.query(Team).filter(Team.abbreviation == team_abbr).first()
        if not team:
            return BenchAnalyticsResponse(
                team_abbr=team_abbr,
                season=season,
                best_bench_lineups=[],
                worst_bench_lineups=[],
                data_status="unavailable",
            )

        starters = _identify_starters(db, team.id, season)

        lineups = (
            db.query(LineupStats)
            .filter(
                LineupStats.season == season,
                LineupStats.team_id == team.id,
                LineupStats.possessions >= min_possessions,
            )
            .all()
        )

        if not lineups:
            return BenchAnalyticsResponse(
                team_abbr=team_abbr,
                season=season,
                best_bench_lineups=[],
                worst_bench_lineups=[],
                data_status="unavailable",
            )

        lineup_players: Dict[str, List[int]] = {
            lu.lineup_key: _parse_lineup_ids(lu.lineup_key) for lu in lineups
        }
        all_player_ids = {pid for ids in lineup_players.values() for pid in ids}
        name_map: Dict[int, str] = {}
        if all_player_ids:
            for player in (
                db.query(Player).filter(Player.person_id.in_(all_player_ids)).all()
            ):
                name_map[player.person_id] = player.full_name

        starter_heavy: List[BenchUnitRow] = []
        bench_heavy: List[BenchUnitRow] = []

        for lineup in lineups:
            player_ids = lineup_players[lineup.lineup_key]
            starter_count = sum(1 for pid in player_ids if pid in starters)
            player_names = [name_map.get(pid, str(pid)) for pid in player_ids]

            unit_row = BenchUnitRow(
                lineup_key=lineup.lineup_key,
                player_names=player_names,
                starter_count=starter_count,
                net_rating=lineup.net_rating,
                minutes=lineup.minutes,
                possessions=lineup.possessions,
            )

            if starter_count >= 3:
                starter_heavy.append(unit_row)
            else:
                bench_heavy.append(unit_row)

        def _avg_nr(units: List[BenchUnitRow]):
            nrs = [u.net_rating for u in units if u.net_rating is not None]
            return round(sum(nrs) / len(nrs), 1) if nrs else None

        starter_net_rating = _avg_nr(starter_heavy)
        bench_net_rating = _avg_nr(bench_heavy)

        bench_anchor_name = None
        bench_anchor_id = None
        positive_bench = [
            u for u in bench_heavy if u.net_rating is not None and u.net_rating > 0
        ]
        if positive_bench:
            best_bench = max(positive_bench, key=lambda u: u.possessions or 0)
            anchor_ids = lineup_players.get(best_bench.lineup_key, [])
            anchor_ids = [pid for pid in anchor_ids if pid not in starters]
            if anchor_ids:
                bench_anchor_id = anchor_ids[0]
                bench_anchor_name = name_map.get(bench_anchor_id)

        net_rating_gap = None
        if starter_net_rating is not None and bench_net_rating is not None:
            net_rating_gap = round(starter_net_rating - bench_net_rating, 1)

        bench_heavy.sort(key=lambda u: u.net_rating or 0, reverse=True)
        best_bench_lineups = bench_heavy[:3]
        worst_bench_lineups = list(reversed(bench_heavy[-3:])) if len(bench_heavy) > 3 else []

        return BenchAnalyticsResponse(
            team_abbr=team_abbr,
            season=season,
            starter_net_rating=starter_net_rating,
            bench_net_rating=bench_net_rating,
            net_rating_gap=net_rating_gap,
            bench_anchor_name=bench_anchor_name,
            bench_anchor_id=bench_anchor_id,
            best_bench_lineups=best_bench_lineups,
            worst_bench_lineups=worst_bench_lineups,
            data_status="ready",
        )

    except Exception:
        return BenchAnalyticsResponse(
            team_abbr=team_abbr,
            season=season,
            best_bench_lineups=[],
            worst_bench_lineups=[],
            data_status="error",
        )
