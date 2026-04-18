from __future__ import annotations

import json
import re
import time
from io import BytesIO
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import pandas as pd
from sqlalchemy.exc import IntegrityError
from nba_api.stats.endpoints import (
    boxscoretraditionalv2,
    commonplayerinfo,
    leaguedashplayerstats,
    leaguehustlestatsplayer,
    leaguedashteamstats,
    leaguegamelog,
    leaguestandings,
    playergamelog,
    playbyplayv3,
    playercareerstats,
    playerdashptpass,
    playerdashptshotdefend,
    playerdashptshots,
    shotchartdetail,
    synergyplaytypes,
    teamdashboardbygeneralsplits,
)
from nba_api.live.nba.endpoints import boxscore as live_boxscore
from nba_api.stats.static import players as static_players
from nba_api.stats.static import teams as static_teams

from config import NBA_API_DELAY, NBA_API_TIMEOUT
from data.cache import CacheManager
from db.database import SessionLocal
from db.models import ApiRequestState

_last_request_time = 0.0
_REQUEST_SOURCE = "nba_public"
NBA_LIVE_BASE_URL = "https://cdn.nba.com/static/json/liveData"
NBA_STATIC_BASE_URL = "https://cdn.nba.com/static/json/staticData"
NBA_MOBILE_BASE_URL = "https://data.nba.com/data/10s/v2015/json/mobile_teams/nba"
CURRENT_SEASON_CACHE_TTL = 6 * 3600
HISTORICAL_SEASON_CACHE_TTL = 30 * 24 * 3600
NBA_LIVE_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
}
OFFICIAL_NBA_INJURY_REPORT_URL = "https://official.nba.com/nba-injury-report-{season}-season/"
OFFICIAL_NBA_INJURY_REPORT_DEFAULT_URL = "https://official.nba.com/nba-injury-report/"
OFFICIAL_INJURY_REPORT_STATUSES = (
    "NOT YET SUBMITTED",
    "Questionable",
    "Doubtful",
    "Probable",
    "Available",
    "Out",
)
OFFICIAL_TEAM_NAMES = (
    "Atlanta Hawks",
    "Boston Celtics",
    "Brooklyn Nets",
    "Charlotte Hornets",
    "Chicago Bulls",
    "Cleveland Cavaliers",
    "Dallas Mavericks",
    "Denver Nuggets",
    "Detroit Pistons",
    "Golden State Warriors",
    "Houston Rockets",
    "Indiana Pacers",
    "LA Clippers",
    "Los Angeles Lakers",
    "Memphis Grizzlies",
    "Miami Heat",
    "Milwaukee Bucks",
    "Minnesota Timberwolves",
    "New Orleans Pelicans",
    "New York Knicks",
    "Oklahoma City Thunder",
    "Orlando Magic",
    "Philadelphia 76ers",
    "Phoenix Suns",
    "Portland Trail Blazers",
    "Sacramento Kings",
    "San Antonio Spurs",
    "Toronto Raptors",
    "Utah Jazz",
    "Washington Wizards",
)
OFFICIAL_TEAM_NAMES_BY_LENGTH = tuple(sorted(OFFICIAL_TEAM_NAMES, key=len, reverse=True))
OFFICIAL_TEAM_NAME_TOKENS = tuple(
    (team_name, tuple(team_name.split()))
    for team_name in sorted(OFFICIAL_TEAM_NAMES, key=lambda value: len(value.split()), reverse=True)
)
OFFICIAL_STATUS_TOKEN_SEQUENCES = (
    ("NOT YET SUBMITTED", ("NOT", "YET", "SUBMITTED")),
    ("Questionable", ("Questionable",)),
    ("Doubtful", ("Doubtful",)),
    ("Probable", ("Probable",)),
    ("Available", ("Available",)),
    ("Out", ("Out",)),
)
OFFICIAL_NAME_SUFFIXES = {"JR", "SR", "II", "III", "IV", "V"}
_STATIC_TEAMS_BY_ID = {int(team["id"]): team for team in static_teams.get_teams()}
_STATIC_TEAMS_BY_FULL_NAME = {
    str(team.get("full_name", "")).strip().lower(): team
    for team in static_teams.get_teams()
}


def _canonical_name(name: str) -> str:
    if not name:
        return ""
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return " ".join(normalized.lower().replace(".", "").split())


def _resolve_dashboard_team_identity(row: dict) -> tuple[str, str]:
    team_id = row.get("TEAM_ID")
    team_name = str(row.get("TEAM_NAME", "")).strip()
    abbreviation = str(row.get("TEAM_ABBREVIATION", "")).strip().upper()
    if abbreviation:
        return abbreviation, team_name

    static_team = None
    if team_id is not None:
        try:
            static_team = _STATIC_TEAMS_BY_ID.get(int(team_id))
        except (TypeError, ValueError):
            static_team = None
    if static_team is None and team_name:
        static_team = _STATIC_TEAMS_BY_FULL_NAME.get(team_name.lower())

    if static_team:
        return str(static_team.get("abbreviation", "")).upper(), str(static_team.get("full_name", team_name))
    return abbreviation, team_name


