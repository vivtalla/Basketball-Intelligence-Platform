"""Sprint 100 (Stream B) — CBS Sports prospect-rankings scraper.

URL: https://www.cbssports.com/nba/draft/prospect-rankings/

CBS publishes a top-60 prospect-rankings page that we scrape for rank,
name, school, position, height/weight. Same shape as ESPN /
NBADraft.net (rank + tier inferred from position-in-list).

CBS occasionally renders the board inside a JS-rendered widget. We
parse the static HTML; if the table isn't present we raise
``ScraperError`` and the orchestrator drops CBS from the consensus
that run.
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


class CBSMockDraftScraper(HttpScraper):
    BASE_URL = "https://www.cbssports.com"
    DELAY_SECONDS = 2.5
    FIXTURE_PREFIX = "cbs_mock_draft"

    def fetch_board(
        self,
        draft_year: int,
        fixture_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        path = "/nba/draft/prospect-rankings/"
        html = self.get(path, fixture_name=fixture_name)
        rankings = self._parse_board(html)
        if len(rankings) < 20:
            raise ScraperError(
                "cbs: only {0} prospects parsed — selector changed".format(len(rankings))
            )
        return {
            "source": "cbs",
            "source_url": "https://www.cbssports.com/nba/draft/prospect-rankings/",
            "as_of": datetime.now(timezone.utc).isoformat(),
            "draft_year": draft_year,
            "rankings": rankings,
        }

    def _parse_board(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        out: List[Dict[str, Any]] = []
        # CBS uses a "TableBase" class for sortable lists. Find tables
        # whose headers include "Rk" or "Rank".
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
                # Name is usually in cell 1 (or 2 if cell 0 is a rank-arrow).
                name_cell = cells[1]
                anchor = name_cell.find("a")
                name = anchor.get_text(strip=True) if anchor else name_cell.get_text(strip=True)
                if not name:
                    continue
                school: Optional[str] = None
                school_el = name_cell.find("span", class_="school") or name_cell.find("small")
                if school_el:
                    school = school_el.get_text(strip=True)
                elif len(cells) >= 3:
                    school = cells[2].get_text(strip=True) or None
                position = None
                if len(cells) >= 4:
                    position = cells[3].get_text(strip=True) or None
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


__all__ = ["CBSMockDraftScraper"]
