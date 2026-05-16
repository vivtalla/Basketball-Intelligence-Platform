"""Sports Reference College Basketball scraper for draft prospects.

Pulls per-season player stats from the scoring leaders page at
``https://www.sports-reference.com/cbb/seasons/men/{year}-leaders.html``
and follows individual player profile links for full stat lines.

Sports Reference uses Cloudflare anti-scrape in some environments, and also
wraps certain content in HTML comments. Both cases are handled.

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
    """Pulls top NCAA prospects from a season's leaders page."""

    BASE_URL = "https://www.sports-reference.com"
    DELAY_SECONDS = 3.0  # Sports Reference is strict about scraper rate
    # Sprint 100 (Stream B) — fixture mode for tests.
    FIXTURE_PREFIX = "sportsreference_cbb"

    def fetch_top_prospects(
        self,
        season_year: int,
        top_n: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return up to ``top_n`` prospects ranked by PPG for ``season_year``.

        Args:
            season_year: ending year of the NCAA season (2026 for 2025-26).
            top_n: cap on rows returned (default 100; seed CSV has 30).

        Raises ``ScraperError`` if the leaders div is missing, suggesting an
        anti-bot interception or Sports Reference layout change.
        """
        path = "/cbb/seasons/men/{0}-leaders.html".format(season_year)
        html = self.get(path)

        leader_entries = self._parse_leaders_page(html)
        if not leader_entries:
            raise ScraperError(
                "sports-reference: 0 leaders found at {0} — page structure may have changed".format(path)
            )

        # Filter to minimum PPG threshold, sort descending, cap at top_n.
        MIN_PPG = 10.0
        leader_entries = [e for e in leader_entries if (e[2] or 0.0) >= MIN_PPG]
        leader_entries.sort(key=lambda e: e[2] or 0.0, reverse=True)
        leader_entries = leader_entries[:top_n]

        rows: List[Dict[str, Any]] = []
        for name, school, ppg, profile_url in leader_entries:
            row = self._fetch_player_profile_stats(name, school, ppg, profile_url, season_year)
            rows.append(row)

        return rows

    def _parse_leaders_page(self, html: str) -> List[Tuple[str, Optional[str], Optional[float], str]]:
        """Parse scoring leaders div. Returns [(name, school, ppg, profile_url), ...]."""
        from bs4 import Comment  # type: ignore[import]
        soup = BeautifulSoup(html, "html.parser")

        # Try direct parse first; fall back to HTML-comment-wrapped content (SR anti-scrape).
        div = soup.find("div", id="leaders_pts_per_g")
        if div is None:
            for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
                inner = BeautifulSoup(str(comment), "html.parser")
                div = inner.find("div", id="leaders_pts_per_g")
                if div is not None:
                    break

        if div is None:
            return []

        entries: List[Tuple[str, Optional[str], Optional[float], str]] = []
        for who_span in div.find_all("span", class_="who"):
            anchor = who_span.find("a")
            if not anchor:
                continue
            name = anchor.get_text(strip=True)
            small = who_span.find("small")
            school: Optional[str] = small.get_text(strip=True) if small else None
            profile_path = anchor.get("href", "")
            profile_url = (
                "https://www.sports-reference.com" + profile_path
                if profile_path.startswith("/")
                else profile_path
            )
            value_span = who_span.find_next_sibling("span", class_="value")
            ppg: Optional[float] = None
            if value_span:
                try:
                    ppg = float(value_span.get_text(strip=True))
                except (ValueError, TypeError):
                    ppg = None
            entries.append((name, school, ppg, profile_url))

        return entries

    def _fetch_player_profile_stats(
        self, name: str, school: Optional[str], ppg: Optional[float],
        profile_url: str, season_year: int
    ) -> Dict[str, Any]:
        """Fetch full stat line from a player profile page for the target season."""
        from bs4 import Comment  # type: ignore[import]

        slug_name = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        slug_school = re.sub(r"[^a-z0-9]+", "-", (school or "").lower()).strip("-")
        external_id = "sr-cbb-{0}-{1}-{2}".format(season_year, slug_school, slug_name)

        base: Dict[str, Any] = {
            "external_id": external_id,
            "full_name": name,
            "school": school,
            "school_type": "ncaa",
            "primary_position": None,
            "consensus_rank": None,
            "age": None,
            "height_inches": None,
            "weight_lbs": None,
            "wingspan": None,
            "ppg": ppg,
            "rpg": None,
            "apg": None,
            "fg_pct": None,
            "fg3_pct": None,
            "ts_pct": None,
            "usg_pct": None,
            "gp": None,
            "min_pg": None,
            "source": "sportsreference",
        }

        try:
            html = self.get(profile_url)
            soup = BeautifulSoup(html, "html.parser")

            # Find per-game table — may be wrapped in HTML comment.
            table = soup.find("table", id="players_per_game")
            if table is None:
                for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
                    inner = BeautifulSoup(str(comment), "html.parser")
                    table = inner.find("table", id="players_per_game")
                    if table is not None:
                        break

            if table is None:
                return base

            # Find the row for the target season (season_year = end year, e.g., 2026 for 2025-26).
            target_season_str = "{0}-{1}".format(season_year - 1, str(season_year)[-2:])
            for row in table.find_all("tr"):
                season_td = row.find("td", {"data-stat": "season"})
                if season_td and season_td.get_text(strip=True) == target_season_str:
                    def _get(stat: str) -> Optional[float]:
                        cell = row.find("td", {"data-stat": stat})
                        if cell is None:
                            return None
                        try:
                            return float(cell.get_text(strip=True))
                        except (ValueError, TypeError):
                            return None

                    base["ppg"] = _get("pts_per_g") or ppg
                    base["rpg"] = _get("trb_per_g")
                    base["apg"] = _get("ast_per_g")
                    base["fg_pct"] = _get("fg_pct")
                    base["fg3_pct"] = _get("fg3_pct")
                    base["gp"] = int(_get("g") or 0) or None
                    base["min_pg"] = _get("mp_per_g")
                    # TS% computed if pts + fga + fta available; otherwise leave None.
                    pts_g = _get("pts_per_g")
                    fga_g = _get("fga_per_g")
                    fta_g = _get("fta_per_g")
                    if pts_g and fga_g is not None and fta_g is not None:
                        denominator = 2.0 * (fga_g + 0.44 * fta_g)
                        if denominator > 0:
                            base["ts_pct"] = pts_g / denominator
                    break

        except ScraperError as exc:
            logger.warning("sr-cbb: could not enrich %s from profile: %s", name, exc)

        return base

    def _parse_per_game_page(
        self, html: str, season_year: int
    ) -> List[Dict[str, Any]]:
        """Parse the legacy per-game stats table (kept for backward compatibility with tests).

        The per-game stats page (``-per-game.html``) returns 404 in production;
        the live path now uses ``_parse_leaders_page`` + ``_fetch_player_profile_stats``.
        This method is retained so existing tests that fixture against the old
        ``per_game_stats`` table structure continue to pass.
        """
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

            # Build a stable external_id from school + name slug.
            slug_name = re.sub(r"[^a-z0-9]+", "-", player_name.lower()).strip("-")
            slug_school = re.sub(r"[^a-z0-9]+", "-", school.lower()).strip("-")
            external_id = "sr-cbb-{0}-{1}-{2}".format(season_year, slug_school, slug_name)

            rows.append({
                "external_id": external_id,
                "full_name": player_name,
                "school": school,
                "school_type": "ncaa",
                "primary_position": position,
                "consensus_rank": None,
                "age": None,
                "height_inches": None,
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
