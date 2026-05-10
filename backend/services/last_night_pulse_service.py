"""Sprint 96 — Last Night Pulse service.

Three tiles for the broadsheet hero, all driven directly from raw game data
so freshness tracks the post-game sync within minutes (not the multi-hour
SeasonStat aggregate path the StoryRail relied on).

- Last Night's Hero: top playoff PlayerGameLog from games in the last ~36h,
  ranked by Hollinger Game Score.
- Tonight's Headliner: tonight's playoff matchup with the lowest combined
  seed sum (the marquee game on the slate).
- Series Momentum: the playoff series whose state changed most recently
  (W/L flip, advancement) within the last ~36h.
"""
from __future__ import annotations

from datetime import date as _date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pytz
from sqlalchemy.orm import Session

from db.models import GameLog, Player, PlayerGameLog, PlayoffSeries, Team
from models.playoffs import (
    LastNightHeroTile,
    LastNightPulseResponse,
    SeriesMomentumTile,
    TonightHeadlinerTile,
)


_PACIFIC_TZ = pytz.timezone("US/Pacific")
_LOOKBACK_HOURS = 36


def _today_pacific() -> _date:
    return datetime.now(tz=_PACIFIC_TZ).date()


def _now_utc() -> datetime:
    return datetime.utcnow()


def _game_score(log: PlayerGameLog) -> float:
    """Hollinger Game Score for a single playoff game.

    GS = PTS + 0.4·FGM − 0.7·FGA − 0.4·(FTA − FTM)
       + 0.7·OREB + 0.3·DREB + STL + 0.7·AST + 0.7·BLK
       − 0.4·PF − TOV
    """
    def f(x):
        return float(x) if x is not None else 0.0

    pts = f(log.pts)
    fgm = f(log.fgm)
    fga = f(log.fga)
    fta = f(log.fta)
    ftm = f(log.ftm)
    oreb = f(log.oreb)
    dreb = f(log.dreb)
    if oreb == 0 and dreb == 0 and log.reb is not None:
        # Some box scores only populate total reb. Approximate by treating
        # the lot as defensive — common for older fixtures and for some
        # NBA-API fallbacks that omit OREB/DREB splits.
        dreb = f(log.reb)
    return (
        pts
        + 0.4 * fgm
        - 0.7 * fga
        - 0.4 * (fta - ftm)
        + 0.7 * oreb
        + 0.3 * dreb
        + f(log.stl)
        + 0.7 * f(log.ast)
        + 0.7 * f(log.blk)
        - 0.4 * f(log.pf)
        - f(log.tov)
    )


def _format_hero_line(log: PlayerGameLog) -> str:
    parts: List[str] = []
    if log.pts is not None:
        parts.append("{0} PTS".format(int(log.pts)))
    if log.reb is not None and int(log.reb) > 0:
        parts.append("{0} REB".format(int(log.reb)))
    if log.ast is not None and int(log.ast) > 0:
        parts.append("{0} AST".format(int(log.ast)))
    return " · ".join(parts) if parts else "{0} PTS".format(int(log.pts or 0))


def _team_abbr_from_matchup(matchup: Optional[str]) -> str:
    """Extract the player's team from PlayerGameLog.matchup ("BOS @ LAL")."""
    if not matchup:
        return ""
    head = matchup.split(" ", 1)[0].strip()
    return head


