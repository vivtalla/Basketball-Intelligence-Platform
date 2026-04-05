from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import GameTeamStat, Team, WarehouseGame
from models.compare import TeamComparisonResponse, TeamComparisonRow, TeamComparisonSnapshot, TeamComparisonStory


def _estimate_possessions(fga: Optional[float], oreb: Optional[float], tov: Optional[float], fta: Optional[float]) -> Optional[float]:
    if fga is None or oreb is None or tov is None or fta is None:
        return None
    possessions = float(fga) - float(oreb) + float(tov) + (0.44 * float(fta))
    if possessions <= 0:
        return None
    return possessions


def _safe_round(value: Optional[float], digits: int = 2) -> Optional[float]:
    if value is None:
        return None
    return round(value, digits)


def _edge(team_a_value: Optional[float], team_b_value: Optional[float], higher_better: bool) -> str:
    if team_a_value is None or team_b_value is None:
        return "even"
    if abs(team_a_value - team_b_value) < 1e-9:
        return "even"
    if higher_better:
        return "team_a" if team_a_value > team_b_value else "team_b"
    return "team_a" if team_a_value < team_b_value else "team_b"


def _record_string(wins: int, losses: int) -> Optional[str]:
    if wins + losses == 0:
        return None
    return "{0}-{1}".format(wins, losses)


