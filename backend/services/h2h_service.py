from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from db.models import GameLog, Team
from models.decision import H2HGame, H2HResponse


def build_h2h_history(
    db: Session,
    team_abbr: str,
    opponent_abbr: str,
    season: str,
    lookback_seasons: int = 3,
) -> H2HResponse:
    """Build head-to-head history for two teams across recent seasons."""
    try:
        team = db.query(Team).filter(Team.abbreviation == team_abbr).first()
        opponent = db.query(Team).filter(Team.abbreviation == opponent_abbr).first()

        if not team or not opponent:
            return H2HResponse(
                team_abbr=team_abbr,
                opponent_abbr=opponent_abbr,
                seasons_covered=[],
                wins=0,
                losses=0,
                series_record="0-0",
                avg_margin=None,
                last_meeting_date=None,
                last_meeting_result=None,
                games=[],
                data_status="unavailable",
            )

        team_id = team.id
        opponent_id = opponent.id

        season_int = int(season.split("-")[0])
        lookback_seasons_list = [
            f"{season_int - i}-{(season_int - i) + 1}" for i in range(lookback_seasons)
        ]

        games_query = db.query(GameLog).filter(
            GameLog.season.in_(lookback_seasons_list),
            (
                (GameLog.home_team_id == team_id) & (GameLog.away_team_id == opponent_id)
            )
            | ((GameLog.away_team_id == team_id) & (GameLog.home_team_id == opponent_id)),
        )

        games_data = games_query.all()

        games_list: List[H2HGame] = []
        wins = 0
        losses = 0

        for game in sorted(games_data, key=lambda g: g.game_date or ""):
            is_home = game.home_team_id == team_id
            team_score = game.home_score if is_home else game.away_score
            opponent_score = game.away_score if is_home else game.home_score
            margin = (team_score or 0) - (opponent_score or 0) if team_score and opponent_score else None
            result = "W" if margin and margin > 0 else "L" if margin and margin < 0 else "T"

            if result == "W":
                wins += 1
            elif result == "L":
                losses += 1

            games_list.append(
                H2HGame(
                    game_id=game.game_id,
                    game_date=game.game_date.isoformat() if game.game_date else None,
                    season=game.season,
                    is_home=is_home,
                    team_score=team_score,
                    opponent_score=opponent_score,
                    margin=margin,
                    result=result,
                )
            )

        games_list_sorted = sorted(games_list, key=lambda g: g.game_date or "", reverse=True)

        avg_margin = None
        if games_list:
            margins = [g.margin for g in games_list if g.margin is not None]
            avg_margin = sum(margins) / len(margins) if margins else None

        last_meeting = games_list_sorted[0] if games_list_sorted else None
        last_meeting_date = last_meeting.game_date if last_meeting else None
        last_meeting_result = last_meeting.result if last_meeting else None

        series_record = f"{wins}-{losses}"

        return H2HResponse(
            team_abbr=team_abbr,
            opponent_abbr=opponent_abbr,
            seasons_covered=lookback_seasons_list,
            wins=wins,
            losses=losses,
            series_record=series_record,
            avg_margin=round(avg_margin, 2) if avg_margin is not None else None,
            last_meeting_date=last_meeting_date,
            last_meeting_result=last_meeting_result,
            games=games_list_sorted[:5],
            data_status="ready",
        )

    except Exception:
        return H2HResponse(
            team_abbr=team_abbr,
            opponent_abbr=opponent_abbr,
            seasons_covered=[],
            wins=0,
            losses=0,
            series_record="0-0",
            avg_margin=None,
            last_meeting_date=None,
            last_meeting_result=None,
            games=[],
            data_status="error",
        )
