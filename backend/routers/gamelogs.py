"""Game log endpoints — per-game stats for a player in a season."""

from typing import Optional

from fastapi import APIRouter, HTTPException

from data.nba_client import get_player_game_logs

router = APIRouter()


@router.get("/{player_id}")
def player_game_logs(
    player_id: int,
    season: str = "2024-25",
    season_type: str = "Regular Season",
):
    """Return per-game stats for a player, ordered newest-first.

    season_type: 'Regular Season' | 'Playoffs' | 'Pre Season'
    """
    try:
        logs = get_player_game_logs(player_id, season, season_type)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"NBA API error: {exc}")

    if not logs:
        raise HTTPException(
            status_code=404,
            detail=f"No game logs found for player {player_id} in {season} {season_type}.",
        )

    # Compute rolling 5-game averages for pts/reb/ast (newest-first order)
    def _rolling_avg(values: list[Optional[int]], window: int = 5) -> list[Optional[float]]:
        result = []
        for i in range(len(values)):
            # Look back from current position (values are newest-first, so look forward)
            end = min(i + window, len(values))
            chunk = [v for v in values[i:end] if v is not None]
            result.append(round(sum(chunk) / len(chunk), 1) if chunk else None)
        return result

    pts_vals = [g["pts"] for g in logs]
    reb_vals = [g["reb"] for g in logs]
    ast_vals = [g["ast"] for g in logs]

    pts_roll = _rolling_avg(pts_vals)
    reb_roll = _rolling_avg(reb_vals)
    ast_roll = _rolling_avg(ast_vals)

    for i, game in enumerate(logs):
        game["pts_roll5"] = pts_roll[i]
        game["reb_roll5"] = reb_roll[i]
        game["ast_roll5"] = ast_roll[i]

    # Season-to-date averages
    def _avg(vals: list) -> Optional[float]:
        clean = [v for v in vals if v is not None]
        return round(sum(clean) / len(clean), 1) if clean else None

    season_avgs = {
        "pts": _avg(pts_vals),
        "reb": _avg(reb_vals),
        "ast": _avg(ast_vals),
        "stl": _avg([g["stl"] for g in logs]),
        "blk": _avg([g["blk"] for g in logs]),
        "tov": _avg([g["tov"] for g in logs]),
        "fg_pct": _avg([g["fg_pct"] for g in logs if g["fg_pct"] is not None]),
        "fg3_pct": _avg([g["fg3_pct"] for g in logs if g["fg3_pct"] is not None]),
        "ft_pct": _avg([g["ft_pct"] for g in logs if g["ft_pct"] is not None]),
        "min": _avg([g["min"] for g in logs]),
        "plus_minus": _avg([g["plus_minus"] for g in logs]),
    }

    return {
        "player_id": player_id,
        "season": season,
        "season_type": season_type,
        "games": logs,
        "season_averages": season_avgs,
        "gp": len(logs),
    }
