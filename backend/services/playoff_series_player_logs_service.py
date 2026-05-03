"""Sprint 85 — per-series player game-log assembler.

The bracket already exposes series-level intelligence
(``/api/playoffs/series/{id}/intelligence``) and a per-series simulator,
but coaches/fans drilling into a single matchup also want a focused
"matchup so far" tracker: every player's per-game stat line, click-through
to the full game-detail page.

This service assembles that response from rows already living in
``PlayerGameLog`` — playoff games are tagged ``season_type="Playoffs"`` by
the daily sync, and the playoffs router resolves the series → games →
participating players in the same way ``_games_for_series`` does for the
bracket detail card.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import GameLog, Player, PlayerGameLog, PlayoffSeries, Team
from models.playoffs import (
    PlayoffSeriesPlayerLogsResponse,
    SeriesPlayerGameLine,
    SeriesPlayerLogs,
)


def _empty_line(game_id: str, series_game_num: int) -> SeriesPlayerGameLine:
    return SeriesPlayerGameLine(
        game_id=game_id,
        series_game_num=series_game_num,
    )


def _line_from_game_log(log: PlayerGameLog, series_game_num: int) -> SeriesPlayerGameLine:
    return SeriesPlayerGameLine(
        game_id=log.game_id,
        series_game_num=series_game_num,
        min=float(log.min or 0.0),
        pts=int(log.pts or 0),
        reb=int(log.reb or 0),
        ast=int(log.ast or 0),
        stl=int(log.stl or 0),
        blk=int(log.blk or 0),
        tov=int(log.tov or 0),
        fgm=int(log.fgm or 0),
        fga=int(log.fga or 0),
        fg3m=int(log.fg3m or 0),
        fg3a=int(log.fg3a or 0),
        ftm=int(log.ftm or 0),
        fta=int(log.fta or 0),
        plus_minus=int(log.plus_minus or 0),
    )


def _sum_lines(lines: List[SeriesPlayerGameLine]) -> SeriesPlayerGameLine:
    """Sum a player's per-game lines into a single totals row.

    ``game_id`` is set to a stable sentinel (``"TOTALS"``) and
    ``series_game_num`` is set to ``0`` so the frontend can detect and
    style the totals row distinctly without needing a separate type.
    """
    totals = _empty_line(game_id="TOTALS", series_game_num=0)
    for ln in lines:
        totals.min += ln.min
        totals.pts += ln.pts
        totals.reb += ln.reb
        totals.ast += ln.ast
        totals.stl += ln.stl
        totals.blk += ln.blk
        totals.tov += ln.tov
        totals.fgm += ln.fgm
        totals.fga += ln.fga
        totals.fg3m += ln.fg3m
        totals.fg3a += ln.fg3a
        totals.ftm += ln.ftm
        totals.fta += ln.fta
        totals.plus_minus += ln.plus_minus
    return totals


def build_series_player_logs(
    db: Session, series_id: str
) -> Optional[PlayoffSeriesPlayerLogsResponse]:
    """Return per-team player game-by-game logs for a single playoff series.

    Returns ``None`` when the series_id does not resolve to a row in
    ``playoff_series`` so the route handler can surface a clean 404.
    """
    series = (
        db.query(PlayoffSeries)
        .filter(PlayoffSeries.series_id == series_id)
        .first()
    )
    if series is None:
        return None

    games: List[GameLog] = (
        db.query(GameLog)
        .filter(GameLog.series_id == series_id)
        .order_by(
            GameLog.series_game_num.asc(),
            GameLog.game_date.asc(),
            GameLog.game_id.asc(),
        )
        .all()
    )

    # game_id → series_game_num lookup (fallback to enumeration index when
    # the column is null on early-season ingests).
    game_num_by_id: Dict[str, int] = {}
    for idx, g in enumerate(games, start=1):
        game_num_by_id[g.game_id] = int(g.series_game_num) if g.series_game_num is not None else idx

    game_ids = list(game_num_by_id.keys())

    if not game_ids:
        return PlayoffSeriesPlayerLogsResponse(series_id=series_id, top_seed=[], bottom_seed=[])

    logs: List[PlayerGameLog] = (
        db.query(PlayerGameLog)
        .filter(PlayerGameLog.game_id.in_(game_ids))
        .filter(PlayerGameLog.season_type == "Playoffs")
        .all()
    )

    # Group raw logs by player_id.
    logs_by_player: Dict[int, List[PlayerGameLog]] = {}
    for log in logs:
        logs_by_player.setdefault(log.player_id, []).append(log)

    # Resolve player + team metadata in one pass to avoid N+1 lookups.
    player_ids = list(logs_by_player.keys())
    players: Dict[int, Player] = {}
    if player_ids:
        for p in db.query(Player).filter(Player.id.in_(player_ids)).all():
            players[p.id] = p

    # Build the per-team team metadata lookup. We only care about the two
    # teams in the series — any stray cross-team logs (which shouldn't
    # exist but we defend against) get dropped.
    team_ids: List[int] = []
    if series.top_seed_team_id is not None:
        team_ids.append(series.top_seed_team_id)
    if series.bottom_seed_team_id is not None:
        team_ids.append(series.bottom_seed_team_id)
    teams: Dict[int, Team] = {}
    if team_ids:
        for t in db.query(Team).filter(Team.id.in_(team_ids)).all():
            teams[t.id] = t

    top_team_id = series.top_seed_team_id
    bot_team_id = series.bottom_seed_team_id

    def _team_assignment(player_id: int) -> Optional[int]:
        """Resolve which side of the series a given player belongs to.

        Strategy:
        1. Use ``Player.team_id`` if it matches one of the series teams
           (typical case — the player is on his current roster).
        2. Otherwise infer from the games: in each game one of the two
           teams played both home and away, and ``PlayerGameLog`` doesn't
           store team_id directly but ``GameLog`` records the matchup.
           The player's logs all belong to the same team across the
           series, so we attribute via the first game's team line: if
           the player's logged minutes correlate with the home team and
           the home team is one of the series teams, that's their side.

        We don't have a per-log team_id column, so we fall back to
        ``Player.team_id`` first (correct in-season) and then to a
        defensive None which routes the player out of the response.
        """
        player = players.get(player_id)
        if player is None:
            return None
        pt = player.team_id
        if pt == top_team_id or pt == bot_team_id:
            return pt
        # Player traded mid-series or roster moved — fall back to None
        # so we don't accidentally bucket them on the wrong team.
        return None

    top_seed_logs: List[SeriesPlayerLogs] = []
    bottom_seed_logs: List[SeriesPlayerLogs] = []

    # Stable iteration order (player_id ascending) → deterministic test
    # output before the minutes-based resort.
    for pid in sorted(logs_by_player.keys()):
        player = players.get(pid)
        if player is None:
            continue
        team_id = _team_assignment(pid)
        if team_id is None:
            continue

        team = teams.get(team_id)
        team_abbr = team.abbreviation if team is not None else ""

        # Per-game lines, sorted by series_game_num.
        lines: List[Tuple[int, SeriesPlayerGameLine]] = []
        for log in logs_by_player[pid]:
            sgn = game_num_by_id.get(log.game_id, 0)
            lines.append((sgn, _line_from_game_log(log, sgn)))
        lines.sort(key=lambda pair: (pair[0], pair[1].game_id))
        ordered_lines = [pair[1] for pair in lines]

        record = SeriesPlayerLogs(
            player_id=pid,
            player_name=player.full_name,
            team_id=team_id,
            team_abbreviation=team_abbr,
            headshot_url=player.headshot_url,
            games=ordered_lines,
            series_totals=_sum_lines(ordered_lines),
        )
        if team_id == top_team_id:
            top_seed_logs.append(record)
        elif team_id == bot_team_id:
            bottom_seed_logs.append(record)

    # Within each team, sort by total minutes played in the series
    # (descending) so the headline rotation appears first.
    top_seed_logs.sort(key=lambda r: r.series_totals.min, reverse=True)
    bottom_seed_logs.sort(key=lambda r: r.series_totals.min, reverse=True)

    return PlayoffSeriesPlayerLogsResponse(
        series_id=series_id,
        top_seed=top_seed_logs,
        bottom_seed=bottom_seed_logs,
    )
