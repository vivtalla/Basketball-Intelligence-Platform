"""Sprint 100 (Stream B) — ESPN best-available board scraper.

URL: https://www.espn.com/nba/draft/bestavailable

The board renders top-60 prospects as a table. We pull rank, name, school,
and projected position. ESPN does not publish a tier label so ``tier``
is inferred from rank (1-14 lottery, 15-30 first_round, 31-60
second_round).

This is a public surface — no auth required, no Cloudflare interception
as of Sprint 100 inspection. Standard ``HttpScraper`` covers it.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from data.scrapers._base import HttpScraper, ScraperError

logger = logging.getLogger(__name__)


def _tier_from_rank(rank: int) -> str:
    if rank <= 14:
        return "lottery"
    if rank <= 30:
        return "first_round"
    return "second_round"


class ESPNMockDraftScraper(HttpScraper):
    BASE_URL = "https://www.espn.com"
    DELAY_SECONDS = 2.5
    FIXTURE_PREFIX = "espn_mock_draft"

    def fetch_board(
        self,
        draft_year: int,
        fixture_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return ESPN's current best-available board.

        ``draft_year`` is included in the response payload for ingest
        attribution; ESPN's URL doesn't include the year (the page
        always shows the next draft).
        """
        path = "/nba/draft/bestavailable"
        html = self.get(path, fixture_name=fixture_name)
        rankings = self._parse_board(html)
        if len(rankings) < 20:
            raise ScraperError(
                "espn: only {0} prospects parsed — selector likely changed".format(len(rankings))
            )
        return {
            "source": "espn",
            "source_url": "https://www.espn.com/nba/draft/bestavailable",
            "as_of": datetime.now(timezone.utc).isoformat(),
            "draft_year": draft_year,
            "rankings": rankings,
        }

    def _parse_board(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        out: List[Dict[str, Any]] = []
        # The board is rendered inside a <table>. ESPN occasionally renames
        # the wrapping div; we walk every table looking for one whose first
        # <th> includes "RK" or "Rank".
        for table in soup.find_all("table"):
            header_text = " ".join(th.get_text(" ", strip=True).lower() for th in table.find_all("th"))
            if "rk" not in header_text and "rank" not in header_text:
                continue
            tbody = table.find("tbody")
            if tbody is None:
                continue
            for tr in tbody.find_all("tr"):
                cells = tr.find_all("td")
                if len(cells) < 3:
                    continue
                rank_txt = cells[0].get_text(strip=True)
                if not rank_txt.isdigit():
                    continue
                rank = int(rank_txt)
                # Player name + school can live in cell 1 (combined) or split
                # across cells 1 and 2 depending on viewport variant.
                name_cell = cells[1]
                anchor = name_cell.find("a")
                name = anchor.get_text(strip=True) if anchor else name_cell.get_text(strip=True)
                if not name:
                    continue
                # School often in an italicized span or the next cell.
                school: Optional[str] = None
                small = name_cell.find("small") or name_cell.find("span", class_="school")
                if small:
                    school = small.get_text(strip=True)
                elif len(cells) >= 3:
                    school = cells[2].get_text(strip=True) or None
                # Position often in cell 3 or 4.
                position: Optional[str] = None
                if len(cells) >= 4:
                    position = (cells[3].get_text(strip=True) or None)
                out.append({
                    "rank": rank,
                    "name": name,
                    "school": school,
                    "position": position,
                    "tier": _tier_from_rank(rank),
                    "comp": None,
                })
            if out:
                return out
        return out


__all__ = ["ESPNMockDraftScraper"]
