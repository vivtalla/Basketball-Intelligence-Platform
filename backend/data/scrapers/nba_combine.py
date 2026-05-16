"""Sprint 100 (Stream B) — NBA Draft Combine measurement scraper.

NBA Stats exposes combine results as JSON at:

    https://stats.nba.com/stats/draftcombinestats
        ?LeagueID=00&SeasonYear={year}-{year+1}

Where ``SeasonYear`` is the draft season (e.g. ``2025-26`` for the 2026 draft).
The response is a NBA-Stats-API shape:

    {
        "resource": "draftcombinestats",
        "resultSets": [{
            "name": "DraftCombineStats",
            "headers": ["TEMP_PLAYER_ID", "PLAYER_ID", "FIRST_NAME", "LAST_NAME",
                        "PLAYER_NAME", "POSITION", "HEIGHT_WO_SHOES",
                        "HEIGHT_W_SHOES", "WEIGHT", "WINGSPAN", "STANDING_REACH",
                        "BODY_FAT_PCT", "HAND_LENGTH", "HAND_WIDTH",
                        "STANDING_VERTICAL_LEAP", "MAX_VERTICAL_LEAP",
                        "LANE_AGILITY_TIME", "MODIFIED_LANE_AGILITY_TIME",
                        "THREE_QUARTER_SPRINT", "BENCH_PRESS", ...],
            "rowSet": [[...], [...], ...]
        }]
    }

The endpoint sits behind NBA's tight rate limiting plus a ``Referer:
https://www.nba.com/`` header check. ``HttpScraper`` already handles the
backoff; we just need the headers and the JSON parse.

Returns a list of ``CombineMeasurement`` dicts that the ingester upserts
into ``DraftProspectMeasurement``.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from data.scrapers._base import HttpScraper, ScraperError

logger = logging.getLogger(__name__)


def _normalize_name(name: str) -> str:
    """Match the normalization in draft_linkage_service so we can fuzzy-link."""
    s = (name or "").strip()
    s = re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


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


class NBACombineScraper(HttpScraper):
    """Fetches draft-combine measurements from NBA Stats."""

    BASE_URL = "https://stats.nba.com"
    DELAY_SECONDS = 1.5  # stats.nba.com tolerates ~1 RPS for combine endpoint
    FIXTURE_PREFIX = "nba_combine"

    def _headers(self) -> Dict[str, str]:
        # NBA Stats requires Referer + Origin to deflect bots. The default
        # HttpScraper UA/Accept-* headers are fine; we add the two extras here.
        base = super()._headers()
        base.update({
            "Referer": "https://www.nba.com/",
            "Origin": "https://www.nba.com",
            "Accept": "application/json, text/plain, */*",
            "x-nba-stats-origin": "stats",
            "x-nba-stats-token": "true",
        })
        return base

    def fetch_combine(self, draft_year: int, fixture_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch combine measurements for ``draft_year`` (e.g. 2026).

        Returns a list of dicts with snake_case keys matching the
        ``DraftProspectMeasurement`` schema, plus ``full_name`` and
        ``nba_player_id`` for linkage.

        Args:
            draft_year: end-year of the draft (combine ran in spring of
                that calendar year).
            fixture_name: in fixture mode, read from
                ``backend/tests/fixtures/scrapers/nba_combine/<fixture_name>``.

        Raises ``ScraperError`` if the rowSet is empty (suggests the
        endpoint blocked us or the season-year format changed).
        """
        season_year = "{0}-{1}".format(draft_year - 1, str(draft_year)[-2:])
        params = {"LeagueID": "00", "SeasonYear": season_year}
        body = self.get(
            "/stats/draftcombinestats",
            params=params,
            fixture_name=fixture_name,
        )

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ScraperError(
                "nba_combine: response not JSON for draft_year={0}: {1}".format(
                    draft_year, exc
                )
            )

        result_sets = payload.get("resultSets") or []
        if not result_sets:
            raise ScraperError("nba_combine: empty resultSets")
        rs = result_sets[0]
        headers = rs.get("headers") or []
        rows = rs.get("rowSet") or []
        if not rows:
            raise ScraperError(
                "nba_combine: 0 rows for draft_year={0} (combine may not have happened yet or "
                "anti-bot intercepted)".format(draft_year)
            )

        # Build header → index map.
        idx = {h: i for i, h in enumerate(headers)}

        def _cell(row: list, key: str) -> Any:
            i = idx.get(key)
            if i is None or i >= len(row):
                return None
            return row[i]

        measurements: List[Dict[str, Any]] = []
        for row in rows:
            full_name = _cell(row, "PLAYER_NAME") or (
                "{0} {1}".format(_cell(row, "FIRST_NAME") or "", _cell(row, "LAST_NAME") or "").strip()
            )
            if not full_name:
                continue
            measurements.append({
                "full_name": full_name,
                "normalized_name": _normalize_name(full_name),
                "nba_player_id": _to_int(_cell(row, "PLAYER_ID")),
                "position": _cell(row, "POSITION"),
                "combine_year": draft_year,
                "height_no_shoes": _to_float(_cell(row, "HEIGHT_WO_SHOES")),
                "height_with_shoes": _to_float(_cell(row, "HEIGHT_W_SHOES")),
                "weight": _to_float(_cell(row, "WEIGHT")),
                "wingspan": _to_float(_cell(row, "WINGSPAN")),
                "standing_reach": _to_float(_cell(row, "STANDING_REACH")),
                "body_fat_pct": _to_float(_cell(row, "BODY_FAT_PCT")),
                "hand_length": _to_float(_cell(row, "HAND_LENGTH")),
                "hand_width": _to_float(_cell(row, "HAND_WIDTH")),
                "standing_vert": _to_float(_cell(row, "STANDING_VERTICAL_LEAP")),
                "max_vert": _to_float(_cell(row, "MAX_VERTICAL_LEAP")),
                "lane_agility_seconds": _to_float(_cell(row, "LANE_AGILITY_TIME")),
                "three_quarter_sprint_seconds": _to_float(_cell(row, "THREE_QUARTER_SPRINT")),
                "bench_press_135": _to_int(_cell(row, "BENCH_PRESS")),
                "source": "nba_combine",
                "source_url": "https://www.nba.com/stats/draft/combine",
            })

        return measurements


__all__ = ["NBACombineScraper"]
