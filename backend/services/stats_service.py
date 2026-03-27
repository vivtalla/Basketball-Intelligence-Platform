"""Service for fetching and transforming player stats."""
from __future__ import annotations

from data.cache import CacheManager
from data.nba_client import (
    get_career_stats,
    get_league_dash_player_stats,
    get_player_advanced_stats_from_league,
)
from config import CACHE_TTL_CAREER_STATS, CACHE_TTL_LEAGUE_DASH
from services.advanced_metrics import enrich_season_with_advanced


def _transform_season_row(row: dict) -> dict:
    """Transform a raw nba_api season row into our internal format."""
    gp = row.get("GP", 0) or 1  # avoid division by zero

    return {
        "season": row.get("SEASON_ID", ""),
        "team_abbreviation": row.get("TEAM_ABBREVIATION", ""),
        "gp": row.get("GP", 0),
        "gs": row.get("GS", 0),
        "min_total": row.get("MIN", 0),
        "min_pg": round(row.get("MIN", 0) / gp, 1),
        "pts": row.get("PTS", 0),
        "pts_pg": round(row.get("PTS", 0) / gp, 1),
        "reb": row.get("REB", 0),
        "reb_pg": round(row.get("REB", 0) / gp, 1),
        "ast": row.get("AST", 0),
        "ast_pg": round(row.get("AST", 0) / gp, 1),
        "stl": row.get("STL", 0),
        "stl_pg": round(row.get("STL", 0) / gp, 1),
        "blk": row.get("BLK", 0),
        "blk_pg": round(row.get("BLK", 0) / gp, 1),
        "tov": row.get("TOV", 0),
        "tov_pg": round(row.get("TOV", 0) / gp, 1),
        "fgm": row.get("FGM", 0),
        "fga": row.get("FGA", 0),
        "fg_pct": row.get("FG_PCT", 0) or 0,
        "fg3m": row.get("FG3M", 0),
        "fg3a": row.get("FG3A", 0),
        "fg3_pct": row.get("FG3_PCT", 0) or 0,
        "ftm": row.get("FTM", 0),
        "fta": row.get("FTA", 0),
        "ft_pct": row.get("FT_PCT", 0) or 0,
        "oreb": row.get("OREB", 0),
        "dreb": row.get("DREB", 0),
        "pf": row.get("PF", 0),
    }


def _get_league_advanced_cached(season: str) -> list[dict]:
    """Fetch league-wide advanced stats with caching."""
    cache_key = f"league_dash_advanced:{season}"
    cached = CacheManager.get(cache_key)
    if cached:
        return cached

    data = get_league_dash_player_stats(season, measure_type="Advanced")
    CacheManager.set(cache_key, data, CACHE_TTL_LEAGUE_DASH)
    return data


def get_player_career_stats(player_id: int, player_name: str = "") -> dict:
    """Get full career stats with advanced metrics for a player."""
    # Check cache
    cache_key = f"career_stats:{player_id}"
    cached = CacheManager.get(cache_key)
    if cached:
        return cached

    raw = get_career_stats(player_id)

    # Transform regular season stats
    seasons = []
    for row in raw.get("season_totals", []):
        season_data = _transform_season_row(row)
        season_id = row.get("SEASON_ID", "")

        # Try to get advanced stats from league dashboard
        advanced_data = None
        try:
            league_stats = _get_league_advanced_cached(season_id)
            advanced_data = get_player_advanced_stats_from_league(
                player_id, league_stats
            )
        except Exception:
            pass  # Advanced stats unavailable for this season

        season_data = enrich_season_with_advanced(season_data, advanced_data)
        seasons.append(season_data)

    # Transform career totals
    career_totals = None
    if raw.get("career_totals"):
        career_totals = _transform_season_row(raw["career_totals"][0])
        career_totals["season"] = "Career"
        career_totals = enrich_season_with_advanced(career_totals, None)

    # Transform playoff seasons
    playoff_seasons = []
    for row in raw.get("post_season_totals", []):
        playoff_seasons.append(_transform_season_row(row))

    result = {
        "player_id": player_id,
        "player_name": player_name,
        "seasons": seasons,
        "career_totals": career_totals,
        "playoff_seasons": playoff_seasons,
    }

    CacheManager.set(cache_key, result, CACHE_TTL_CAREER_STATS)
    return result
