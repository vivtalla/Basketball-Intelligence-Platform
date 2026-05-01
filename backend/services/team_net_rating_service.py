from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from data.nba_client import LiveFetchBlockedError, get_team_game_log
from db.models import Team
from models.team import TeamNetRatingGame, TeamNetRatingSeriesResponse


def build_team_rolling_net_rating(
    db: Session,
    team_abbr: str,
    season: str,
    window: int = 10,
) -> TeamNetRatingSeriesResponse:
    """Build rolling net rating series from team game log."""
    try:
        team = db.query(Team).filter(Team.abbreviation == team_abbr).first()

        if not team:
            return TeamNetRatingSeriesResponse(
                team_abbr=team_abbr,
                season=season,
                window=window,
                games=[],
                data_status="unavailable",
            )

        try:
            rows = get_team_game_log(team.nba_team_id, season)
        except LiveFetchBlockedError:
            # Sprint 82d public-mode: no cached game log yet. Return empty
            # series with the same "unavailable" status the no-rows path
            # uses so the UI renders a degraded state rather than a 500.
            return TeamNetRatingSeriesResponse(
                team_abbr=team_abbr,
                season=season,
                window=window,
                games=[],
                data_status="unavailable",
            )

        if not rows:
            return TeamNetRatingSeriesResponse(
                team_abbr=team_abbr,
                season=season,
                window=window,
                games=[],
                data_status="unavailable",
            )

        games_list: List[TeamNetRatingGame] = []

        for row in rows:
            game_id = row.get("Game_ID")
            game_date = row.get("GAME_DATE")
            opponent_abbr = row.get("MATCHUP", "").split()[-1] if row.get("MATCHUP") else None
            pts = row.get("PTS")
            opp_pts = row.get("OPP_PTS")
            wl = row.get("WL")

            margin = (pts - opp_pts) if (pts and opp_pts) else None

            games_list.append(
                TeamNetRatingGame(
                    game_id=game_id,
                    game_date=game_date,
                    opponent_abbr=opponent_abbr,
                    pts=pts,
                    opp_pts=opp_pts,
                    margin=margin,
                    rolling_net_rating=None,
                    wl=wl,
                )
            )

        games_list.reverse()

        for i in range(len(games_list)):
            start = max(0, i - window + 1)
            window_games = games_list[start : i + 1]
            margins = [g.margin for g in window_games if g.margin is not None]
            if margins:
                rolling_nr = sum(margins) / len(margins)
                games_list[i].rolling_net_rating = round(rolling_nr, 2)

        season_margins = [g.margin for g in games_list if g.margin is not None]
        season_avg_margin = sum(season_margins) / len(season_margins) if season_margins else None

        return TeamNetRatingSeriesResponse(
            team_abbr=team_abbr,
            season=season,
            window=window,
            games=games_list,
            season_avg_margin=round(season_avg_margin, 2) if season_avg_margin is not None else None,
            data_status="ready",
        )

    except Exception:
        return TeamNetRatingSeriesResponse(
            team_abbr=team_abbr,
            season=season,
            window=window,
            games=[],
            data_status="error",
        )
