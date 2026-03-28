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
    leaguedashteamstats,
    leaguegamelog,
    leaguestandings,
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
NBA_STATIC_BASE_URL = "https://cdn.nba.com/static/json/staticData"
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


def _fetch_nba_json(base_url: str, path: str, timeout: int = NBA_API_TIMEOUT) -> dict:
    """Fetch raw JSON from NBA's public JSON feeds."""
    request = Request(f"{base_url}/{path}", headers=NBA_LIVE_HEADERS)
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"NBA JSON HTTP {exc.code} for {path}") from exc
    except URLError as exc:
        raise RuntimeError(f"NBA JSON network error for {path}: {exc.reason}") from exc


def _fetch_live_json(path: str, timeout: int = NBA_API_TIMEOUT) -> dict:
    """Fetch raw JSON from NBA's public live-data CDN."""
    return _fetch_nba_json(NBA_LIVE_BASE_URL, path, timeout=timeout)


def _fetch_static_json(path: str, timeout: int = NBA_API_TIMEOUT) -> dict:
    """Fetch raw JSON from NBA's public static-data CDN."""
    return _fetch_nba_json(NBA_STATIC_BASE_URL, path, timeout=timeout)


def _current_schedule_game_ids(season: str, timeout: int = NBA_API_TIMEOUT) -> list[str]:
    """Return current-season regular-season game IDs from the free NBA schedule feed."""
    payload = _fetch_static_json("scheduleLeagueV2.json", timeout=timeout)
    league_schedule = payload.get("leagueSchedule", {})
    season_year = str(league_schedule.get("seasonYear") or "")
    if season_year != season:
        return []

    ids: list[str] = []
    seen: set[str] = set()
    for game_date in league_schedule.get("gameDates", []):
        for game in game_date.get("games", []):
            game_id = str(game.get("gameId") or "")
            if not game_id or game_id in seen:
                continue
            if game_id.startswith("002"):
                seen.add(game_id)
                ids.append(game_id)
    return ids


def _current_team_schedule_game_ids(
    season: str,
    team_id: int,
    timeout: int = NBA_API_TIMEOUT,
) -> list[str]:
    """Return current-season regular-season game IDs for one team from the free NBA schedule feed."""
    payload = _fetch_static_json("scheduleLeagueV2.json", timeout=timeout)
    league_schedule = payload.get("leagueSchedule", {})
    season_year = str(league_schedule.get("seasonYear") or "")
    if season_year != season:
        return []

    ids: list[str] = []
    seen: set[str] = set()
    team_id_str = str(team_id)
    for game_date in league_schedule.get("gameDates", []):
        for game in game_date.get("games", []):
            game_id = str(game.get("gameId") or "")
            if not game_id or game_id in seen or not game_id.startswith("002"):
                continue

            home_team_id = str(game.get("homeTeam", {}).get("teamId") or "")
            away_team_id = str(game.get("awayTeam", {}).get("teamId") or "")
            if team_id_str not in {home_team_id, away_team_id}:
                continue

            seen.add(game_id)
            ids.append(game_id)
    return ids


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
    try:
        current_ids = _current_schedule_game_ids(season, timeout=timeout)
        if current_ids:
            return current_ids
    except Exception:
        pass

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


def get_team_season_game_ids(
    season: str,
    team_id: int,
    timeout: int = NBA_API_TIMEOUT,
) -> list[str]:
    """Return regular-season game IDs for one team.

    Uses the free official schedule feed for the active season, otherwise falls
    back to all season game IDs.
    """
    _rate_limit()
    try:
        ids = _current_team_schedule_game_ids(season, team_id, timeout=timeout)
        if ids:
            return ids
    except Exception:
        pass
    return get_season_game_ids(season, timeout=timeout)