def _build_snapshot(db: Session, abbreviation: str, season: str) -> TeamComparisonSnapshot:
    team = db.query(Team).filter(Team.abbreviation == abbreviation.upper()).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team '{0}' not found.".format(abbreviation))

    rows = (
        db.query(GameTeamStat, WarehouseGame)
        .join(WarehouseGame, WarehouseGame.game_id == GameTeamStat.game_id)
        .filter(GameTeamStat.season == season, GameTeamStat.team_id == team.id)
        .order_by(WarehouseGame.game_date.desc().nullslast(), GameTeamStat.game_id.desc())
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No game-level team stats found for {0} in {1}.".format(abbreviation.upper(), season))

    totals: Dict[str, float] = {
        "pts": 0.0,
        "reb": 0.0,
        "tov": 0.0,
        "fgm": 0.0,
        "fga": 0.0,
        "fg3m": 0.0,
        "fta": 0.0,
    }
    game_count = 0.0
    points_allowed = 0.0
    possessions_total = 0.0
    recent_wins = 0
    recent_losses = 0

    for index, (row, game) in enumerate(rows):
        game_count += 1.0
        totals["pts"] += float(row.pts or 0.0)
        totals["reb"] += float(row.reb or 0.0)
        totals["tov"] += float(row.tov or 0.0)
        totals["fgm"] += float(row.fgm or 0.0)
        totals["fga"] += float(row.fga or 0.0)
        totals["fg3m"] += float(row.fg3m or 0.0)
        totals["fta"] += float(row.fta or 0.0)

        if row.won is True and index < 10:
            recent_wins += 1
        elif row.won is False and index < 10:
            recent_losses += 1

        opponent_score = None
        if game.home_team_id == team.id:
            opponent_score = game.away_score
        elif game.away_team_id == team.id:
            opponent_score = game.home_score
        if opponent_score is not None:
            points_allowed += float(opponent_score)

        possessions = _estimate_possessions(row.fga, row.oreb, row.tov, row.fta)
        if possessions is not None:
            possessions_total += possessions

    ts_pct = None
    ts_denominator = 2.0 * (totals["fga"] + (0.44 * totals["fta"]))
    if ts_denominator > 0:
        ts_pct = totals["pts"] / ts_denominator

    efg_pct = None
    if totals["fga"] > 0:
        efg_pct = (totals["fgm"] + (0.5 * totals["fg3m"])) / totals["fga"]

    pace = None
    if game_count > 0 and possessions_total > 0:
        pace = possessions_total / game_count

    net_rating = None
    if possessions_total > 0:
        net_rating = ((totals["pts"] - points_allowed) / possessions_total) * 100.0

    return TeamComparisonSnapshot(
        abbreviation=team.abbreviation,
        name=team.name,
        season=season,
        recent_record=_record_string(recent_wins, recent_losses),
        net_rating=_safe_round(net_rating, 1),
        ts_pct=_safe_round(ts_pct, 3),
        efg_pct=_safe_round(efg_pct, 3),
        tov_pg=_safe_round(totals["tov"] / game_count if game_count else None, 1),
        reb_pg=_safe_round(totals["reb"] / game_count if game_count else None, 1),
        pace=_safe_round(pace, 1),
    )


def _story(label: str, summary: str, edge: str) -> TeamComparisonStory:
    return TeamComparisonStory(label=label, summary=summary, edge=edge)  # type: ignore[arg-type]


def build_team_comparison_report(
    db: Session,
    team_a: str,
    team_b: str,
    season: str,
    source_context: Optional[Dict[str, str]] = None,
) -> TeamComparisonResponse:
    team_a_snapshot = _build_snapshot(db, team_a, season)
    team_b_snapshot = _build_snapshot(db, team_b, season)

    rows: List[TeamComparisonRow] = []

    def add_row(stat_id: str, label: str, team_a_value: Optional[float], team_b_value: Optional[float], higher_better: bool, format: str):
        rows.append(
            TeamComparisonRow(
                stat_id=stat_id,
                label=label,
                team_a_value=team_a_value,
                team_b_value=team_b_value,
                higher_better=higher_better,
                format=format,  # type: ignore[arg-type]
                edge=_edge(team_a_value, team_b_value, higher_better),  # type: ignore[arg-type]
            )
        )

    add_row("efg_pct", "Effective FG%", team_a_snapshot.efg_pct, team_b_snapshot.efg_pct, True, "percent")
    add_row("ts_pct", "True Shooting%", team_a_snapshot.ts_pct, team_b_snapshot.ts_pct, True, "percent")
    add_row("tov_pg", "Turnovers / Game", team_a_snapshot.tov_pg, team_b_snapshot.tov_pg, False, "number")
    add_row("reb_pg", "Rebounds / Game", team_a_snapshot.reb_pg, team_b_snapshot.reb_pg, True, "number")
    add_row("pace", "Estimated Pace", team_a_snapshot.pace, team_b_snapshot.pace, True, "number")
    add_row("net_rating", "Net Rating", team_a_snapshot.net_rating, team_b_snapshot.net_rating, True, "signed")

    stories: List[TeamComparisonStory] = []

    if team_a_snapshot.tov_pg is not None and team_b_snapshot.tov_pg is not None:
        edge = _edge(team_a_snapshot.tov_pg, team_b_snapshot.tov_pg, False)
        if edge != "even":
            leader = team_a_snapshot if edge == "team_a" else team_b_snapshot
            stories.append(_story("Wins turnover battle", "{0} protects possessions better, which raises the offensive floor.".format(leader.abbreviation), edge))
    if team_a_snapshot.ts_pct is not None and team_b_snapshot.ts_pct is not None:
        edge = _edge(team_a_snapshot.ts_pct, team_b_snapshot.ts_pct, True)
        if edge != "even":
            leader = team_a_snapshot if edge == "team_a" else team_b_snapshot
            stories.append(_story("More efficient shooting team", "{0} carries the cleaner true-shooting profile in this matchup frame.".format(leader.abbreviation), edge))
    if team_a_snapshot.reb_pg is not None and team_b_snapshot.reb_pg is not None:
        edge = _edge(team_a_snapshot.reb_pg, team_b_snapshot.reb_pg, True)
        if edge != "even":
            leader = team_a_snapshot if edge == "team_a" else team_b_snapshot
            stories.append(_story("Stronger glass profile", "{0} owns the better rebounding base, which should create more margin on missed shots.".format(leader.abbreviation), edge))
    if team_a_snapshot.pace is not None and team_b_snapshot.pace is not None:
        edge = _edge(team_a_snapshot.pace, team_b_snapshot.pace, True)
        if edge != "even":
            leader = team_a_snapshot if edge == "team_a" else team_b_snapshot
            stories.append(_story("Faster tempo team", "{0} is more likely to pull the game toward its preferred pace.".format(leader.abbreviation), edge))
    if team_a_snapshot.net_rating is not None and team_b_snapshot.net_rating is not None:
        edge = _edge(team_a_snapshot.net_rating, team_b_snapshot.net_rating, True)
        if edge != "even":
            leader = team_a_snapshot if edge == "team_a" else team_b_snapshot
            stories.append(_story("Cleaner overall profile", "{0} owns the better net-rating baseline across the season.".format(leader.abbreviation), edge))

    return TeamComparisonResponse(
        season=season,
        team_a=team_a_snapshot,
        team_b=team_b_snapshot,
        rows=rows,
        stories=stories[:5],
        source_context=source_context,
    )
