from __future__ import annotations

import json
import time
from typing import Optional
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd
from nba_api.stats.endpoints import (
    boxscoretraditionalv2,
    commonplayerinfo,
    leaguedashplayerstats,
    leaguegamelog,
    playergamelog,
    playbyplayv3,
    playercareerstats,
    shotchartdetail,
)
from nba_api.live.nba.endpoints import boxscore as live_boxscore
from nba_api.stats.static import players as static_players

from config import NBA_API_DELAY, NBA_API_TIMEOUT

_last_request_time = 0.0
NBA_LIVE_BASE_URL = "https://cdn.nba.com/static/json/liveData"
NBA_LIVE_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
}


def _canonical_name(name: str) -> str:
    if not name:
        return ""
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return " ".join(normalized.lower().replace(".", "").split())


def _rate_limit():
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < NBA_API_DELAY:
        time.sleep(NBA_API_DELAY - elapsed)
    _last_request_time = time.time()


def _fetch_live_json(path: str, timeout: int = NBA_API_TIMEOUT) -> dict:
    """Fetch raw JSON from NBA's public live-data CDN."""
    request = Request(f"{NBA_LIVE_BASE_URL}/{path}", headers=NBA_LIVE_HEADERS)
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"NBA live data HTTP {exc.code} for {path}") from exc
    except URLError as exc:
        raise RuntimeError(f"NBA live data network error for {path}: {exc.reason}") from exc


def _normalize_pbp_rows(rows: list[dict]) -> list[dict]:
    """Convert raw NBA live/stats play-by-play rows into the app's canonical shape."""
    normalized_rows: list[dict] = []
    last_miss_team_id: Optional[int] = None

    for row in rows:
        raw_action = str(row.get("actionType") or "")
        raw_sub_type = str(row.get("subType") or "")
        description = str(row.get("description") or "")
        shot_value = int(row.get("shotValue") or 0)

        team_id = row.get("teamId") or None
        person_id = row.get("personId") or None
        if team_id == 0:
            team_id = None
        if person_id == 0:
            person_id = None

        action_type = raw_action.lower()
        sub_type = raw_sub_type.lower()

        if raw_action in {"Made Shot", "Missed Shot"}:
            action_type = "3pt" if shot_value == 3 else "2pt"
            sub_type = "made" if raw_action == "Made Shot" else "missed"
            last_miss_team_id = team_id if sub_type == "missed" else None
        elif raw_action == "Free Throw":
            action_type = "freethrow"
            sub_type = "missed" if description.upper().startswith("MISS ") else "made"
            last_miss_team_id = team_id if sub_type == "missed" else None
        elif raw_action == "Turnover":
            action_type = "turnover"
            last_miss_team_id = None
        elif raw_action == "Rebound":
            action_type = "rebound"
            rebound_team_id = team_id or person_id
            team_id = rebound_team_id
            if rebound_team_id and last_miss_team_id:
                sub_type = "offensive" if rebound_team_id == last_miss_team_id else "defensive"
            else:
                sub_type = "unknown"
            last_miss_team_id = None
        elif raw_action == "Substitution":
            action_type = "substitution"
            sub_type = ""
            last_miss_team_id = None
        elif raw_action == "period":
            action_type = "period"
            last_miss_team_id = None

        normalized_rows.append(
            {
                "gameId": row.get("gameId"),
                "actionNumber": row.get("actionNumber"),
                "actionId": row.get("actionId"),
                "clock": row.get("clock"),
                "period": row.get("period"),
                "teamId": team_id,
                "personId": person_id,
                "description": description,
                "actionType": action_type,
                "subType": sub_type,
                "scoreHome": row.get("scoreHome"),
                "scoreAway": row.get("scoreAway"),
                "playerName": row.get("playerName"),
                "incomingPlayerName": _canonical_name(description.split("SUB:", 1)[1].split(" FOR ", 1)[0].strip())
                if raw_action == "Substitution" and " FOR " in description
                else "",
                "outgoingPlayerName": _canonical_name(description.rsplit(" FOR ", 1)[1].strip())
                if raw_action == "Substitution" and " FOR " in description
                else "",
            }
        )
    return normalized_rows