def get_player_game_ids(
    player_id: int,
    season: str,
    candidate_game_ids: list[str] | None = None,
    prefer_candidate_scan: bool = False,
    timeout: int = NBA_API_TIMEOUT,
) -> list[str]:
    """Return regular-season game IDs for a player in a given season."""
    if prefer_candidate_scan and candidate_game_ids:
        fallback_ids: list[str] = []
        for game_id in candidate_game_ids:
            try:
                box_score = get_game_box_score(game_id, timeout=timeout)
            except Exception:
                continue
            if any(player.get("player_id") == player_id for player in box_score.get("players", [])):
                fallback_ids.append(game_id)
        if fallback_ids:
            return fallback_ids

    _rate_limit()
    try:
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
        if ids:
            return ids
    except Exception:
        pass

    game_ids = candidate_game_ids or get_season_game_ids(season, timeout=timeout)
    fallback_ids: list[str] = []
    for game_id in game_ids:
        try:
            box_score = get_game_box_score(game_id, timeout=timeout)
        except Exception:
            continue
        if any(player.get("player_id") == player_id for player in box_score.get("players", [])):
            fallback_ids.append(game_id)
    return fallback_ids


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


def get_team_stats(season: str) -> dict[str, dict]:
    """Fetch league-wide team stats for a season (both Base and Advanced measures).

    Returns a dict keyed by team abbreviation with merged Base + Advanced fields.
    """
    def _fetch(measure_type: str) -> list[dict]:
        _rate_limit()
        dash = leaguedashteamstats.LeagueDashTeamStats(
            season=season,
            measure_type_detailed_defense=measure_type,
            timeout=NBA_API_TIMEOUT,
        )
        return dash.get_normalized_dict().get("LeagueDashTeamStats", [])

    base_rows = _fetch("Base")
    advanced_rows = _fetch("Advanced")

    # Index advanced by team_id for O(1) merge
    adv_by_id: dict[int, dict] = {r["TEAM_ID"]: r for r in advanced_rows}

    result: dict[str, dict] = {}
    for row in base_rows:
        team_id = row["TEAM_ID"]
        abbr = str(row.get("TEAM_ABBREVIATION", "")).upper()
        adv = adv_by_id.get(team_id, {})
        gp = int(row.get("GP") or 0)
        result[abbr] = {
            "team_id": team_id,
            "abbreviation": abbr,
            "name": str(row.get("TEAM_NAME", "")),
            "season": season,
            "gp": gp,
            "w": int(row.get("W") or 0),
            "l": int(row.get("L") or 0),
            "w_pct": float(row.get("W_PCT") or 0.0),
            # Per-game scoring/playmaking (from Base, divide by GP)
            "pts_pg": round(float(row["PTS"]) / gp, 1) if gp else None,
            "ast_pg": round(float(row["AST"]) / gp, 1) if gp else None,
            "reb_pg": round(float(row["REB"]) / gp, 1) if gp else None,
            "tov_pg": round(float(row["TOV"]) / gp, 1) if gp else None,
            "blk_pg": round(float(row["BLK"]) / gp, 1) if gp else None,
            "stl_pg": round(float(row["STL"]) / gp, 1) if gp else None,
            "fg_pct": float(row["FG_PCT"]) if row.get("FG_PCT") is not None else None,
            "fg3_pct": float(row["FG3_PCT"]) if row.get("FG3_PCT") is not None else None,
            "ft_pct": float(row["FT_PCT"]) if row.get("FT_PCT") is not None else None,
            "plus_minus_pg": round(float(row["PLUS_MINUS"]) / gp, 1) if gp and row.get("PLUS_MINUS") is not None else None,
            # Advanced ratings
            "off_rating": float(adv["OFF_RATING"]) if adv.get("OFF_RATING") is not None else None,
            "def_rating": float(adv["DEF_RATING"]) if adv.get("DEF_RATING") is not None else None,
            "net_rating": float(adv["NET_RATING"]) if adv.get("NET_RATING") is not None else None,
            "pace": float(adv["PACE"]) if adv.get("PACE") is not None else None,
            "efg_pct": float(adv["EFG_PCT"]) if adv.get("EFG_PCT") is not None else None,
            "ts_pct": float(adv["TS_PCT"]) if adv.get("TS_PCT") is not None else None,
            "pie": float(adv["PIE"]) if adv.get("PIE") is not None else None,
            "oreb_pct": float(adv["OREB_PCT"]) if adv.get("OREB_PCT") is not None else None,
            "dreb_pct": float(adv["DREB_PCT"]) if adv.get("DREB_PCT") is not None else None,
            "tov_pct": float(adv["TM_TOV_PCT"]) if adv.get("TM_TOV_PCT") is not None else None,
            "ast_pct": float(adv["AST_PCT"]) if adv.get("AST_PCT") is not None else None,
            # League ranks (lower rank = better, except def_rating where lower is better too)
            "off_rating_rank": int(adv["OFF_RATING_RANK"]) if adv.get("OFF_RATING_RANK") is not None else None,
            "def_rating_rank": int(adv["DEF_RATING_RANK"]) if adv.get("DEF_RATING_RANK") is not None else None,
            "net_rating_rank": int(adv["NET_RATING_RANK"]) if adv.get("NET_RATING_RANK") is not None else None,
            "pace_rank": int(adv["PACE_RANK"]) if adv.get("PACE_RANK") is not None else None,
            "efg_pct_rank": int(adv["EFG_PCT_RANK"]) if adv.get("EFG_PCT_RANK") is not None else None,
            "ts_pct_rank": int(adv["TS_PCT_RANK"]) if adv.get("TS_PCT_RANK") is not None else None,
            "oreb_pct_rank": int(adv["OREB_PCT_RANK"]) if adv.get("OREB_PCT_RANK") is not None else None,
            "tov_pct_rank": int(adv["TM_TOV_PCT_RANK"]) if adv.get("TM_TOV_PCT_RANK") is not None else None,
        }
    return result


