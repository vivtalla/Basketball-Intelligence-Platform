"""Playoff API surface (Sprint 73).

Routes:

- ``GET /api/playoffs/bracket?season=2025-26`` — full bracket grouped by
  conference plus the finals, if it exists.
- ``GET /api/playoffs/series/{series_id}`` — a single series with all games
  in ``series_game_num`` order.
- ``GET /api/playoffs/today?date=YYYY-MM-DD`` — playoff games on a given date
  (defaults to "today" in US/Pacific).
- ``GET /api/playoffs/series-simulation/{series_id}`` — Monte-Carlo projection.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional

import pytz
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import GameLog, Team
from models.playoffs import (
    PlayoffBracketResponse,
    PlayoffSeriesIntelligenceResponse,
    PlayoffSeriesGame,
    PlayoffSeriesGameWithMatchup,
    PlayoffSeriesResponse,
    PlayoffTodayResponse,
    SeriesSimulationResponse,
)
from services.playoff_series_intelligence_service import build_playoff_series_intelligence
from services.playoff_simulator_service import simulate_series

router = APIRouter()


# ---------------------------------------------------------------------------
# Static EAST/WEST fallback used when `Team.conference` is empty.
# ---------------------------------------------------------------------------

_EAST_ABBRS = {
    "ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DET", "IND", "MIA",
    "MIL", "NYK", "ORL", "PHI", "TOR", "WAS",
}
_WEST_ABBRS = {
    "DAL", "DEN", "GSW", "HOU", "LAC", "LAL", "MEM", "MIN", "NOP",
    "OKC", "PHX", "POR", "SAC", "SAS", "UTA",
}


# US Pacific via pytz (DST-aware). Stdlib `zoneinfo` isn't available on Python
# 3.8 without a third-party install, but pytz is already in the dep tree.
_PACIFIC_TZ = pytz.timezone("US/Pacific")


def _today_pacific() -> date:
    return datetime.now(tz=_PACIFIC_TZ).date()


def _conference_for_team(team: Optional[Team], abbr_fallback: Optional[str]) -> Optional[str]:
    if team is not None:
        conf = (team.conference or "").strip()
        if conf:
            normalized = conf.upper()
            if normalized.startswith("E"):
                return "East"
            if normalized.startswith("W"):
                return "West"
    abbr = (abbr_fallback or "").upper()
    if abbr in _EAST_ABBRS:
        return "East"
    if abbr in _WEST_ABBRS:
        return "West"
    return None


def _team_lookup(db: Session, team_ids: List[int]) -> Dict[int, Team]:
    if not team_ids:
        return {}
    rows = db.query(Team).filter(Team.id.in_(team_ids)).all()
    return {row.id: row for row in rows}


def _winner_team_id(game: GameLog) -> Optional[int]:
    if game.home_score is None or game.away_score is None:
        return None
    if game.home_score > game.away_score:
        return game.home_team_id
    if game.away_score > game.home_score:
        return game.away_team_id
    return None


def _games_for_series(
    db: Session, series_id: str, team_lookup: Optional[Dict[int, Team]] = None
) -> List[PlayoffSeriesGame]:
    rows = (
        db.query(GameLog)
        .filter(GameLog.series_id == series_id)
        .order_by(
            GameLog.series_game_num.asc(),
            GameLog.game_date.asc(),
            GameLog.game_id.asc(),
        )
        .all()
    )
    needed_team_ids: List[int] = []
    for row in rows:
        if row.home_team_id is not None:
            needed_team_ids.append(row.home_team_id)
        if row.away_team_id is not None:
            needed_team_ids.append(row.away_team_id)
    if team_lookup is None:
        team_lookup = _team_lookup(db, list(set(needed_team_ids)))

    games: List[PlayoffSeriesGame] = []
    for row in rows:
        home_team = team_lookup.get(row.home_team_id) if row.home_team_id is not None else None
        away_team = team_lookup.get(row.away_team_id) if row.away_team_id is not None else None
        games.append(
            PlayoffSeriesGame(
                game_id=row.game_id,
                game_date=row.game_date,
                home_team_id=row.home_team_id,
                home_team_abbr=home_team.abbreviation if home_team is not None else None,
                away_team_id=row.away_team_id,
                away_team_abbr=away_team.abbreviation if away_team is not None else None,
                home_pts=row.home_score,
                away_pts=row.away_score,
                winner_team_id=_winner_team_id(row),
                series_game_num=row.series_game_num,
            )
        )
    return games


def _series_to_response(
    series, team_lookup: Dict[int, Team], games: List[PlayoffSeriesGame]
) -> PlayoffSeriesResponse:
    top = team_lookup.get(series.top_seed_team_id)
    bottom = team_lookup.get(series.bottom_seed_team_id)
    return PlayoffSeriesResponse(
        season=series.season,
        round=series.round,
        series_id=series.series_id,
        top_seed_team_id=series.top_seed_team_id,
        bottom_seed_team_id=series.bottom_seed_team_id,
        top_seed_team_abbr=top.abbreviation if top is not None else None,
        bottom_seed_team_abbr=bottom.abbreviation if bottom is not None else None,
        top_seed=series.top_seed,
        bottom_seed=series.bottom_seed,
        top_wins=series.top_wins or 0,
        bottom_wins=series.bottom_wins or 0,
        status=series.status,
        winner_team_id=series.winner_team_id,
        games=games,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/bracket", response_model=PlayoffBracketResponse)
def get_bracket(
    season: str = Query(...),
    db: Session = Depends(get_db),
) -> PlayoffBracketResponse:
    """Return the full playoff bracket for ``season`` grouped by conference."""
    from db.models import PlayoffSeries  # local import — see season_phase_service

    series_rows = (
        db.query(PlayoffSeries)
        .filter(PlayoffSeries.season == season)
        .order_by(PlayoffSeries.round.asc(), PlayoffSeries.top_seed.asc())
        .all()
    )

    team_ids: List[int] = []
    for s in series_rows:
        if s.top_seed_team_id is not None:
            team_ids.append(s.top_seed_team_id)
        if s.bottom_seed_team_id is not None:
            team_ids.append(s.bottom_seed_team_id)
    team_lookup = _team_lookup(db, list(set(team_ids)))

    east: List[PlayoffSeriesResponse] = []
    west: List[PlayoffSeriesResponse] = []
    finals: Optional[PlayoffSeriesResponse] = None

    for s in series_rows:
        games = _games_for_series(db, s.series_id, team_lookup)
        response = _series_to_response(s, team_lookup, games)

        if s.round == 4:
            finals = response
            continue

        # Determine conference from either top-seed or bottom-seed team.
        top_team = team_lookup.get(s.top_seed_team_id)
        bottom_team = team_lookup.get(s.bottom_seed_team_id)
        top_abbr = top_team.abbreviation if top_team is not None else None
        bottom_abbr = bottom_team.abbreviation if bottom_team is not None else None
        conference = _conference_for_team(top_team, top_abbr) or _conference_for_team(
            bottom_team, bottom_abbr
        )
        if conference == "East":
            east.append(response)
        elif conference == "West":
            west.append(response)
        else:
            # Unknown conference (e.g. a play-in or test seed without a team
            # mapping) — drop into east as a neutral default.
            east.append(response)

    return PlayoffBracketResponse(season=season, east=east, west=west, finals=finals)


@router.get("/series/{series_id}", response_model=PlayoffSeriesResponse)
def get_series(
    series_id: str,
    db: Session = Depends(get_db),
) -> PlayoffSeriesResponse:
    """Return a single playoff series with games in series_game_num order."""
    from db.models import PlayoffSeries  # local import

    series = (
        db.query(PlayoffSeries)
        .filter(PlayoffSeries.series_id == series_id)
        .first()
    )
    if series is None:
        raise HTTPException(status_code=404, detail=f"Playoff series '{series_id}' not found")

    team_ids: List[int] = []
    if series.top_seed_team_id is not None:
        team_ids.append(series.top_seed_team_id)
    if series.bottom_seed_team_id is not None:
        team_ids.append(series.bottom_seed_team_id)
    team_lookup = _team_lookup(db, team_ids)

    games = _games_for_series(db, series_id, team_lookup)
    return _series_to_response(series, team_lookup, games)


@router.get("/series/{series_id}/intelligence", response_model=PlayoffSeriesIntelligenceResponse)
def get_series_intelligence(
    series_id: str,
    db: Session = Depends(get_db),
) -> PlayoffSeriesIntelligenceResponse:
    """Return deterministic coach/analyst intelligence for one playoff series."""
    response = build_playoff_series_intelligence(db, series_id)
    if response is None:
        raise HTTPException(status_code=404, detail=f"Playoff series '{series_id}' not found")
    return response


@router.get("/today", response_model=PlayoffTodayResponse)
def get_today(
    date_param: Optional[str] = Query(None, alias="date", description="YYYY-MM-DD; defaults to today (US/Pacific)."),
    db: Session = Depends(get_db),
) -> PlayoffTodayResponse:
    """Return all playoff games on a given date along with their series context."""
    from db.models import PlayoffSeries  # local import

    if date_param is None:
        target = _today_pacific()
    else:
        try:
            target = datetime.strptime(date_param, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="`date` must be formatted YYYY-MM-DD")

    rows = (
        db.query(GameLog)
        .filter(GameLog.season_type == "Playoffs")
        .filter(GameLog.game_date == target)
        .order_by(GameLog.game_id.asc())
        .all()
    )

    if not rows:
        return PlayoffTodayResponse(date=target, games=[])

    series_ids = list({row.series_id for row in rows if row.series_id})
    series_rows = []
    if series_ids:
        series_rows = (
            db.query(PlayoffSeries)
            .filter(PlayoffSeries.series_id.in_(series_ids))
            .all()
        )
    series_lookup = {s.series_id: s for s in series_rows}

    needed_team_ids: List[int] = []
    for row in rows:
        if row.home_team_id is not None:
            needed_team_ids.append(row.home_team_id)
        if row.away_team_id is not None:
            needed_team_ids.append(row.away_team_id)
    for s in series_rows:
        if s.top_seed_team_id is not None:
            needed_team_ids.append(s.top_seed_team_id)
        if s.bottom_seed_team_id is not None:
            needed_team_ids.append(s.bottom_seed_team_id)
    team_lookup = _team_lookup(db, list(set(needed_team_ids)))

    games: List[PlayoffSeriesGameWithMatchup] = []
    for row in rows:
        home_team = team_lookup.get(row.home_team_id) if row.home_team_id is not None else None
        away_team = team_lookup.get(row.away_team_id) if row.away_team_id is not None else None
        series = series_lookup.get(row.series_id) if row.series_id else None

        top_team = team_lookup.get(series.top_seed_team_id) if series is not None else None
        bottom_team = team_lookup.get(series.bottom_seed_team_id) if series is not None else None

        games.append(
            PlayoffSeriesGameWithMatchup(
                game_id=row.game_id,
                game_date=row.game_date,
                home_team_id=row.home_team_id,
                home_team_abbr=home_team.abbreviation if home_team is not None else None,
                away_team_id=row.away_team_id,
                away_team_abbr=away_team.abbreviation if away_team is not None else None,
                home_pts=row.home_score,
                away_pts=row.away_score,
                winner_team_id=_winner_team_id(row),
                series_game_num=row.series_game_num,
                series_id=row.series_id,
                season=series.season if series is not None else None,
                round=series.round if series is not None else None,
                top_seed_team_abbr=top_team.abbreviation if top_team is not None else None,
                bottom_seed_team_abbr=bottom_team.abbreviation if bottom_team is not None else None,
                top_wins=series.top_wins if series is not None else None,
                bottom_wins=series.bottom_wins if series is not None else None,
                status=series.status if series is not None else None,
            )
        )

    return PlayoffTodayResponse(date=target, games=games)


@router.get("/series-simulation/{series_id}", response_model=SeriesSimulationResponse)
def get_series_simulation(
    series_id: str,
    override_top_wins: Optional[int] = None,
    override_bottom_wins: Optional[int] = None,
    db: Session = Depends(get_db),
) -> SeriesSimulationResponse:
    """Return the Monte-Carlo projection for the requested series."""
    return simulate_series(
        db,
        series_id,
        override_top_wins=override_top_wins,
        override_bottom_wins=override_bottom_wins,
    )
