"""Sports Reference College Basketball scraper for draft prospects.

Pulls per-season player stats from
``https://www.sports-reference.com/cbb/seasons/men/{year}-per-game.html``
and ranks by points to build a top-N draft prospect candidate list.

Sports Reference exposes the master per-game table with stable ``id``
attributes (``per_game_stats``) so a content-based parser is durable.

This scraper is the simplest of the three — minimal anti-bot, consistent
schema, and we only need the top 60-100 prospects (not the full league).
Measurements (wingspan, vertical) live on combine pages and are out of
scope for this sprint; we surface height/weight from the roster column.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup

from data.scrapers._base import HttpScraper, ScraperError

logger = logging.getLogger(__name__)


# Sports Reference exposes positions as G, F, C, G-F, F-C, etc. Map to our
# primary_position vocabulary.
_POSITION_MAP: Dict[str, str] = {
    "G": "G",
    "F": "F",
    "C": "C",
    "G-F": "G",  # combo guards default to guard
    "F-G": "G",
    "F-C": "F",
    "C-F": "C",
}


def _normalize_position(raw: str) -> str:
    return _POSITION_MAP.get((raw or "").strip().upper(), "F")


def _height_to_inches(raw: str) -> Optional[float]:
    """'6-5' → 77.0; '6'5"' → 77.0; bad inputs → None."""
    if not raw:
        return None
    raw = (
        raw.strip()
        .replace("′", "-").replace("'", "-")  # primes → dash
        .replace('"', "").replace("″", "")     # double-primes → strip
    )
    match = re.match(r"^(\d+)\s*[-]\s*(\d+)$", raw)
    if not match:
        return None
    feet = int(match.group(1))
    inches = int(match.group(2))
    return float(feet * 12 + inches)


def _to_float(raw: Optional[str]) -> Optional[float]:
    if raw is None or raw == "":
        return None
    try:
        return float(str(raw).strip())
    except (TypeError, ValueError):
        return None


def _to_int(raw: Optional[str]) -> Optional[int]:
    f = _to_float(raw)
    if f is None:
        return None
    return int(f)


class SportsReferenceCBBScraper(HttpScraper):
    """Pulls top NCAA prospects from a season's per-game stats page."""

    BASE_URL = "https://www.sports-reference.com"
    DELAY_SECONDS = 3.0  # Sports Reference is strict about scraper rate

    def fetch_top_prospects(
        self,
        season_year: int,
        top_n: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return up to ``top_n`` prospects ranked by PPG for ``season_year``.

        Args:
            season_year: ending year of the NCAA season (2026 for 2025-26).
            top_n: cap on rows returned (default 100; seed CSV has 30).

        Raises ``ScraperError`` if the page schema doesn't include the
        ``per_game_stats`` table, suggesting an anti-bot interception or
        Sports Reference layout change.
        """
        path = "/cbb/seasons/men/{0}-per-game.html".format(season_year)
        html = self.get(path)
        rows = self._parse_per_game_page(html, season_year=season_year)
        if not rows:
            raise ScraperError(
                "sports-reference: 0 rows parsed from {0} — likely anti-bot or schema change".format(path)
            )
        # Sort by PPG desc and take top N. Filter out players with <10 PPG to
        # avoid noise from the long tail of the table.
        rows.sort(key=lambda r: r.get("ppg") or 0, reverse=True)
        rows = [r for r in rows if (r.get("ppg") or 0) >= 10][:top_n]
        return rows

    def _parse_per_game_page(
        self, html: str, season_year: int
    ) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")

        # Sports Reference wraps the main per-game stats table in an HTML
        # comment for one of its anti-scrape tricks; bs4 can read both.
        table = soup.find("table", id="per_game_stats")
        if table is None:
            # Fallback: search inside HTML comments for the table.
            from bs4 import Comment
            comments = soup.find_all(string=lambda t: isinstance(t, Comment))
            for comment in comments:
                inner = BeautifulSoup(str(comment), "html.parser")
                table = inner.find("table", id="per_game_stats")
                if table is not None:
                    break

        if table is None:
            return []

        # Header row → column index map (data-stat attribute is stable).
        col_idx: Dict[str, int] = {}
        header_row = table.find("thead").find_all("tr")[-1]  # last header row
        for idx, th in enumerate(header_row.find_all("th")):
            stat = th.get("data-stat")
            if stat:
                col_idx[stat] = idx

        rows: List[Dict[str, Any]] = []
        for tr in table.find("tbody").find_all("tr"):
            if "thead" in (tr.get("class") or []):
                continue  # mid-table header rows
            cells = tr.find_all(["th", "td"])
            if not cells:
                continue
            row: Dict[str, Any] = {}
            for stat, idx in col_idx.items():
                if idx >= len(cells):
                    continue
                row[stat] = cells[idx].get_text(strip=True)

            player_name = row.get("player")
            school = row.get("school_name")
            if not player_name or not school:
                continue

            position = _normalize_position(row.get("pos") or "")
            ppg = _to_float(row.get("pts_per_g"))
            rpg = _to_float(row.get("trb_per_g"))
            apg = _to_float(row.get("ast_per_g"))
            fg_pct = _to_float(row.get("fg_pct"))
            fg3_pct = _to_float(row.get("fg3_pct"))
            ts_pct = _to_float(row.get("ts_pct"))
            usg_pct = _to_float(row.get("usg_pct"))
            gp = _to_int(row.get("g"))
            min_pg = _to_float(row.get("mp_per_g"))

            # Build a stable external_id from school + name slug. Sports
            # Reference also exposes a player_id slug we could parse from the
            # anchor href, but this is sufficient for the seed-CSV contract.
            slug_name = re.sub(r"[^a-z0-9]+", "-", player_name.lower()).strip("-")
            slug_school = re.sub(r"[^a-z0-9]+", "-", school.lower()).strip("-")
            external_id = "sr-cbb-{0}-{1}-{2}".format(season_year, slug_school, slug_name)

            rows.append({
                "external_id": external_id,
                "full_name": player_name,
                "school": school,
                "school_type": "ncaa",
                "primary_position": position,
                "consensus_rank": None,  # PPG-based ordering = best we have here
                "age": None,  # Sports Reference doesn't expose age on this page
                "height_inches": None,  # also not on per-game page; future enrichment
                "weight_lbs": None,
                "wingspan": None,
                "ppg": ppg,
                "rpg": rpg,
                "apg": apg,
                "fg_pct": fg_pct,
                "fg3_pct": fg3_pct,
                "ts_pct": ts_pct,
                "usg_pct": usg_pct,
                "gp": gp,
                "min_pg": min_pg,
                "source": "sportsreference",
            })

        return rows


__all__ = [
    "SportsReferenceCBBScraper",
    "_height_to_inches",
    "_normalize_position",
]
