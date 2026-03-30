from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import GamePlayerStat, GameTeamStat, Player, WarehouseGame
from models.game import GamePlayerBoxScore, GameSummaryResponse, GameTeamBoxScore


def _percentage(made: Optional[int], attempted: Optional[int]) -> Optional[float]:
    if made is None or attempted is None or attempted == 0:
        return None
    return float(made) / float(attempted)


def _team_box_score(row: GameTeamStat) -> GameTeamBoxScore:
    return GameTeamBoxScore(
        team_id=row.team_id,
        team_abbreviation=row.team_abbreviation,
        is_home=bool(row.is_home),
        won=row.won,
        pts=row.pts or 0,
        reb=row.reb or 0,
        ast=row.ast or 0,
        stl=row.stl or 0,
        blk=row.blk or 0,
        tov=row.tov or 0,
        fgm=row.fgm or 0,
        fga=row.fga or 0,
        fg_pct=_percentage(row.fgm, row.fga),
        fg3m=row.fg3m or 0,
        fg3a=row.fg3a or 0,
        fg3_pct=_percentage(row.fg3m, row.fg3a),
        ftm=row.ftm or 0,
        fta=row.fta or 0,
        ft_pct=_percentage(row.ftm, row.fta),
        oreb=row.oreb or 0,
        dreb=row.dreb or 0,
        pf=row.pf or 0,
        plus_minus=row.plus_minus,
    )


def _player_box_score(row: GamePlayerStat, player: Optional[Player]) -> GamePlayerBoxScore:
    return GamePlayerBoxScore(
        player_id=row.player_id,
        player_name=player.full_name if player else str(row.player_id),
        team_id=row.team_id,
        team_abbreviation=row.team_abbreviation,
        is_starter=bool(row.is_starter),
        wl=row.wl,
        min=row.min,
        pts=row.pts or 0,
        reb=row.reb or 0,
        ast=row.ast or 0,
        stl=row.stl or 0,
        blk=row.blk or 0,
        tov=row.tov or 0,
        fgm=row.fgm or 0,
        fga=row.fga or 0,
        fg_pct=row.fg_pct,
        fg3m=row.fg3m or 0,
        fg3a=row.fg3a or 0,
        fg3_pct=row.fg3_pct,
        ftm=row.ftm or 0,
        fta=row.fta or 0,
        ft_pct=row.ft_pct,
        oreb=row.oreb or 0,
        dreb=row.dreb or 0,
        pf=row.pf or 0,
        plus_minus=row.plus_minus,
    )


def _player_sort_key(
    item: Tuple[GamePlayerStat, Optional[Player]],
    home_team_id: Optional[int],
    away_team_id: Optional[int],
) -> Tuple[int, int, float, int, int]:
    row = item[0]
    if row.team_id == home_team_id:
        team_order = 0
    elif row.team_id == away_team_id:
        team_order = 1
    else:
        team_order = 2
    return (
        0 if row.is_starter else 1,
        team_order,
        -(row.min or 0.0),
        -(row.pts or 0),
        row.player_id,
    )


def get_game_summary(db: Session, game_id: str) -> Optional[GameSummaryResponse]:
    game = db.query(WarehouseGame).filter(WarehouseGame.game_id == game_id).first()
    if not game:
        return None

    response = GameSummaryResponse(
        game_id=game.game_id,
        season=game.season,
        game_date=game.game_date.isoformat() if game.game_date else None,
        home_team_id=game.home_team_id,
        away_team_id=game.away_team_id,
        home_team_abbreviation=game.home_team_abbreviation,
        away_team_abbreviation=game.away_team_abbreviation,
        home_score=game.home_score,
        away_score=game.away_score,
        materialized=bool(game.has_materialized_game_stats),
        home_team_stats=None,
        away_team_stats=None,
        players=[],
    )
    if not game.has_materialized_game_stats:
        return response

    team_rows = (
        db.query(GameTeamStat)
        .filter(GameTeamStat.game_id == game_id)
        .order_by(GameTeamStat.is_home.desc(), GameTeamStat.team_id.asc())
        .all()
    )
    for row in team_rows:
        box_score = _team_box_score(row)
        if row.is_home:
            response.home_team_stats = box_score
        else:
            response.away_team_stats = box_score

    player_rows = (
        db.query(GamePlayerStat, Player)
        .outerjoin(Player, Player.id == GamePlayerStat.player_id)
        .filter(GamePlayerStat.game_id == game_id)
        .all()
    )
    sorted_rows = sorted(
        player_rows,
        key=lambda item: _player_sort_key(item, game.home_team_id, game.away_team_id),
    )
    response.players = [_player_box_score(row, player) for row, player in sorted_rows]
    return response
