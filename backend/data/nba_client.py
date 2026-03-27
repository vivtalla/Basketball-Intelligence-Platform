from __future__ import annotations

import time
from typing import Optional

import pandas as pd
from nba_api.stats.endpoints import (
    commonplayerinfo,
    leaguedashplayerstats,
    playercareerstats,
    shotchartdetail,
)
from nba_api.stats.static import players as static_players

from config import NBA_API_DELAY, NBA_API_TIMEOUT

_last_request_time = 0.0


def _rate_limit():
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < NBA_API_DELAY:
        time.sleep(NBA_API_DELAY - elapsed)
    _last_request_time = time.time()


def search_players(query: str) -> list[dict]:
    """Search players by name. Uses local static data (no HTTP call)."""
    results = static_players.find_players_by_full_name(query)
    return [
        {
            "id": p["id"],
            "full_name": p["full_name"],
            "is_active": p["is_active"],
        }
        for p in results
    ]


def get_player_info(player_id: int) -> dict:
    """Fetch player bio/profile from NBA.com."""
    _rate_limit()
    info = commonplayerinfo.CommonPlayerInfo(
        player_id=player_id, timeout=NBA_API_TIMEOUT
    )
    data = info.get_normalized_dict()
    player = data["CommonPlayerInfo"][0]

    return {
        "id": player_id,
        "full_name": player.get("DISPLAY_FIRST_LAST", ""),
        "first_name": player.get("FIRST_NAME", ""),
        "last_name": player.get("LAST_NAME", ""),
        "team_name": player.get("TEAM_NAME", ""),
        "team_abbreviation": player.get("TEAM_ABBREVIATION", ""),
        "team_id": player.get("TEAM_ID"),
        "jersey": player.get("JERSEY", ""),
        "position": player.get("POSITION", ""),
        "height": player.get("HEIGHT", ""),
        "weight": player.get("WEIGHT", ""),
        "birth_date": player.get("BIRTHDATE", ""),
        "country": player.get("COUNTRY", ""),
        "school": player.get("SCHOOL", ""),
        "draft_year": player.get("DRAFT_YEAR"),
        "draft_round": player.get("DRAFT_ROUND"),
        "draft_number": player.get("DRAFT_NUMBER"),
        "from_year": player.get("FROM_YEAR"),
        "to_year": player.get("TO_YEAR"),
        "headshot_url": f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png",
    }


def get_career_stats(player_id: int) -> dict:
    """Fetch career stats (season-by-season + career totals)."""
    _rate_limit()
    career = playercareerstats.PlayerCareerStats(
        player_id=player_id, timeout=NBA_API_TIMEOUT
    )
    data = career.get_normalized_dict()

    return {
        "season_totals": data.get("SeasonTotalsRegularSeason", []),
        "career_totals": data.get("CareerTotalsRegularSeason", []),
        "post_season_totals": data.get("SeasonTotalsPostSeason", []),
        "post_career_totals": data.get("CareerTotalsPostSeason", []),
    }


def get_league_dash_player_stats(
    season: str, measure_type: str = "Advanced"
) -> list[dict]:
    """Fetch league-wide player stats for a given season.

    measure_type: 'Base' for traditional, 'Advanced' for advanced metrics.
    """
    _rate_limit()
    dash = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        measure_type_detailed_defense=measure_type,
        timeout=NBA_API_TIMEOUT,
    )
    data = dash.get_normalized_dict()
    return data.get("LeagueDashPlayerStats", [])


def get_player_advanced_stats_from_league(
    player_id: int, league_stats: list[dict]
) -> Optional[dict]:
    """Extract a single player's advanced stats from the league-wide dataset."""
    for player in league_stats:
        if player.get("PLAYER_ID") == player_id:
            return player
    return None


def get_shot_chart_data(
    player_id: int, season: str, season_type: str = "Regular Season"
) -> list[dict]:
    """Fetch all shot attempts for a player in a given season from NBA.com.

    Returns a list of shot dicts with: loc_x, loc_y, shot_made, shot_type,
    action_type, zone_basic, zone_area, distance.
    """
    _rate_limit()
    response = shotchartdetail.ShotChartDetail(
        player_id=player_id,
        team_id=0,
        game_id_nullable="",
        season_nullable=season,
        season_type_all_star=season_type,
        context_measure_simple="FGA",
        timeout=NBA_API_TIMEOUT,
    )
    frames = response.get_data_frames()
    if not frames or frames[0].empty:
        return []
    df = frames[0]
    shots = []
    for _, row in df.iterrows():
        shots.append({
            "loc_x": int(row.get("LOC_X", 0)),
            "loc_y": int(row.get("LOC_Y", 0)),
            "shot_made": bool(row.get("SHOT_MADE_FLAG", 0)),
            "shot_type": str(row.get("SHOT_TYPE", "")),
            "action_type": str(row.get("ACTION_TYPE", "")),
            "zone_basic": str(row.get("SHOT_ZONE_BASIC", "")),
            "zone_area": str(row.get("SHOT_ZONE_AREA", "")),
            "distance": int(row.get("SHOT_DISTANCE", 0)),
        })
    return shots
