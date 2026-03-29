import statistics
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Player, SeasonStat
from models.stats import CareerStatsResponse, LeagueContext, SeasonStats
from services.advanced_metrics import (
    calculate_bpm,
    calculate_win_shares,
    calculate_vorp,
    calculate_darko,
    compute_age_at_season,
)
from services.sync_service import sync_player_if_needed

router = APIRouter()


_RATE_STATS = ["pts", "reb", "ast", "stl", "blk", "tov", "fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "oreb", "dreb", "pf"]


def _compute_per36(stat: SeasonStat) -> Optional[dict]:
    min_total = stat.min_total or 0
    if min_total < 1:
        return None
    return {
        k: round(getattr(stat, k, 0) / min_total * 36, 1)
        for k in _RATE_STATS
        if getattr(stat, k, None) is not None
    }


def _compute_per100(stat: SeasonStat) -> Optional[dict]:
    fga = stat.fga or 0
    fta = stat.fta or 0
    tov = stat.tov or 0
    gp = stat.gp or 1
    poss = fga + 0.44 * fta + tov  # season totals possessions estimate
    if poss < 1:
        return None
    return {
        k: round(getattr(stat, k, 0) / poss * 100, 1)
        for k in _RATE_STATS
        if getattr(stat, k, None) is not None
    }


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
        "darko": stat.darko,
        "epm": stat.epm,
        "rapm": stat.rapm,
        "lebron": stat.lebron,
        "raptor": stat.raptor,
        "pipm": stat.pipm,
        "obpm": stat.obpm,
        "dbpm": stat.dbpm,
        "ftr": stat.ftr,
        "par3": stat.par3,
        "ast_tov": stat.ast_tov,
        "oreb_pct": stat.oreb_pct,
        "clutch_pts": stat.clutch_pts,
        "clutch_fga": stat.clutch_fga,
        "clutch_fg_pct": stat.clutch_fg_pct,
        "clutch_plus_minus": stat.clutch_plus_minus,
        "second_chance_pts": stat.second_chance_pts,
        "fast_break_pts": stat.fast_break_pts,
        "per36": _compute_per36(stat),
        "per100": _compute_per100(stat),
    }


def _backfill_computed_metrics(db: Session, stats: List[SeasonStat], player: Player) -> bool:
    """Fill in BPM, WS, VORP, DARKO for rows that were synced before these
    formulas existed. Returns True if any rows were updated."""
    dirty = False
    for stat in stats:
        if stat.bpm is not None and stat.ws is not None and stat.darko is not None:
            continue

        row = {
            "per": stat.per,
            "gp": stat.gp or 1,
            "min_total": stat.min_total or 0,
            "stl_pg": stat.stl_pg or 0,
            "blk_pg": stat.blk_pg or 0,
            "usg_pct": stat.usg_pct,
        }

        if stat.bpm is None and stat.per is not None:
            stat.bpm = calculate_bpm(row)
            stat.ws = calculate_win_shares(stat.bpm, stat.min_total or 0)
            stat.vorp = calculate_vorp(stat.bpm, stat.min_total or 0, stat.gp or 0)
            dirty = True

        if stat.darko is None and stat.per is not None:
            age = compute_age_at_season(player.birth_date, stat.season)
            stat.darko = calculate_darko(age, stat.per, stat.ts_pct, stat.usg_pct)
            dirty = True

    if dirty:
        db.commit()
    return dirty


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

    # Career WS = sum of season WS values
    ws_values = [s.get("ws") for s in seasons if s.get("ws") is not None]
    totals["ws"] = round(sum(ws_values), 1) if ws_values else None

    # Career BPM = minutes-weighted average across seasons
    bpm_seasons = [(s["bpm"], s.get("min_total", 0)) for s in seasons if s.get("bpm") is not None]
    if bpm_seasons:
        total_mp = sum(mp for _, mp in bpm_seasons)
        totals["bpm"] = round(sum(b * mp for b, mp in bpm_seasons) / total_mp, 1) if total_mp else None
    else:
        totals["bpm"] = None

    # Career VORP = sum of season VORP values
    vorp_values = [s.get("vorp") for s in seasons if s.get("vorp") is not None]
    totals["vorp"] = round(sum(vorp_values), 1) if vorp_values else None

    totals["season"] = "Career"
    totals["team_abbreviation"] = ""
    totals["usg_pct"] = None
    totals["off_rating"] = None
    totals["def_rating"] = None
    totals["net_rating"] = None
    totals["pie"] = None
    totals["pace"] = None
    totals["darko"] = None
    totals["epm"] = None
    totals["rapm"] = None
    totals["lebron"] = None
    totals["raptor"] = None
    totals["pipm"] = None
    totals["obpm"] = None
    totals["dbpm"] = None
    totals["ftr"] = None
    totals["par3"] = None
    totals["ast_tov"] = None
    totals["oreb_pct"] = None
    totals["clutch_pts"] = None
    totals["clutch_fga"] = None
    totals["clutch_fg_pct"] = None
    totals["clutch_plus_minus"] = None
    totals["second_chance_pts"] = None
    totals["fast_break_pts"] = None
    totals["per36"] = None
    totals["per100"] = None

    return totals