def _build_last_night_hero(
    db: Session,
    season: str,
    today: _date,
) -> Optional[LastNightHeroTile]:
    cutoff = today - timedelta(days=1)
    rows = (
        db.query(PlayerGameLog)
        .filter(
            PlayerGameLog.season == season,
            PlayerGameLog.season_type == "Playoffs",
            PlayerGameLog.game_date >= cutoff,
            PlayerGameLog.game_date <= today,
            PlayerGameLog.pts.isnot(None),
        )
        .all()
    )
    if not rows:
        return None

    scored = [(log, _game_score(log)) for log in rows]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    log, score = scored[0]

    player = db.query(Player).filter(Player.id == log.player_id).first()
    name = (
        player.full_name
        if player is not None and player.full_name
        else "Player {0}".format(log.player_id)
    )

    return LastNightHeroTile(
        player_id=int(log.player_id),
        player_name=name,
        team_abbreviation=_team_abbr_from_matchup(log.matchup),
        game_id=log.game_id,
        game_date=log.game_date,
        matchup=log.matchup or None,
        pts=int(log.pts or 0),
        reb=int(log.reb or 0),
        ast=int(log.ast or 0),
        line=_format_hero_line(log),
        game_score=round(score, 1),
        href="/games/{0}".format(log.game_id),
    )


def _build_tonight_headliner(
    db: Session,
    season: str,
    today: _date,
) -> Optional[TonightHeadlinerTile]:
    games = (
        db.query(GameLog)
        .filter(
            GameLog.season == season,
            GameLog.season_type == "Playoffs",
            GameLog.game_date == today,
            GameLog.home_score.is_(None),  # not yet final
        )
        .all()
    )
    if not games:
        return None

    series_ids = [g.series_id for g in games if g.series_id]
    series_lookup: Dict[str, PlayoffSeries] = {}
    if series_ids:
        for s in (
            db.query(PlayoffSeries)
            .filter(PlayoffSeries.series_id.in_(series_ids))
            .all()
        ):
            series_lookup[s.series_id] = s

    def rank_key(game: GameLog) -> Tuple[int, str]:
        s = series_lookup.get(game.series_id) if game.series_id else None
        if s is None or s.top_seed is None or s.bottom_seed is None:
            return (99, game.game_id)
        return (int(s.top_seed) + int(s.bottom_seed), game.game_id)

    games_sorted = sorted(games, key=rank_key)
    pick = games_sorted[0]
    series = series_lookup.get(pick.series_id) if pick.series_id else None

    team_ids: List[int] = []
    if pick.home_team_id is not None:
        team_ids.append(pick.home_team_id)
    if pick.away_team_id is not None:
        team_ids.append(pick.away_team_id)
    if series is not None:
        if series.top_seed_team_id is not None:
            team_ids.append(series.top_seed_team_id)
        if series.bottom_seed_team_id is not None:
            team_ids.append(series.bottom_seed_team_id)

    teams_by_id: Dict[int, Team] = {}
    if team_ids:
        for t in db.query(Team).filter(Team.id.in_(set(team_ids))).all():
            teams_by_id[t.id] = t

    home_abbr = (
        teams_by_id[pick.home_team_id].abbreviation
        if pick.home_team_id is not None and pick.home_team_id in teams_by_id
        else None
    )
    away_abbr = (
        teams_by_id[pick.away_team_id].abbreviation
        if pick.away_team_id is not None and pick.away_team_id in teams_by_id
        else None
    )
    matchup = "{0} at {1}".format(away_abbr or "TBD", home_abbr or "TBD")

    seeds_label: Optional[str] = None
    series_state: Optional[str] = None
    round_no: Optional[int] = None
    href = "/bracket"
    series_id: Optional[str] = None

    if series is not None:
        round_no = series.round
        series_id = series.series_id
        if series.top_seed is not None and series.bottom_seed is not None:
            lo = min(int(series.top_seed), int(series.bottom_seed))
            hi = max(int(series.top_seed), int(series.bottom_seed))
            seeds_label = "#{0} vs #{1}".format(lo, hi)

        tw = int(series.top_wins or 0)
        bw = int(series.bottom_wins or 0)
        top_team = (
            teams_by_id.get(series.top_seed_team_id)
            if series.top_seed_team_id is not None
            else None
        )
        bot_team = (
            teams_by_id.get(series.bottom_seed_team_id)
            if series.bottom_seed_team_id is not None
            else None
        )
        if tw == 0 and bw == 0:
            series_state = "Series tied 0-0"
        elif tw == bw:
            series_state = "Series tied {0}-{1}".format(tw, bw)
        elif tw > bw:
            series_state = "{0} leads {1}-{2}".format(
                top_team.abbreviation if top_team else "Top seed", tw, bw
            )
        else:
            series_state = "{0} leads {1}-{2}".format(
                bot_team.abbreviation if bot_team else "Bottom seed", bw, tw
            )
        href = "/pre-read?series_id={0}".format(series.series_id)

    return TonightHeadlinerTile(
        series_id=series_id,
        game_id=pick.game_id,
        home_team_abbr=home_abbr,
        away_team_abbr=away_abbr,
        matchup=matchup,
        round=round_no,
        seeds_label=seeds_label,
        series_state=series_state,
        tipoff_utc=None,
        href=href,
    )


