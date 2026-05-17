"""Sprint 100 (Stream B) — RealGM international league stats scraper.

RealGM publishes per-player season averages for Europe's top leagues at:

    https://basketball.realgm.com/international/league/{LEAGUE_ID}/
        {LEAGUE_SLUG}/stats/{SEASON}/Averages/All/points/All/desc/1/Regular_Season

Where ``SEASON`` is the end-year of the European season (e.g. ``2026`` for
the 2025-26 season). The page is server-rendered HTML; the player rows
live in a ``<table class="basketball compact stats">``.

We only fetch top-N young players per league (filter by `Age <= 23`)
because draft-eligible prospects are a tiny slice of any international
league. RealGM is rate-limit-friendly (no anti-bot challenges as of
Sprint 100) so the standard ``HttpScraper`` works.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from data.scrapers._base import HttpScraper, ScraperError

logger = logging.getLogger(__name__)


# (league_id, league_slug, display_label) tuples covering the leagues we care
# about for draft prospects. Order matters for diagnostic logs only.
LEAGUES: List[tuple] = [
    (1, "Euroleague", "Euroleague"),
    (2, "EuroCup", "EuroCup"),
    (18, "ABA-League", "Adriatic"),
    (4, "French-LNB", "French LNB"),
]


def _to_float(raw: Any) -> Optional[float]:
    if raw is None or raw == "":
        return None
    try:
        return float(str(raw).strip())
    except (TypeError, ValueError):
        return None


def _to_int(raw: Any) -> Optional[int]:
    f = _to_float(raw)
    if f is None:
        return None
    return int(f)


def _pct(raw: Any) -> Optional[float]:
    """RealGM gives shooting percentages as ``45.6`` (i.e. percent points)."""
    f = _to_float(raw)
    if f is None:
        return None
    # If a row shows 0.456 vs 45.6, normalize both to 0.456 (0-1 range).
    return f / 100.0 if f > 1.5 else f


class RealGMInternationalScraper(HttpScraper):
    """Fetches per-season RealGM averages for one of the supported leagues."""

    BASE_URL = "https://basketball.realgm.com"
    DELAY_SECONDS = 2.0
    FIXTURE_PREFIX = "realgm_international"

    def fetch_league(
        self,
        league_id: int,
        league_slug: str,
        season_end_year: int,
        max_age: int = 23,
        fixture_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return per-player season averages for ``league_id`` / ``season_end_year``.

        Filters to players with Age <= ``max_age`` (draft-eligible window).
        Always returns a list; an empty list raises ``ScraperError`` since
        a healthy fetch always has at least one young rotation player.
        """
        path = (
            "/international/league/{league_id}/{slug}/stats/{season}/"
            "Averages/All/points/All/desc/1/Regular_Season"
        ).format(league_id=league_id, slug=league_slug, season=season_end_year)
        html = self.get(path, fixture_name=fixture_name)
        rows = self._parse_stats_table(html, max_age=max_age)
        if not rows:
            raise ScraperError(
                "realgm: 0 young players parsed for {0} {1}".format(league_slug, season_end_year)
            )
        return [
            {**row, "season_end_year": season_end_year, "league_id": league_id,
             "league_slug": league_slug, "source_url": "{0}{1}".format(self.BASE_URL, path)}
            for row in rows
        ]

    def fetch_all_leagues(
        self,
        season_end_year: int,
        max_age: int = 23,
    ) -> List[Dict[str, Any]]:
        """Pull all configured leagues for ``season_end_year``.

        A failure on one league does not abort the others; failures are
        logged but the partial result is returned. The ingest layer
        wraps the result so that "all leagues failed" surfaces as a
        single ``ScraperError`` at the orchestrator level.
        """
        out: List[Dict[str, Any]] = []
        for league_id, slug, _label in LEAGUES:
            try:
                rows = self.fetch_league(league_id, slug, season_end_year, max_age=max_age)
                out.extend(rows)
            except ScraperError as exc:
                logger.warning(
                    "realgm: skipped league=%s season=%d err=%s", slug, season_end_year, exc
                )
        if not out:
            raise ScraperError(
                "realgm: every league fetch failed for {0}".format(season_end_year)
            )
        return out

    def _parse_stats_table(self, html: str, max_age: int) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        # RealGM stats tables carry ``class="basketball compact stats"``; the
        # one we want is the one inside ``id="table-stats"``. Fall back to
        # any table with the right class if the wrapper id changes.
        wrap = soup.find(id="table-stats") or soup
        table = wrap.find("table")
        if table is None:
            return []

        # Build column index from header row.
        thead = table.find("thead")
        if thead is None:
            return []
        col_idx: Dict[str, int] = {}
        for i, th in enumerate(thead.find_all("th")):
            stat = th.get("data-stat") or th.get_text(strip=True).lower()
            if stat:
                col_idx[stat.lower()] = i

        rows: List[Dict[str, Any]] = []
        body = table.find("tbody")
        if body is None:
            return []
        for tr in body.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            if len(cells) < 5:
                continue

            def cell(key: str) -> Optional[str]:
                # Prefer the data-stat header; fall back to lowercase header text.
                idx = col_idx.get(key) or col_idx.get(key.lower())
                if idx is None or idx >= len(cells):
                    return None
                txt = cells[idx].get_text(strip=True)
                return txt or None

            # RealGM column ids include "player", "team", "age", "gp", "min",
            # "pts", "reb", "ast", "stl", "blk", "fgp", "3pp", "ftp", "tspct",
            # "uspct" (varying by view). Map liberally.
            age = _to_int(cell("age"))
            if age is None or age > max_age:
                continue
            player = cell("player")
            if not player:
                continue
            team = cell("team")
            rows.append({
                "player": player,
                "age": age,
                "team_name": team,
                "games": _to_int(cell("gp")),
                "minutes_per_game": _to_float(cell("min")),
                "ppg": _to_float(cell("pts")),
                "rpg": _to_float(cell("reb")) or _to_float(cell("trb")),
                "apg": _to_float(cell("ast")),
                "spg": _to_float(cell("stl")),
                "bpg": _to_float(cell("blk")),
                "fg_pct": _pct(cell("fgp")),
                "three_pct": _pct(cell("3pp")) or _pct(cell("3pct")),
                "ft_pct": _pct(cell("ftp")),
                "usage_rate": _pct(cell("usg")) or _pct(cell("uspct")),
                "ts_pct": _pct(cell("ts")) or _pct(cell("tspct")),
            })
        return rows


__all__ = ["RealGMInternationalScraper", "LEAGUES"]