def _normalize_live_box_score(live_data: dict) -> dict:
    """Convert NBA live box score JSON into the app's canonical game shape."""
    game = live_data.get("game", live_data)
    home_team = game.get("homeTeam", {})
    away_team = game.get("awayTeam", {})

    players = []
    for team in [home_team, away_team]:
        team_id = team.get("teamId")
        for p in team.get("players", []):
            players.append(
                {
                    "player_id": p.get("personId"),
                    "player_name": p.get("name", ""),
                    "team_id": team_id,
                    "start_position": p.get("position", "") if p.get("starter") == "1" else "",
                }
            )

    return {
        "home_team_id": home_team.get("teamId"),
        "away_team_id": away_team.get("teamId"),
        "home_team_abbreviation": home_team.get("teamTricode", ""),
        "away_team_abbreviation": away_team.get("teamTricode", ""),
        "home_team_name": home_team.get("teamName", ""),
        "away_team_name": away_team.get("teamName", ""),
        "home_score": int(home_team.get("score") or 0),
        "away_score": int(away_team.get("score") or 0),
        "players": players,
    }


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


def get_season_game_ids(season: str, timeout: int = NBA_API_TIMEOUT) -> list[str]:
    """Return all regular-season game IDs for a given season (e.g. '2023-24')."""
    _rate_limit()
    log = leaguegamelog.LeagueGameLog(
        season=season,
        player_or_team_abbreviation="T",
        timeout=timeout,
    )
    data = log.get_normalized_dict()
    rows = data.get("LeagueGameLog", [])
    # Each team has its own row per game — deduplicate by game_id
    seen: set[str] = set()
    ids: list[str] = []
    for row in rows:
        gid = str(row.get("GAME_ID", ""))
        if gid and gid not in seen:
            seen.add(gid)
            ids.append(gid)
    return ids


def get_player_game_ids(
    player_id: int,
    season: str,
    timeout: int = NBA_API_TIMEOUT,
) -> list[str]:
    """Return regular-season game IDs for a player in a given season."""
    _rate_limit()
    log = playergamelog.PlayerGameLog(
        player_id=player_id,
        season=season,
        season_type_all_star="Regular Season",
        timeout=timeout,
    )
    data = log.get_normalized_dict()
    rows = data.get("PlayerGameLog", [])
    ids: list[str] = []
    for row in rows:
        gid = str(row.get("Game_ID", ""))
        if gid:
            ids.append(gid)
    return ids


def get_player_game_logs(
    player_id: int,
    season: str,
    season_type: str = "Regular Season",
    timeout: int = NBA_API_TIMEOUT,
) -> list[dict]:
    """Return per-game stats for a player in a given season, ordered newest-first.

    Each entry contains: game_id, game_date, matchup, wl, min, pts, reb, ast,
    stl, blk, tov, fgm, fga, fg_pct, fg3m, fg3a, fg3_pct, ftm, fta, ft_pct,
    oreb, dreb, pf, plus_minus.
    """
    _rate_limit()
    log = playergamelog.PlayerGameLog(
        player_id=player_id,
        season=season,
        season_type_all_star=season_type,
        timeout=timeout,
    )
    data = log.get_normalized_dict()
    rows = data.get("PlayerGameLog", [])

    def _safe_float(val) -> Optional[float]:
        try:
            return float(val) if val is not None else None
        except (ValueError, TypeError):
            return None

    def _safe_int(val) -> Optional[int]:
        try:
            return int(val) if val is not None else None
        except (ValueError, TypeError):
            return None

    result = []
    for row in rows:
        result.append({
            "game_id": str(row.get("Game_ID", "")),
            "game_date": str(row.get("GAME_DATE", "")),
            "matchup": str(row.get("MATCHUP", "")),
            "wl": str(row.get("WL", "")),
            "min": _safe_float(row.get("MIN")),
            "pts": _safe_int(row.get("PTS")),
            "reb": _safe_int(row.get("REB")),
            "ast": _safe_int(row.get("AST")),
            "stl": _safe_int(row.get("STL")),
            "blk": _safe_int(row.get("BLK")),
            "tov": _safe_int(row.get("TOV")),
            "fgm": _safe_int(row.get("FGM")),
            "fga": _safe_int(row.get("FGA")),
            "fg_pct": _safe_float(row.get("FG_PCT")),
            "fg3m": _safe_int(row.get("FG3M")),
            "fg3a": _safe_int(row.get("FG3A")),
            "fg3_pct": _safe_float(row.get("FG3_PCT")),
            "ftm": _safe_int(row.get("FTM")),
            "fta": _safe_int(row.get("FTA")),
            "ft_pct": _safe_float(row.get("FT_PCT")),
            "oreb": _safe_int(row.get("OREB")),
            "dreb": _safe_int(row.get("DREB")),
            "pf": _safe_int(row.get("PF")),
            "plus_minus": _safe_int(row.get("PLUS_MINUS")),
        })
    return result


