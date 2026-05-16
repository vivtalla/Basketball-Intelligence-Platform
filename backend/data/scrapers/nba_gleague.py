"""Sprint 100 (Stream B) — NBA G League player stats scraper.

The G League uses the same NBA Stats endpoint as the main league, with
``LeagueID=20`` instead of ``00``:

    https://stats.nba.com/stats/leaguedashplayerstats
        ?LeagueID=20&Season={SEASON}&SeasonType=Regular+Season
        &PerMode=PerGame&MeasureType=Base

We pull per-game averages for the full season and filter to young players
(<=23) on the ingest side. The JSON shape matches the main NBA Stats
playerdash endpoint; we reuse the headers + rate-limit pattern from
``nba_combine.py``.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from data.scrapers._base import HttpScraper, ScraperError

logger = logging.getLogger(__name__)

# G League is LeagueID=20 in NBA Stats API.
LEAGUE_ID = "20"


def _to_float(raw: Any) -> Optional[float]:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _to_int(raw: Any) -> Optional[int]:
    f = _to_float(raw)
    if f is None:
        return None
    return int(f)


def _normalize_name(name: str) -> str:
    s = (name or "").strip()
    s = re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


class NBAGLeagueScraper(HttpScraper):
    """Fetches G League per-player season averages."""

    BASE_URL = "https://stats.nba.com"
    DELAY_SECONDS = 1.5
    FIXTURE_PREFIX = "nba_gleague"

    def _headers(self) -> Dict[str, str]:
        base = super()._headers()
        base.update({
            "Referer": "https://www.nba.com/",
            "Origin": "https://www.nba.com",
            "Accept": "application/json, text/plain, */*",
            "x-nba-stats-origin": "stats",
            "x-nba-stats-token": "true",
        })
        return base

    def fetch_season(
        self,
        season_end_year: int,
        fixture_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Pull G League per-game averages for ``season_end_year`` (e.g. 2026 = 2025-26).

        Returns rows annotated with ``source_url`` + ``league=G League``.
        """
        season = "{0}-{1}".format(season_end_year - 1, str(season_end_year)[-2:])
        params = {
            "LeagueID": LEAGUE_ID,
            "Season": season,
            "SeasonType": "Regular Season",
            "PerMode": "PerGame",
            "MeasureType": "Base",
            "PaceAdjust": "N",
            "PlusMinus": "N",
            "Rank": "N",
            "Outcome": "",
            "Location": "",
            "Month": "0",
            "SeasonSegment": "",
            "DateFrom": "",
            "DateTo": "",
            "OpponentTeamID": "0",
            "VsConference": "",
            "VsDivision": "",
            "GameSegment": "",
            "Period": "0",
            "ShotClockRange": "",
            "LastNGames": "0",
            "TeamID": "0",
            "Conference": "",
            "Division": "",
            "GameScope": "",
            "PlayerExperience": "",
            "PlayerPosition": "",
            "StarterBench": "",
            "DraftYear": "",
            "DraftPick": "",
            "College": "",
            "Country": "",
            "Height": "",
            "Weight": "",
        }
        body = self.get(
            "/stats/leaguedashplayerstats",
            params=params,
            fixture_name=fixture_name,
        )
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ScraperError("nba_gleague: response not JSON: {0}".format(exc))

        result_sets = payload.get("resultSets") or []
        if not result_sets:
            raise ScraperError("nba_gleague: empty resultSets")
        rs = result_sets[0]
        headers = rs.get("headers") or []
        rows = rs.get("rowSet") or []
        if not rows:
            raise ScraperError(
                "nba_gleague: 0 rows for season={0}".format(season)
            )

        idx = {h: i for i, h in enumerate(headers)}

        def cell(row: list, key: str) -> Any:
            i = idx.get(key)
            if i is None or i >= len(row):
                return None
            return row[i]

        out: List[Dict[str, Any]] = []
        for row in rows:
            name = cell(row, "PLAYER_NAME")
            if not name:
                continue
            out.append({
                "player": name,
                "normalized_name": _normalize_name(name),
                "nba_player_id": _to_int(cell(row, "PLAYER_ID")),
                "team_name": cell(row, "TEAM_ABBREVIATION") or cell(row, "TEAM_NAME"),
                "season_end_year": season_end_year,
                "league": "G League",
                "games": _to_int(cell(row, "GP")),
                "minutes_per_game": _to_float(cell(row, "MIN")),
                "ppg": _to_float(cell(row, "PTS")),
                "rpg": _to_float(cell(row, "REB")),
                "apg": _to_float(cell(row, "AST")),
                "spg": _to_float(cell(row, "STL")),
                "bpg": _to_float(cell(row, "BLK")),
                "fg_pct": _to_float(cell(row, "FG_PCT")),
                "three_pct": _to_float(cell(row, "FG3_PCT")),
                "ft_pct": _to_float(cell(row, "FT_PCT")),
                "usage_rate": None,   # Base measure-type doesn't include usage
                "ts_pct": None,        # Advanced measure-type call required separately
                "source": "nba_gleague",
                "source_url": "https://www.nba.com/stats/players/traditional?LeagueID=20",
            })
        return out


__all__ = ["NBAGLeagueScraper"]
