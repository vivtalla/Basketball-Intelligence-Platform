"""ProSportsTransactions injury scraper.

Pulls NBA injury filings from
``https://prosportstransactions.com/basketball/Search/SearchResults.php``.
Each page is a table of (Date, Team, Acquired, Relinquished, Notes) rows.

Pairing logic: an injury "starts" on a Relinquished row (player → IL) and
"resolves" on the matching Acquired row (player → activated). We pair by
``(player_name, body_part)`` order, oldest unresolved first.

Body-part extraction is regex over the Notes column — PST writes things like
"placed on IL with sore left knee" or "returned to lineup". We map a small
controlled vocabulary (knee, ankle, hamstring, etc.) plus a fallback.
"""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup

from data.scrapers._base import HttpScraper, ScraperError

logger = logging.getLogger(__name__)


# Controlled body-part vocabulary. Matches PST diagnosis prose.
_BODY_PART_PATTERNS: Tuple[Tuple[str, re.Pattern], ...] = (
    ("knee", re.compile(r"\b(knee|patella|meniscus|acl|mcl|lcl)\b", re.IGNORECASE)),
    ("ankle", re.compile(r"\bankle\b", re.IGNORECASE)),
    ("hamstring", re.compile(r"\bhamstring\b", re.IGNORECASE)),
    ("calf", re.compile(r"\bcalf\b", re.IGNORECASE)),
    ("foot", re.compile(r"\b(foot|toe|plantar)\b", re.IGNORECASE)),
    ("hip", re.compile(r"\bhip\b", re.IGNORECASE)),
    ("groin", re.compile(r"\bgroin\b", re.IGNORECASE)),
    ("quad", re.compile(r"\b(quad|quadriceps)\b", re.IGNORECASE)),
    ("achilles", re.compile(r"\bachilles\b", re.IGNORECASE)),
    ("back", re.compile(r"\b(back|lumbar|spine)\b", re.IGNORECASE)),
    ("shoulder", re.compile(r"\b(shoulder|rotator|labrum)\b", re.IGNORECASE)),
    ("elbow", re.compile(r"\belbow\b", re.IGNORECASE)),
    ("wrist", re.compile(r"\bwrist\b", re.IGNORECASE)),
    ("hand", re.compile(r"\b(hand|finger|thumb)\b", re.IGNORECASE)),
    ("neck", re.compile(r"\bneck\b", re.IGNORECASE)),
    ("head", re.compile(r"\b(head|concussion|face)\b", re.IGNORECASE)),
    ("ribs", re.compile(r"\brib(s)?\b", re.IGNORECASE)),
    ("illness", re.compile(r"\b(illness|flu|virus|covid|sick)\b", re.IGNORECASE)),
)


_SEVERITY_PATTERNS: Tuple[Tuple[str, re.Pattern], ...] = (
    ("season-ending", re.compile(r"\b(season-ending|out for (the )?season|done for (the )?season)\b", re.IGNORECASE)),
    ("severe", re.compile(r"\b(torn|rupture|fracture|broken|surgery)\b", re.IGNORECASE)),
    ("moderate", re.compile(r"\b(strain|sprain)\b", re.IGNORECASE)),
    ("minor", re.compile(r"\b(sore|soreness|tightness|bruise)\b", re.IGNORECASE)),
)


# Strip leading bullet/punctuation that PST uses to delimit diagnosis text.
_LEADING_BULLET_RE = re.compile(r"^\s*[••\-]\s*")


def _classify_body_part(notes: str) -> str:
    if not notes:
        return "other"
    for label, pattern in _BODY_PART_PATTERNS:
        if pattern.search(notes):
            return label
    return "other"


def _classify_severity(notes: str) -> Optional[str]:
    if not notes:
        return None
    for label, pattern in _SEVERITY_PATTERNS:
        if pattern.search(notes):
            return label
    return None


def _season_for(start: date) -> str:
    """NBA season string for a date. Aug-Jul split (Aug 1 → next-year start)."""
    year = start.year if start.month >= 8 else start.year - 1
    return "{0}-{1}".format(year, str((year + 1) % 100).zfill(2))


def _age_at(birth_date: Optional[date], event: date) -> Optional[float]:
    if not birth_date:
        return None
    delta = event - birth_date
    return round(delta.days / 365.25, 1)