def get_play_by_play(game_id: str, timeout: int = NBA_API_TIMEOUT) -> list[dict]:
    """Fetch all play-by-play events for a game.

    Primary source is NBA's public live-data CDN; falls back to stats PlayByPlayV3.
    """
    _rate_limit()
    try:
        payload = _fetch_live_json(f"playbyplay/playbyplay_{game_id}.json", timeout=timeout)
        rows = payload.get("game", {}).get("actions", [])
        if rows:
            return _normalize_pbp_rows(rows)
    except Exception:
        pass

    pbp = playbyplayv3.PlayByPlayV3(
        game_id=game_id,
        start_period=0,
        end_period=0,
        timeout=timeout,
    )
    frames = pbp.get_data_frames()
    if frames and not frames[0].empty:
        return _normalize_pbp_rows(frames[0].to_dict(orient="records"))
    data = pbp.get_normalized_dict()
    return data.get("PlayByPlay", [])


def get_game_box_score(game_id: str, timeout: int = NBA_API_TIMEOUT) -> dict:
    """Fetch per-player traditional box score for a game.

    Returns {'home_team_id': int, 'away_team_id': int,
             'home_score': int, 'away_score': int,
             'players': [{'player_id', 'team_id', 'start_position', ...}]}
    """
    _rate_limit()
    try:
        live_payload = _fetch_live_json(f"boxscore/boxscore_{game_id}.json", timeout=timeout)
        normalized = _normalize_live_box_score(live_payload)
        if normalized.get("players"):
            return normalized
    except Exception:
        pass

    bs = boxscoretraditionalv2.BoxScoreTraditionalV2(
        game_id=game_id,
        timeout=timeout,
    )
    data = bs.get_normalized_dict()
    player_stats = data.get("PlayerStats", [])
    team_stats = data.get("TeamStats", [])

    if player_stats and team_stats:
        home_team_id = team_stats[0].get("TEAM_ID")
        away_team_id = team_stats[1].get("TEAM_ID") if len(team_stats) > 1 else None

        home_score, away_score = 0, 0
        for t in team_stats:
            tid = t.get("TEAM_ID")
            pts = t.get("PTS") or 0
            if tid == home_team_id:
                home_score = pts
            elif tid == away_team_id:
                away_score = pts

        players = []
        for p in player_stats:
            players.append({
                "player_id": p.get("PLAYER_ID"),
                "player_name": p.get("PLAYER_NAME", ""),
                "team_id": p.get("TEAM_ID"),
                "start_position": p.get("START_POSITION", ""),
            })

        return {
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "home_team_abbreviation": team_stats[0].get("TEAM_ABBREVIATION", "") if team_stats else "",
            "away_team_abbreviation": team_stats[1].get("TEAM_ABBREVIATION", "") if len(team_stats) > 1 else "",
            "home_team_name": team_stats[0].get("TEAM_NAME", "") if team_stats else "",
            "away_team_name": team_stats[1].get("TEAM_NAME", "") if len(team_stats) > 1 else "",
            "home_score": home_score,
            "away_score": away_score,
            "players": players,
        }

    # Newer/current-season games are more reliable through the live box score endpoint.
    _rate_limit()
    live_data = live_boxscore.BoxScore(game_id=game_id, timeout=timeout).get_dict()
    return _normalize_live_box_score(live_data)


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