def get_standings_data(season: str) -> list[dict]:
    """Fetch league standings for a season.

    Returns one dict per team with keys: team_id, team_city, team_name,
    conference, division, playoff_rank, wins, losses, win_pct, games_back,
    l10, home_record, road_record, pts_pg, opp_pts_pg, diff_pts_pg,
    current_streak, clinch_indicator.
    """
    _rate_limit()
    standings = leaguestandings.LeagueStandings(
        season=season,
        timeout=NBA_API_TIMEOUT,
    )
    data = standings.get_normalized_dict()
    rows = data.get("Standings", [])

    def _sf(val) -> Optional[float]:
        try:
            return float(val) if val is not None else None
        except (ValueError, TypeError):
            return None

    result = []
    for row in rows:
        result.append({
            "team_id": int(row.get("TeamID") or 0),
            "team_city": str(row.get("TeamCity") or ""),
            "team_name": str(row.get("TeamName") or ""),
            "conference": str(row.get("Conference") or ""),
            "division": str(row.get("Division") or ""),
            "playoff_rank": int(row.get("PlayoffRank") or 0),
            "wins": int(row.get("WINS") or 0),
            "losses": int(row.get("LOSSES") or 0),
            "win_pct": _sf(row.get("WinPCT")) or 0.0,
            "games_back": _sf(row.get("ConferenceGamesBack")),
            "l10": str(row.get("L10") or ""),
            "home_record": str(row.get("Home") or ""),
            "road_record": str(row.get("Road") or ""),
            "pts_pg": _sf(row.get("PointsPG")),
            "opp_pts_pg": _sf(row.get("OppPointsPG")),
            "diff_pts_pg": _sf(row.get("DiffPointsPG")),
            "current_streak": str(row.get("strCurrentStreak") or ""),
            "clinch_indicator": str(row.get("ClinchIndicator") or "").strip() or None,
        })
    return result


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
