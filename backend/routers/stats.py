from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Player, SeasonStat
from models.stats import CareerStatsResponse, SeasonStats
from services.sync_service import sync_player_if_needed

router = APIRouter()


def _stat_to_dict(stat: SeasonStat) -> dict:
    """Convert a SeasonStat ORM object to a dict matching the SeasonStats Pydantic model."""
    return {
        "season": stat.season,
        "team_abbreviation": stat.team_abbreviation,
        "gp": stat.gp or 0,
        "gs": stat.gs or 0,
        "min_pg": stat.min_pg or 0,
        "pts_pg": stat.pts_pg or 0,
        "reb_pg": stat.reb_pg or 0,
        "ast_pg": stat.ast_pg or 0,
        "stl_pg": stat.stl_pg or 0,
        "blk_pg": stat.blk_pg or 0,
        "tov_pg": stat.tov_pg or 0,
        "fg_pct": stat.fg_pct or 0,
        "fg3_pct": stat.fg3_pct or 0,
        "ft_pct": stat.ft_pct or 0,
        "pts": stat.pts or 0,
        "reb": stat.reb or 0,
        "ast": stat.ast or 0,
        "fgm": stat.fgm or 0,
        "fga": stat.fga or 0,
        "fg3m": stat.fg3m or 0,
        "fg3a": stat.fg3a or 0,
        "ftm": stat.ftm or 0,
        "fta": stat.fta or 0,
        "oreb": stat.oreb or 0,
        "dreb": stat.dreb or 0,
        "stl": stat.stl or 0,
        "blk": stat.blk or 0,
        "tov": stat.tov or 0,
        "pf": stat.pf or 0,
        "min_total": stat.min_total or 0,
        "ts_pct": stat.ts_pct,
        "efg_pct": stat.efg_pct,
        "usg_pct": stat.usg_pct,
        "per": stat.per,
        "bpm": stat.bpm,
        "off_rating": stat.off_rating,
        "def_rating": stat.def_rating,
        "net_rating": stat.net_rating,
        "ws": stat.ws,
        "vorp": stat.vorp,
        "pie": stat.pie,
        "pace": stat.pace,
    }


def _compute_career_totals(seasons: list) -> dict:
    """Compute career totals from a list of season stat dicts."""
    if not seasons:
        return None

    totals = {}
    sum_fields = [
        "gp", "gs", "pts", "reb", "ast", "stl", "blk", "tov",
        "fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "oreb", "dreb", "pf",
    ]
    for field in sum_fields:
        totals[field] = sum(s.get(field, 0) for s in seasons)

    totals["min_total"] = sum(s.get("min_total", 0) for s in seasons)
    gp = totals["gp"] or 1
    totals["min_pg"] = round(totals["min_total"] / gp, 1)
    totals["pts_pg"] = round(totals["pts"] / gp, 1)
    totals["reb_pg"] = round(totals["reb"] / gp, 1)
    totals["ast_pg"] = round(totals["ast"] / gp, 1)
    totals["stl_pg"] = round(totals["stl"] / gp, 1)
    totals["blk_pg"] = round(totals["blk"] / gp, 1)
    totals["tov_pg"] = round(totals["tov"] / gp, 1)
    totals["fg_pct"] = round(totals["fgm"] / totals["fga"], 3) if totals["fga"] else 0
    totals["fg3_pct"] = round(totals["fg3m"] / totals["fg3a"], 3) if totals["fg3a"] else 0
    totals["ft_pct"] = round(totals["ftm"] / totals["fta"], 3) if totals["fta"] else 0

    # Advanced career totals - compute from raw totals
    from services.advanced_metrics import calculate_ts_pct, calculate_efg_pct, calculate_per_simplified
    totals["ts_pct"] = calculate_ts_pct(totals["pts"], totals["fga"], totals["fta"])
    totals["efg_pct"] = calculate_efg_pct(totals["fgm"], totals["fg3m"], totals["fga"])
    totals["per"] = calculate_per_simplified(totals)

    totals["season"] = "Career"
    totals["team_abbreviation"] = ""
    totals["usg_pct"] = None
    totals["bpm"] = None
    totals["off_rating"] = None
    totals["def_rating"] = None
    totals["net_rating"] = None
    totals["ws"] = None
    totals["vorp"] = None
    totals["pie"] = None
    totals["pace"] = None

    return totals


@router.get("/{player_id}/career", response_model=CareerStatsResponse)
def career_stats(player_id: int, db: Session = Depends(get_db)):
    try:
        player = sync_player_if_needed(db, player_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {e}")

    # Get regular season stats from DB, ordered by season
    regular_stats = (
        db.query(SeasonStat)
        .filter(SeasonStat.player_id == player_id, SeasonStat.is_playoff == False)
        .order_by(SeasonStat.season)
        .all()
    )

    playoff_stats = (
        db.query(SeasonStat)
        .filter(SeasonStat.player_id == player_id, SeasonStat.is_playoff == True)
        .order_by(SeasonStat.season)
        .all()
    )

    seasons = [_stat_to_dict(s) for s in regular_stats]
    playoff_seasons = [_stat_to_dict(s) for s in playoff_stats]
    career_totals = _compute_career_totals(seasons)

    return CareerStatsResponse(
        player_id=player_id,
        player_name=player.full_name,
        seasons=[SeasonStats(**s) for s in seasons],
        career_totals=SeasonStats(**career_totals) if career_totals else None,
        playoff_seasons=[SeasonStats(**s) for s in playoff_seasons],
    )