def _build_series_momentum(
    db: Session,
    season: str,
    now: datetime,
) -> Optional[SeriesMomentumTile]:
    cutoff = now - timedelta(hours=_LOOKBACK_HOURS)
    series = (
        db.query(PlayoffSeries)
        .filter(
            PlayoffSeries.season == season,
            PlayoffSeries.updated_at >= cutoff,
        )
        .order_by(PlayoffSeries.updated_at.desc().nullslast())
        .first()
    )
    if series is None:
        return None

    team_ids: List[int] = []
    if series.top_seed_team_id is not None:
        team_ids.append(series.top_seed_team_id)
    if series.bottom_seed_team_id is not None:
        team_ids.append(series.bottom_seed_team_id)
    teams_by_id: Dict[int, Team] = {}
    if team_ids:
        for t in db.query(Team).filter(Team.id.in_(team_ids)).all():
            teams_by_id[t.id] = t

    top_abbr = (
        teams_by_id[series.top_seed_team_id].abbreviation
        if series.top_seed_team_id is not None and series.top_seed_team_id in teams_by_id
        else None
    )
    bot_abbr = (
        teams_by_id[series.bottom_seed_team_id].abbreviation
        if series.bottom_seed_team_id is not None and series.bottom_seed_team_id in teams_by_id
        else None
    )
    matchup = "{0} vs {1}".format(top_abbr or "TBD", bot_abbr or "TBD")

    tw = int(series.top_wins or 0)
    bw = int(series.bottom_wins or 0)
    if series.status == "closed" and series.winner_team_id is not None:
        winner = teams_by_id.get(series.winner_team_id)
        winner_abbr = winner.abbreviation if winner is not None else "Winner"
        big = max(tw, bw)
        small = min(tw, bw)
        summary = "{0} take the series {1}-{2}.".format(winner_abbr, big, small)
    elif tw == 0 and bw == 0:
        summary = "Series tips off."
    elif tw > bw:
        summary = "{0} leads {1}-{2}.".format(top_abbr or "Top seed", tw, bw)
    elif bw > tw:
        summary = "{0} leads {1}-{2}.".format(bot_abbr or "Bottom seed", bw, tw)
    else:
        summary = "Series tied {0}-{1}.".format(tw, bw)

    return SeriesMomentumTile(
        series_id=series.series_id,
        matchup=matchup,
        summary=summary,
        round=series.round,
        href="/pre-read?series_id={0}".format(series.series_id),
    )


def compute_last_night_pulse(
    db: Session,
    season: str,
    today: Optional[_date] = None,
    now: Optional[datetime] = None,
) -> LastNightPulseResponse:
    """Compute the three Last Night Pulse tiles for the given season.

    ``today`` and ``now`` are exposed for testability — in production both
    default to the current Pacific date / UTC instant.
    """
    if today is None:
        today = _today_pacific()
    if now is None:
        now = _now_utc()

    return LastNightPulseResponse(
        season=season,
        last_night_hero=_build_last_night_hero(db, season, today),
        tonight_headliner=_build_tonight_headliner(db, season, today),
        series_momentum=_build_series_momentum(db, season, now),
        data_as_of=now,
        computed_at=now,
    )


__all__ = ["compute_last_night_pulse"]