class ProSportsTransactionsScraper(HttpScraper):
    """Scrapes the PST injury archive in date-windowed chunks."""

    BASE_URL = "https://prosportstransactions.com"
    DELAY_SECONDS = 2.5  # be polite — PST is a small archive site
    PAGE_SIZE = 25

    def fetch_injuries(
        self,
        start_date: date,
        end_date: date,
    ) -> List[Dict[str, Any]]:
        """Fetch all paired injury events between start_date and end_date.

        Returns list of dicts in the seed-CSV shape (minus player_id, which
        the ingestion service resolves via name lookup):
            player_name, body_part, severity, started_on, resolved_on,
            games_missed (None — PST doesn't expose), is_recurring (False
            — derived from prior records), source='prosportstransactions',
            source_url, raw_notes (for diagnosis field).
        """
        events = self._fetch_all_pages(start_date, end_date)
        return self._pair_events(events)

    def _fetch_all_pages(
        self, start_date: date, end_date: date
    ) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        start = 0
        while True:
            html = self.get(
                "/basketball/Search/SearchResults.php",
                params={
                    "Player": "",
                    "Team": "",
                    "BeginDate": start_date.isoformat(),
                    "EndDate": end_date.isoformat(),
                    "ILChkBx": "yes",  # injury list filings only
                    "Submit": "Search",
                    "start": start,
                },
            )
            page_events, has_more = self._parse_page(html)
            events.extend(page_events)
            if not has_more:
                break
            start += self.PAGE_SIZE
            # Hard safety cap so a parser bug can't infinite-loop.
            if start > 50_000:
                logger.warning("PST pagination exceeded 50,000 — stopping")
                break

        return events

    def _parse_page(self, html: str) -> Tuple[List[Dict[str, Any]], bool]:
        """Parse one results page → (events, has_next_page)."""
        soup = BeautifulSoup(html, "html.parser")
        rows: List[Dict[str, Any]] = []

        # PST uses a single results table whose first row is column headers.
        results_table = None
        for table in soup.find_all("table"):
            header = table.find("tr")
            if header is None:
                continue
            header_text = header.get_text(" ", strip=True).lower()
            if "acquired" in header_text and "relinquished" in header_text:
                results_table = table
                break

        if results_table is None:
            # No results table at all is not an error — just an empty window.
            return [], False

        for tr in results_table.find_all("tr")[1:]:
            cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if len(cells) < 5:
                continue
            date_str, team, acquired, relinquished, notes = cells[:5]
            event_date = _parse_pst_date(date_str)
            if event_date is None:
                continue

            if relinquished:  # going to IL
                player_name = _LEADING_BULLET_RE.sub("", relinquished).strip()
                if not player_name:
                    continue
                rows.append({
                    "kind": "relinquished",
                    "date": event_date,
                    "team": team,
                    "player_name": player_name,
                    "notes": notes,
                })
            elif acquired:  # returning from IL
                player_name = _LEADING_BULLET_RE.sub("", acquired).strip()
                if not player_name:
                    continue
                rows.append({
                    "kind": "acquired",
                    "date": event_date,
                    "team": team,
                    "player_name": player_name,
                    "notes": notes,
                })

        # Pagination: PST shows "Next" link when more results exist.
        has_next = bool(soup.find("a", string=re.compile(r"^Next", re.IGNORECASE)))
        return rows, has_next

    def _pair_events(
        self, events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Pair relinquished → acquired events into complete injury records.

        We use a per-player FIFO queue of unresolved injuries; each acquired
        event closes the oldest open one. Some never resolve in the window
        (still on IL at end_date) — those are emitted with resolved_on=None.
        """
        events = sorted(events, key=lambda e: e["date"])
        open_by_player: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        paired: List[Dict[str, Any]] = []

        for event in events:
            name = event["player_name"]
            if event["kind"] == "relinquished":
                open_by_player[name].append({
                    "started_on": event["date"],
                    "team": event["team"],
                    "notes": event["notes"],
                    "body_part": _classify_body_part(event["notes"]),
                    "severity": _classify_severity(event["notes"]),
                })
            else:  # acquired — close the oldest open injury for this player
                if open_by_player[name]:
                    opened = open_by_player[name].pop(0)
                    paired.append({
                        "player_name": name,
                        "body_part": opened["body_part"],
                        "severity": opened["severity"],
                        "started_on": opened["started_on"],
                        "resolved_on": event["date"],
                        "team_abbr": opened["team"],
                        "diagnosis": opened["notes"][:200] if opened["notes"] else None,
                        "source": "prosportstransactions",
                    })

        # Emit still-open injuries (no resolved_on yet)
        for name, opens in open_by_player.items():
            for opened in opens:
                paired.append({
                    "player_name": name,
                    "body_part": opened["body_part"],
                    "severity": opened["severity"],
                    "started_on": opened["started_on"],
                    "resolved_on": None,
                    "team_abbr": opened["team"],
                    "diagnosis": opened["notes"][:200] if opened["notes"] else None,
                    "source": "prosportstransactions",
                })

        return paired


def _parse_pst_date(raw: str) -> Optional[date]:
    """PST emits dates as 'YYYY-MM-DD' or 'YYYY-MM-DD ' with stray whitespace."""
    if not raw:
        return None
    raw = raw.strip()
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


# Re-export helpers so the ingestion service / tests can use them directly.
__all__ = [
    "ProSportsTransactionsScraper",
    "_classify_body_part",
    "_classify_severity",
    "_season_for",
    "_age_at",
    "_parse_pst_date",
]