def _rate_limit():
    global _last_request_time

    wait_seconds = 0.0
    while True:
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            state = (
                db.query(ApiRequestState)
                .filter(ApiRequestState.source == _REQUEST_SOURCE)
                .with_for_update()
                .first()
            )
            if not state:
                state = ApiRequestState(source=_REQUEST_SOURCE, available_at=now)
                db.add(state)
                try:
                    db.flush()
                except IntegrityError:
                    db.rollback()
                    wait_seconds = NBA_API_DELAY
                    continue

            available_at = state.available_at or now
            if available_at > now:
                wait_seconds = max((available_at - now).total_seconds(), 0.05)
                db.rollback()
                continue

            state.last_request_at = now
            state.available_at = now + timedelta(seconds=NBA_API_DELAY)
            db.commit()
            _last_request_time = time.time()
            return
        finally:
            db.close()


def _active_nba_season() -> str:
    now = time.localtime()
    start_year = now.tm_year if now.tm_mon >= 8 else now.tm_year - 1
    return f"{start_year}-{str((start_year + 1) % 100).zfill(2)}"


def _cache_ttl_for_season(season: str) -> int:
    return CURRENT_SEASON_CACHE_TTL if season == _active_nba_season() else HISTORICAL_SEASON_CACHE_TTL


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


def _fetch_text(url: str, timeout: int = NBA_API_TIMEOUT) -> str:
    request = Request(url, headers=NBA_LIVE_HEADERS)
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", "ignore")
    except HTTPError as exc:
        raise RuntimeError(f"NBA text HTTP {exc.code} for {url}") from exc
    except URLError as exc:
        raise RuntimeError(f"NBA text network error for {url}: {exc.reason}") from exc


def _fetch_bytes(url: str, timeout: int = NBA_API_TIMEOUT) -> bytes:
    request = Request(url, headers=NBA_LIVE_HEADERS)
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except HTTPError as exc:
        raise RuntimeError(f"NBA bytes HTTP {exc.code} for {url}") from exc
    except URLError as exc:
        raise RuntimeError(f"NBA bytes network error for {url}: {exc.reason}") from exc


class _OfficialInjuryReportLinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: List[str] = []

    def handle_starttag(self, tag: str, attrs):
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(href)