@router.get("/{player_id}/percentiles")
def player_percentiles(
    player_id: int,
    season: str,
    db: Session = Depends(get_db),
):
    """Return percentile ranks (0–100) for 6 key stats vs all players in the same season."""
    PERCENTILE_STATS = ["pts_pg", "reb_pg", "ast_pg", "ts_pct", "per", "bpm"]
    MIN_GP = 15

    target = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.player_id == player_id,
            SeasonStat.season == season,
            SeasonStat.is_playoff == False,  # noqa: E712
        )
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="No stats for this player/season combination")

    all_rows = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.season == season,
            SeasonStat.is_playoff == False,  # noqa: E712
            SeasonStat.gp >= MIN_GP,
        )
        .all()
    )

    result = {}
    for stat in PERCENTILE_STATS:
        target_val = getattr(target, stat, None)
        if target_val is None:
            result[stat] = None
            continue
        all_vals = [getattr(r, stat) for r in all_rows if getattr(r, stat) is not None]
        if not all_vals:
            result[stat] = None
            continue
        below = sum(1 for v in all_vals if v < target_val)
        result[stat] = round(below / len(all_vals) * 100)

    return {"season": season, "percentiles": result}


_CONTEXT_STATS = ["pts_pg", "reb_pg", "ast_pg", "ts_pct", "per", "bpm", "usg_pct", "ast_tov"]

# Broad position groups to avoid tiny samples
_POS_MAP = {
    "PG": "G", "SG": "G", "G": "G",
    "SF": "F", "PF": "F", "F": "F",
    "C": "C",
}


def _median_map(rows: list, stats: list) -> dict:
    result = {}
    for s in stats:
        vals = [getattr(r, s) for r in rows if getattr(r, s) is not None]
        result[s] = round(statistics.median(vals), 3) if vals else None
    return result


@router.get("/context", response_model=LeagueContext)
def league_context(
    season: str = Query("2024-25"),
    position: Optional[str] = Query(None, description="Player position (PG, SG, SF, PF, C, G, F)"),
    db: Session = Depends(get_db),
):
    """Return league and position-group medians for key stats in a season."""
    MIN_GP = 15

    all_rows = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.season == season,
            SeasonStat.is_playoff == False,  # noqa: E712
            SeasonStat.gp >= MIN_GP,
        )
        .all()
    )

    if not all_rows:
        raise HTTPException(status_code=404, detail=f"No stats found for season {season}")

    league_medians = _median_map(all_rows, _CONTEXT_STATS)

    # Position-group filtering
    position_group: Optional[str] = None
    position_medians: dict = {s: None for s in _CONTEXT_STATS}

    if position:
        position_group = _POS_MAP.get(position.upper())
        if position_group:
            # Collect player positions from joined Player table
            player_ids_in_group = {
                p.id
                for p in db.query(Player).all()
                if p.position and _POS_MAP.get(p.position.upper()) == position_group
            }
            pos_rows = [r for r in all_rows if r.player_id in player_ids_in_group]
            if pos_rows:
                position_medians = _median_map(pos_rows, _CONTEXT_STATS)

    return LeagueContext(
        season=season,
        position_group=position_group,
        league_medians=league_medians,
        position_medians=position_medians,
    )


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

    # Backfill computed metrics for players synced before BPM/WS/DARKO were implemented
    _backfill_computed_metrics(db, regular_stats, player)

    # Deduplicate: for mid-season trades, keep only the highest-GP row per season.
    # Also filter out future seasons (season start year > current year + 1).
    def _dedup_seasons(rows: List[SeasonStat]) -> List[SeasonStat]:
        from datetime import date
        current_year = date.today().year
        best: dict = {}
        for r in rows:
            # Filter out clearly bogus future seasons
            try:
                season_start = int(r.season.split("-")[0])
                if season_start > current_year + 1:
                    continue
            except (ValueError, AttributeError):
                pass
            if r.season not in best or (r.gp or 0) > (best[r.season].gp or 0):
                best[r.season] = r
        return sorted(best.values(), key=lambda s: s.season)

    seasons = [_stat_to_dict(s) for s in _dedup_seasons(regular_stats)]
    playoff_seasons = [_stat_to_dict(s) for s in _dedup_seasons(playoff_stats)]
    career_totals = _compute_career_totals(seasons)

    return CareerStatsResponse(
        player_id=player_id,
        player_name=player.full_name,
        seasons=[SeasonStats(**s) for s in seasons],
        career_totals=SeasonStats(**career_totals) if career_totals else None,
        playoff_seasons=[SeasonStats(**s) for s in playoff_seasons],
    )