def _official_injury_report_filename_dt(url: str) -> Optional[datetime]:
    match = re.search(
        r"Injury-Report_(\d{4}-\d{2}-\d{2})_(\d{2})_(\d{2})(AM|PM)\.pdf",
        url,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    date_part, hour, minute, meridiem = match.groups()
    return datetime.strptime(
        "{0} {1}:{2}{3}".format(date_part, hour, minute, meridiem.upper()),
        "%Y-%m-%d %I:%M%p",
    )


def _extract_latest_official_injury_report_pdf_url(html: str, page_url: str) -> str:
    parser = _OfficialInjuryReportLinkParser()
    parser.feed(html)

    candidates = []
    for href in parser.links:
        absolute_url = urljoin(page_url, href)
        if "Injury-Report_" not in absolute_url or not absolute_url.lower().endswith(".pdf"):
            continue
        report_dt = _official_injury_report_filename_dt(absolute_url)
        if report_dt:
            candidates.append((report_dt, absolute_url))

    if not candidates:
        raise RuntimeError("Official injury report page did not expose a report PDF link.")

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required for official injury report fallback parsing.") from exc

    reader = PdfReader(BytesIO(pdf_bytes))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _match_official_team_prefix(text: str) -> Tuple[Optional[str], str]:
    for team_name in OFFICIAL_TEAM_NAMES_BY_LENGTH:
        if text == team_name:
            return team_name, ""
        if text.startswith(team_name + " "):
            return team_name, text[len(team_name):].strip()
    return None, text


def _split_official_injury_reason(reason_text: str) -> Tuple[str, str, str]:
    cleaned = " ".join((reason_text or "").split()).strip(" -")
    if not cleaned:
        return "", "", ""
    if cleaned.startswith("Injury/Illness - "):
        cleaned = cleaned[len("Injury/Illness - "):].strip()

    if " - " in cleaned:
        injury_type, detail = cleaned.split(" - ", 1)
        return injury_type.strip(), detail.strip(), ""
    if ";" in cleaned:
        injury_type, detail = cleaned.split(";", 1)
        return injury_type.strip(), detail.strip(), ""
    return cleaned, cleaned, ""


def _join_pdf_tokens(tokens: List[str]) -> str:
    value = " ".join(token for token in tokens if token).strip()
    value = re.sub(r"(?<=\w)-\s+(?=\w)", "-", value)
    value = re.sub(r"\s+([,;:])", r"\1", value)
    return " ".join(value.split())


def _starts_with_token_sequence(tokens: List[str], start: int, expected: Tuple[str, ...]) -> bool:
    end = start + len(expected)
    if end > len(tokens):
        return False
    return tuple(tokens[start:end]) == expected


def _match_official_team_tokens(tokens: List[str], start: int) -> Tuple[Optional[str], int]:
    for team_name, team_tokens in OFFICIAL_TEAM_NAME_TOKENS:
        if _starts_with_token_sequence(tokens, start, team_tokens):
            return team_name, start + len(team_tokens)
    return None, start


def _match_status_tokens(tokens: List[str], start: int) -> Tuple[Optional[str], int]:
    for status_name, status_tokens in OFFICIAL_STATUS_TOKEN_SEQUENCES:
        if _starts_with_token_sequence(tokens, start, status_tokens):
            return status_name, start + len(status_tokens)
    return None, start


def _is_game_start(tokens: List[str], start: int) -> bool:
    if start + 2 < len(tokens):
        if (
            bool(re.match(r"^\d{2}:\d{2}$", tokens[start]))
            and tokens[start + 1] == "(ET)"
            and bool(re.match(r"^[A-Z]{2,4}@[A-Z]{2,4}$", tokens[start + 2]))
        ):
            return True
    if start + 3 < len(tokens):
        if (
            bool(re.match(r"^\d{2}/\d{2}/\d{4}$", tokens[start]))
            and bool(re.match(r"^\d{2}:\d{2}$", tokens[start + 1]))
            and tokens[start + 2] == "(ET)"
            and bool(re.match(r"^[A-Z]{2,4}@[A-Z]{2,4}$", tokens[start + 3]))
        ):
            return True
    return False


def _game_start_token_count(tokens: List[str], start: int) -> int:
    if start + 2 < len(tokens) and (
        bool(re.match(r"^\d{2}:\d{2}$", tokens[start]))
        and tokens[start + 1] == "(ET)"
        and bool(re.match(r"^[A-Z]{2,4}@[A-Z]{2,4}$", tokens[start + 2]))
    ):
        return 3
    if start + 3 < len(tokens) and (
        bool(re.match(r"^\d{2}/\d{2}/\d{4}$", tokens[start]))
        and bool(re.match(r"^\d{2}:\d{2}$", tokens[start + 1]))
        and tokens[start + 2] == "(ET)"
        and bool(re.match(r"^[A-Z]{2,4}@[A-Z]{2,4}$", tokens[start + 3]))
    ):
        return 4
    return 0


def _is_matchup_token(token: str) -> bool:
    return bool(re.match(r"^[A-Z]{2,4}@[A-Z]{2,4}$", token))


def _looks_like_player_row(tokens: List[str], start: int) -> bool:
    for offset in range(1, 5):
        status_index = start + offset
        status_name, _ = _match_status_tokens(tokens, status_index)
        if not status_name:
            continue
        candidate_tokens = tokens[start:status_index]
        if not candidate_tokens or len(candidate_tokens) > 3:
            return False
        first_token = candidate_tokens[0]
        if "-" in first_token and not first_token.endswith("-") and "," not in first_token:
            return False
        if "," in first_token:
            return True
        if len(candidate_tokens) >= 2:
            second_token = candidate_tokens[1]
            normalized_second = re.sub(r"[^A-Za-z0-9]", "", second_token).upper()
            if first_token.endswith("-") and "," in second_token:
                return True
            if normalized_second in OFFICIAL_NAME_SUFFIXES and "," in second_token:
                return True
        return False
    return False


def _parse_official_injury_report_text(text: str, report_dt: datetime) -> dict:
    tokens = [
        token
        for token in text.replace("\xa0", " ").split()
        if token not in {"Injury", "Report:", "Page", "of", "Game", "Date", "Time", "Matchup", "Team", "Player", "Name", "Current", "Status", "Reason"}
        and not re.match(r"^\d{2}/\d{2}/\d{2}$", token)
        and not re.match(r"^\d+$", token)
        and token not in {"AM", "PM"}
    ]
    entries = []
    current_team: Optional[str] = None
    current_team_abbreviation: Optional[str] = None
    current_matchup_abbreviations: Tuple[Optional[str], Optional[str]] = (None, None)
    current_matchup_teams: dict = {}
    index = 0
    while index < len(tokens):
        game_start_token_count = _game_start_token_count(tokens, index)
        if game_start_token_count:
            matchup_token = tokens[index + game_start_token_count - 1]
            away_abbreviation, home_abbreviation = matchup_token.split("@", 1)
            current_matchup_abbreviations = (away_abbreviation, home_abbreviation)
            current_matchup_teams = {}
            current_team = None
            current_team_abbreviation = None
            index += game_start_token_count
            continue
        if _is_matchup_token(tokens[index]):
            away_abbreviation, home_abbreviation = tokens[index].split("@", 1)
            current_matchup_abbreviations = (away_abbreviation, home_abbreviation)
            current_matchup_teams = {}
            current_team = None
            current_team_abbreviation = None
            index += 1
            continue

        team_name, next_index = _match_official_team_tokens(tokens, index)
        if team_name:
            current_team = team_name
            if team_name not in current_matchup_teams:
                if not current_matchup_teams and current_matchup_abbreviations[0]:
                    current_matchup_teams[team_name] = current_matchup_abbreviations[0]
                elif current_matchup_abbreviations[1]:
                    current_matchup_teams[team_name] = current_matchup_abbreviations[1]
            current_team_abbreviation = current_matchup_teams.get(team_name)
            index = next_index
            continue

        if not current_team:
            index += 1
            continue

        status_name = None
        status_index = index
        while status_index < len(tokens):
            if _game_start_token_count(tokens, status_index) or _is_matchup_token(tokens[status_index]):
                break
            next_team_name, _ = _match_official_team_tokens(tokens, status_index)
            if next_team_name and status_index != index:
                break
            status_name, status_end = _match_status_tokens(tokens, status_index)
            if status_name:
                break
            status_index += 1

        if not status_name:
            index += 1
            continue

        player_tokens = tokens[index:status_index]
        player_name = _join_pdf_tokens(player_tokens)
        if not player_name:
            index = status_end
            continue

        reason_index = status_end
        reason_tokens: List[str] = []
        while reason_index < len(tokens):
            if _game_start_token_count(tokens, reason_index) or _is_matchup_token(tokens[reason_index]):
                break
            next_team_name, _ = _match_official_team_tokens(tokens, reason_index)
            if next_team_name:
                break
            if _looks_like_player_row(tokens, reason_index):
                break
            reason_tokens.append(tokens[reason_index])
            reason_index += 1

        reason_text = _join_pdf_tokens(reason_tokens)
        injury_type, detail, comment = _split_official_injury_reason(reason_text)
        entries.append(
            {
                "Team": current_team,
                "TeamAbbreviation": current_team_abbreviation,
                "PlayerName": player_name,
                "Status": status_name,
                "Injury": injury_type,
                "Detail": detail,
                "Comment": comment,
                "Return": "",
            }
        )
        index = reason_index

    return {
        "date": report_dt.strftime("%Y-%m-%dT%H:%M:%S"),
        "InjuryList": entries,
    }


def _fetch_official_injury_report_payload(
    season: Optional[str],
    timeout: int = NBA_API_TIMEOUT,
    fallback_reason: Optional[str] = None,
) -> dict:
    season_value = season or _active_nba_season()
    page_url = OFFICIAL_NBA_INJURY_REPORT_URL.format(season=season_value)
    try:
        html = _fetch_text(page_url, timeout=timeout)
    except RuntimeError:
        page_url = OFFICIAL_NBA_INJURY_REPORT_DEFAULT_URL
        html = _fetch_text(page_url, timeout=timeout)

    pdf_url = _extract_latest_official_injury_report_pdf_url(html, page_url)
    report_dt = _official_injury_report_filename_dt(pdf_url) or datetime.utcnow()
    pdf_bytes = _fetch_bytes(pdf_url, timeout=timeout)
    pdf_text = _extract_pdf_text(pdf_bytes)

    return {
        "source": "official.nba.com/injury-report-pdf",
        "source_url": pdf_url,
        "fallback_reason": fallback_reason,
        "payload": _parse_official_injury_report_text(pdf_text, report_dt),
    }


def _fetch_live_json(path: str, timeout: int = NBA_API_TIMEOUT) -> dict:
    """Fetch raw JSON from NBA's public live-data CDN."""
    return _fetch_nba_json(NBA_LIVE_BASE_URL, path, timeout=timeout)


def _fetch_static_json(path: str, timeout: int = NBA_API_TIMEOUT) -> dict:
    """Fetch raw JSON from NBA's public static-data CDN."""
    return _fetch_nba_json(NBA_STATIC_BASE_URL, path, timeout=timeout)


def get_schedule_payload_for_season(season: str, timeout: int = NBA_API_TIMEOUT) -> dict:
    """Return raw season schedule payload plus source metadata.

    Prefers the current official static schedule feed, then the historical
    mobile schedule feed. This function is intended for ingestion/storage, not
    direct API reads.
    """
    season_start_year = season.split("-")[0] if "-" in season else season

    _rate_limit()
    try:
        payload = _fetch_static_json("scheduleLeagueV2.json", timeout=timeout)
        league_schedule = payload.get("leagueSchedule", {})
        season_year = str(league_schedule.get("seasonYear") or "")
        if season_year in {season, season_start_year}:
            return {"source": "cdn_schedule", "payload": payload}
    except Exception:
        pass

    year = season_start_year
    url = f"{NBA_MOBILE_BASE_URL}/{year}/league/00_full_schedule.json"
    request = Request(url, headers=NBA_LIVE_HEADERS)
    _rate_limit()
    with urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    return {"source": "mobile_schedule", "payload": payload}


def get_injuries_payload(timeout: int = NBA_API_TIMEOUT, season: Optional[str] = None) -> dict:
    """Fetch the current league-wide injury report from the NBA CDN.

    Returns the raw payload dict. The caller is responsible for parsing
    and persisting the results. No rate limiting applied — injuries endpoint
    is a single lightweight JSON document, not a per-entity call.
    """
    try:
        return _fetch_live_json("injuries/injuries.json", timeout=timeout)
    except RuntimeError as exc:
        return _fetch_official_injury_report_payload(
            season=season,
            timeout=timeout,
            fallback_reason=str(exc),
        )


def get_game_box_score_payload(game_id: str, timeout: int = NBA_API_TIMEOUT) -> dict:
    """Fetch the raw live box score payload for a game."""
    _rate_limit()
    return _fetch_live_json(f"boxscore/boxscore_{game_id}.json", timeout=timeout)


def get_play_by_play_payload(game_id: str, timeout: int = NBA_API_TIMEOUT) -> dict:
    """Fetch the raw live play-by-play payload for a game."""
    _rate_limit()
    return _fetch_live_json(f"playbyplay/playbyplay_{game_id}.json", timeout=timeout)


def _current_schedule_game_ids(season: str, timeout: int = NBA_API_TIMEOUT) -> list[str]:
    """Return current-season regular-season game IDs from the free NBA schedule feed."""
    payload = _fetch_static_json("scheduleLeagueV2.json", timeout=timeout)
    league_schedule = payload.get("leagueSchedule", {})
    season_year = str(league_schedule.get("seasonYear") or "")
    # CDN returns start year (e.g. "2025") while app uses "2025-26" format
    season_start_year = season.split("-")[0] if "-" in season else season
    if season_year != season and season_year != season_start_year:
        return []

    ids: list[str] = []
    seen: set[str] = set()
    for game_date in league_schedule.get("gameDates", []):
        for game in game_date.get("games", []):
            game_id = str(game.get("gameId") or "")
            if not game_id or game_id in seen:
                continue
            if int(game.get("gameStatus") or 0) < 2:
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
    season_start_year = season.split("-")[0] if "-" in season else season
    if season_year != season and season_year != season_start_year:
        return []

    ids: list[str] = []
    seen: set[str] = set()
    team_id_str = str(team_id)
    for game_date in league_schedule.get("gameDates", []):
        for game in game_date.get("games", []):
            game_id = str(game.get("gameId") or "")
            if not game_id or game_id in seen or not game_id.startswith("002"):
                continue
            if int(game.get("gameStatus") or 0) < 2:
                continue

            home_team_id = str(game.get("homeTeam", {}).get("teamId") or "")
            away_team_id = str(game.get("awayTeam", {}).get("teamId") or "")
            if team_id_str not in {home_team_id, away_team_id}:
                continue

            seen.add(game_id)
            ids.append(game_id)
    return ids


def _historical_schedule_game_ids(season: str, timeout: int = NBA_API_TIMEOUT) -> list[str]:
    """Return regular-season game IDs for a historical season from data.nba.com mobile feed.

    Uses data.nba.com/data/10s/v2015/json/mobile_teams/nba/{year}/league/00_full_schedule.json
    which is available for all seasons and does not hit stats.nba.com.
    """
    year = season.split("-")[0]  # "2023-24" -> "2023"
    url = f"{NBA_MOBILE_BASE_URL}/{year}/league/00_full_schedule.json"
    request = Request(url, headers=NBA_LIVE_HEADERS)
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except Exception as exc:
        raise RuntimeError(f"Historical schedule fetch failed for {season}: {exc}") from exc

    ids: list[str] = []
    seen: set[str] = set()
    for month in payload.get("lscd", []):
        for game in month.get("mscd", {}).get("g", []):
            game_id = str(game.get("gid") or "")
            # Regular season game IDs start with "002"
            if game_id and game_id not in seen and game_id.startswith("002"):
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


def _parse_cdn_minutes(minutes_str: str) -> float:
    """Parse CDN minutes format 'PT15M12.00S' into decimal minutes."""
    if not minutes_str or not minutes_str.startswith("PT"):
        return 0.0
    try:
        rest = minutes_str[2:]  # strip "PT"
        mins = 0.0
        secs = 0.0
        if "M" in rest:
            m_part, rest = rest.split("M", 1)
            mins = float(m_part)
        if "S" in rest:
            secs = float(rest.replace("S", ""))
        return round(mins + secs / 60.0, 1)
    except (ValueError, TypeError):
        return 0.0


def get_game_box_score_detailed(game_id: str, timeout: int = NBA_API_TIMEOUT) -> dict:
    """Fetch full box score from CDN with per-player stats.

    Returns the standard box score shape plus detailed per-player stats
    (pts, reb, ast, stl, blk, tov, fgm, fga, fg3m, fg3a, ftm, fta, etc.).
    Uses only the CDN endpoint — does not hit stats.nba.com.
    """
    _rate_limit()
    payload = _fetch_live_json(f"boxscore/boxscore_{game_id}.json", timeout=timeout)
    game = payload.get("game", payload)
    home_team = game.get("homeTeam", {})
    away_team = game.get("awayTeam", {})
    game_date = game.get("gameTimeUTC", "")[:10] or None  # "2025-10-22T..."

    players = []
    for team in [home_team, away_team]:
        team_id = team.get("teamId")
        team_tricode = team.get("teamTricode", "")
        for p in team.get("players", []):
            stats = p.get("statistics", {})
            minutes = _parse_cdn_minutes(stats.get("minutes", ""))
            players.append({
                "player_id": p.get("personId"),
                "player_name": p.get("name", ""),
                "team_id": team_id,
                "team_abbreviation": team_tricode,
                "start_position": p.get("position", "") if p.get("starter") == "1" else "",
                "min": minutes,
                "pts": int(stats.get("points") or 0),
                "reb": int(stats.get("reboundsTotal") or 0),
                "ast": int(stats.get("assists") or 0),
                "stl": int(stats.get("steals") or 0),
                "blk": int(stats.get("blocks") or 0),
                "tov": int(stats.get("turnovers") or 0),
                "fgm": int(stats.get("fieldGoalsMade") or 0),
                "fga": int(stats.get("fieldGoalsAttempted") or 0),
                "fg3m": int(stats.get("threePointersMade") or 0),
                "fg3a": int(stats.get("threePointersAttempted") or 0),
                "ftm": int(stats.get("freeThrowsMade") or 0),
                "fta": int(stats.get("freeThrowsAttempted") or 0),
                "oreb": int(stats.get("reboundsOffensive") or 0),
                "dreb": int(stats.get("reboundsDefensive") or 0),
                "pf": int(stats.get("foulsPersonal") or 0),
                "plus_minus": float(stats.get("plusMinusPoints") or 0),
            })

    home_tricode = home_team.get("teamTricode", "")
    away_tricode = away_team.get("teamTricode", "")
    matchup_home = f"{home_tricode} vs. {away_tricode}"
    matchup_away = f"{away_tricode} @ {home_tricode}"
    home_score = int(home_team.get("score") or 0)
    away_score = int(away_team.get("score") or 0)
    home_won = home_score > away_score

    return {
        "game_id": game_id,
        "game_date": game_date,
        "home_team_id": home_team.get("teamId"),
        "away_team_id": away_team.get("teamId"),
        "home_team_abbreviation": home_tricode,
        "away_team_abbreviation": away_tricode,
        "home_team_name": home_team.get("teamName", ""),
        "away_team_name": away_team.get("teamName", ""),
        "home_score": home_score,
        "away_score": away_score,
        "matchup_home": matchup_home,
        "matchup_away": matchup_away,
        "home_won": home_won,
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
    season: str, measure_type: str = "Advanced", timeout: int = NBA_API_TIMEOUT
) -> list[dict]:
    """Fetch league-wide player stats for a given season.

    measure_type: 'Base' for traditional, 'Advanced' for advanced metrics.
    """
    _rate_limit()
    dash = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        measure_type_detailed_defense=measure_type,
        timeout=timeout,
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
    cache_key = f"season_game_ids:{season}"
    cached = CacheManager.get(cache_key)
    if cached and isinstance(cached.get("ids"), list):
        return [str(game_id) for game_id in cached["ids"]]

    _rate_limit()
    try:
        current_ids = _current_schedule_game_ids(season, timeout=timeout)
        if current_ids:
            CacheManager.set(
                cache_key,
                {"ids": current_ids, "source": "schedule"},
                _cache_ttl_for_season(season),
            )
            return current_ids
    except Exception:
        pass

    # Try data.nba.com mobile schedule (works for all historical seasons, no IP blocking)
    _rate_limit()
    try:
        hist_ids = _historical_schedule_game_ids(season, timeout=timeout)
        if hist_ids:
            CacheManager.set(
                cache_key,
                {"ids": hist_ids, "source": "mobile_schedule"},
                _cache_ttl_for_season(season),
            )
            return hist_ids
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
    CacheManager.set(
        cache_key,
        {"ids": ids, "source": "leaguegamelog"},
        _cache_ttl_for_season(season),
    )
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
    cache_key = f"team_game_ids:{season}:{team_id}"
    cached = CacheManager.get(cache_key)
    if cached and isinstance(cached.get("ids"), list):
        return [str(game_id) for game_id in cached["ids"]]

    _rate_limit()
    try:
        ids = _current_team_schedule_game_ids(season, team_id, timeout=timeout)
        if ids:
            CacheManager.set(
                cache_key,
                {"ids": ids, "source": "schedule"},
                _cache_ttl_for_season(season),
            )
            return ids
    except Exception:
        pass
    ids = get_season_game_ids(season, timeout=timeout)
    CacheManager.set(
        cache_key,
        {"ids": ids, "source": "season_fallback"},
        _cache_ttl_for_season(season),
    )
    return ids


def get_player_game_ids(
    player_id: int,
    season: str,
    candidate_game_ids: list[str] | None = None,
    prefer_candidate_scan: bool = False,
    timeout: int = NBA_API_TIMEOUT,
) -> list[str]:
    """Return regular-season game IDs for a player in a given season."""
    cache_key = f"player_game_ids:{player_id}:{season}"
    cached = CacheManager.get(cache_key)
    if cached and isinstance(cached.get("ids"), list):
        return [str(game_id) for game_id in cached["ids"]]

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
            CacheManager.set(
                cache_key,
                {"ids": fallback_ids, "source": "candidate_scan"},
                _cache_ttl_for_season(season),
            )
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
            CacheManager.set(
                cache_key,
                {"ids": ids, "source": "playergamelog"},
                _cache_ttl_for_season(season),
            )
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
    CacheManager.set(
        cache_key,
        {"ids": fallback_ids, "source": "season_scan"},
        _cache_ttl_for_season(season),
    )
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
        abbr, team_name = _resolve_dashboard_team_identity(row)
        adv = adv_by_id.get(team_id, {})
        if not abbr:
            continue
        gp = int(row.get("GP") or 0)
        result[abbr] = {
            "team_id": team_id,
            "abbreviation": abbr,
            "name": team_name,
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


TEAM_GENERAL_SPLIT_DATASETS = (
    "LocationTeamDashboard",
    "WinsLossesTeamDashboard",
    "DaysRestTeamDashboard",
    "MonthTeamDashboard",
    "PrePostAllStarTeamDashboard",
)

TEAM_GENERAL_SPLIT_LABEL_FIELDS = {
    "LocationTeamDashboard": "TEAM_GAME_LOCATION",
    "WinsLossesTeamDashboard": "GAME_RESULT",
    "DaysRestTeamDashboard": "TEAM_DAYS_REST_RANGE",
    "MonthTeamDashboard": "SEASON_MONTH_NAME",
    "PrePostAllStarTeamDashboard": "SEASON_SEGMENT",
}


def _safe_float(value) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _safe_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _team_general_split_row(dataset_name: str, row: dict, season: str, team_id: int) -> Optional[dict]:
    label_field = TEAM_GENERAL_SPLIT_LABEL_FIELDS.get(dataset_name)
    raw_label = row.get(label_field) if label_field else None
    label = str(raw_label or row.get("GROUP_VALUE") or "").strip()
    if not label:
        return None

    return {
        "team_id": int(team_id),
        "season": season,
        "is_playoff": False,
        "split_family": dataset_name,
        "split_value": label,
        "label": label,
        "gp": _safe_int(row.get("GP")),
        "w": _safe_int(row.get("W")),
        "l": _safe_int(row.get("L")),
        "w_pct": _safe_float(row.get("W_PCT")) or 0.0,
        "min": _safe_float(row.get("MIN")),
        "pts": _safe_float(row.get("PTS")),
        "reb": _safe_float(row.get("REB")),
        "ast": _safe_float(row.get("AST")),
        "tov": _safe_float(row.get("TOV")),
        "stl": _safe_float(row.get("STL")),
        "blk": _safe_float(row.get("BLK")),
        "fg_pct": _safe_float(row.get("FG_PCT")),
        "fg3_pct": _safe_float(row.get("FG3_PCT")),
        "ft_pct": _safe_float(row.get("FT_PCT")),
        "plus_minus": _safe_float(row.get("PLUS_MINUS")),
        "source": "stats.nba.com/team-general-splits",
    }


def get_team_general_splits(season: str, team_id: int) -> list[dict]:
    """Fetch official team general splits for one team and season."""
    _rate_limit()
    dash = teamdashboardbygeneralsplits.TeamDashboardByGeneralSplits(
        team_id=team_id,
        season=season,
        per_mode_detailed="Totals",
        season_type_all_star="Regular Season",
        timeout=NBA_API_TIMEOUT,
    )
    data = dash.get_normalized_dict()
    splits: list[dict] = []
    for dataset_name in TEAM_GENERAL_SPLIT_DATASETS:
        for row in data.get(dataset_name, []):
            normalized = _team_general_split_row(dataset_name, row, season, team_id)
            if normalized:
                splits.append(normalized)
    return splits


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
    action_type, zone_basic, zone_area, distance, game_id, game_date,
    period, clock, minutes_remaining, seconds_remaining, shot_value,
    and shot_event_id when available.

    Results are cached in SQLite; historical seasons are cached indefinitely,
    current season for CURRENT_SEASON_CACHE_TTL seconds.
    """
    cache_key = f"shotchart_{player_id}_{season}_{season_type}"
    cached = CacheManager.get(cache_key)
    if cached and isinstance(cached.get("shots"), list):
        return cached["shots"]

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
        raw_game_date = row.get("GAME_DATE")
        minutes_remaining = row.get("MINUTES_REMAINING")
        seconds_remaining = row.get("SECONDS_REMAINING")
        shot_type = str(row.get("SHOT_TYPE", ""))
        shot_value = 3 if "3PT" in shot_type.upper() else 2
        shots.append({
            "loc_x": int(row.get("LOC_X", 0)),
            "loc_y": int(row.get("LOC_Y", 0)),
            "shot_made": bool(row.get("SHOT_MADE_FLAG", 0)),
            "shot_type": shot_type,
            "action_type": str(row.get("ACTION_TYPE", "")),
            "zone_basic": str(row.get("SHOT_ZONE_BASIC", "")),
            "zone_area": str(row.get("SHOT_ZONE_AREA", "")),
            "distance": int(row.get("SHOT_DISTANCE", 0)),
            "game_id": str(row.get("GAME_ID") or "") or None,
            "game_date": _normalize_shot_chart_game_date(raw_game_date),
            "period": int(row.get("PERIOD")) if row.get("PERIOD") is not None else None,
            "clock": _format_shot_clock(minutes_remaining, seconds_remaining),
            "minutes_remaining": int(minutes_remaining) if minutes_remaining is not None else None,
            "seconds_remaining": int(seconds_remaining) if seconds_remaining is not None else None,
            "shot_value": shot_value,
            "shot_event_id": str(row.get("GAME_EVENT_ID") or "") or None,
        })
    CacheManager.set(cache_key, {"shots": shots}, _cache_ttl_for_season(season))
    return shots


def _df_records(frame) -> List[Dict[str, Any]]:
    if frame is None or frame.empty:
        return []
    return frame.where(pd.notnull(frame), None).to_dict("records")


def get_synergy_player_play_types(
    season: str,
    season_type: str = "Regular Season",
    play_type: str = "",
    type_grouping: str = "offensive",
) -> List[Dict[str, Any]]:
    """Fetch official Synergy play-type rows when stats.nba.com exposes them."""
    cache_key = f"synergy_player_play_types_{season}_{season_type}_{play_type}_{type_grouping}"
    cached = CacheManager.get(cache_key)
    if cached and isinstance(cached.get("rows"), list):
        return cached["rows"]

    _rate_limit()
    response = synergyplaytypes.SynergyPlayTypes(
        season=season,
        season_type_all_star=season_type,
        player_or_team_abbreviation="P",
        play_type_nullable=play_type,
        type_grouping_nullable=type_grouping,
        per_mode_simple="Totals",
        timeout=NBA_API_TIMEOUT,
    )
    frames = response.get_data_frames()
    rows = _df_records(frames[0] if frames else None)
    CacheManager.set(cache_key, {"rows": rows}, _cache_ttl_for_season(season))
    return rows


def get_league_hustle_player_stats(
    season: str,
    season_type: str = "Regular Season",
) -> List[Dict[str, Any]]:
    """Fetch official league player hustle rows."""
    cache_key = f"league_hustle_player_{season}_{season_type}"
    cached = CacheManager.get(cache_key)
    if cached and isinstance(cached.get("rows"), list):
        return cached["rows"]

    _rate_limit()
    response = leaguehustlestatsplayer.LeagueHustleStatsPlayer(
        season=season,
        season_type_all_star=season_type,
        per_mode_time="Totals",
        timeout=NBA_API_TIMEOUT,
    )
    frames = response.get_data_frames()
    rows = _df_records(frames[0] if frames else None)
    CacheManager.set(cache_key, {"rows": rows}, _cache_ttl_for_season(season))
    return rows


def get_player_tracking_dashboard(
    player_id: int,
    season: str,
    season_type: str = "Regular Season",
) -> List[Dict[str, Any]]:
    """Fetch selected player-tracking dashboards for one player.

    The result is intentionally normalized into family/split rows so callers
    can persist partial endpoint coverage without changing product contracts.
    """
    cache_key = f"player_tracking_dashboard_{player_id}_{season}_{season_type}"
    cached = CacheManager.get(cache_key)
    if cached and isinstance(cached.get("rows"), list):
        return cached["rows"]

    rows: List[Dict[str, Any]] = []

    def _collect(family: str, endpoint) -> None:
        frames = endpoint.get_data_frames()
        for dataset_name, frame in zip(endpoint.expected_data.keys(), frames):
            for record in _df_records(frame):
                split = (
                    record.get("SHOT_TYPE")
                    or record.get("DRIBBLE_RANGE")
                    or record.get("TOUCH_TIME_RANGE")
                    or record.get("CLOSE_DEF_DIST_RANGE")
                    or record.get("PASS_TYPE")
                    or record.get("DEFENSE_CATEGORY")
                    or dataset_name
                    or "overall"
                )
                rows.append({
                    "family": family,
                    "split_key": str(split),
                    "dataset": dataset_name,
                    "raw": record,
                })

    _rate_limit()
    _collect(
        "shots",
        playerdashptshots.PlayerDashPtShots(
            team_id=0,
            player_id=player_id,
            season=season,
            season_type_all_star=season_type,
            per_mode_simple="Totals",
            timeout=NBA_API_TIMEOUT,
        ),
    )
    _rate_limit()
    _collect(
        "passing",
        playerdashptpass.PlayerDashPtPass(
            team_id=0,
            player_id=player_id,
            season=season,
            season_type_all_star=season_type,
            per_mode_simple="Totals",
            timeout=NBA_API_TIMEOUT,
        ),
    )
    _rate_limit()
    _collect(
        "shot_defense",
        playerdashptshotdefend.PlayerDashPtShotDefend(
            team_id=0,
            player_id=player_id,
            season=season,
            season_type_all_star=season_type,
            per_mode_simple="Totals",
            timeout=NBA_API_TIMEOUT,
        ),
    )
    CacheManager.set(cache_key, {"rows": rows}, _cache_ttl_for_season(season))
    return rows


def get_inside_game_gravity_rows(
    season: str,
    season_type: str = "Regular Season",
) -> List[Dict[str, Any]]:
    """Best-effort source spike for NBA Inside the Game Gravity.

    NBA currently renders Gravity through the Inside the Game web app. This
    function only returns rows if a stable structured payload is discoverable;
    callers must treat an empty result as "official source unavailable" and
    fall back to CourtVue proxy persistence.
    """
    cache_key = f"inside_game_gravity_{season}_{season_type}"
    cached = CacheManager.get(cache_key)
    if cached and isinstance(cached.get("rows"), list):
        return cached["rows"]

    url = "https://www.nba.com/inside-the-game/player/gravity"
    request = Request(url, headers=NBA_LIVE_HEADERS)
    try:
        with urlopen(request, timeout=NBA_API_TIMEOUT) as response:
            html = response.read().decode("utf-8", errors="ignore")
    except (HTTPError, URLError, TimeoutError):
        CacheManager.set(cache_key, {"rows": []}, 1800)
        return []

    rows: List[Dict[str, Any]] = []
    for match in re.finditer(r'"playerId"\s*:\s*(\d+).*?"gravity"\s*:\s*(-?\d+(?:\.\d+)?)', html, flags=re.IGNORECASE | re.DOTALL):
        rows.append({"PLAYER_ID": int(match.group(1)), "GRAV": float(match.group(2)), "raw": match.group(0)})

    CacheManager.set(cache_key, {"rows": rows}, 1800 if not rows else _cache_ttl_for_season(season))
    return rows


def _format_shot_clock(raw_minutes: object, raw_seconds: object) -> Optional[str]:
    if raw_minutes is None or raw_seconds is None:
        return None
    try:
        minutes = int(raw_minutes)
        seconds = int(raw_seconds)
    except (TypeError, ValueError):
        return None
    return "{0}:{1:02d}".format(minutes, seconds)


def _normalize_shot_chart_game_date(raw_value: object) -> Optional[str]:
    if raw_value is None:
        return None

    value = str(raw_value).strip()
    if not value:
        return None

    normalized = value.replace("T00:00:00", "")
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y%m%d", "%b %d, %Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(normalized, fmt).date().isoformat()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(normalized.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        pass

    try:
        return date.fromisoformat(normalized[:10]).isoformat()
    except ValueError:
        return None
