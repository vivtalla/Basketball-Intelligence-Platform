"""Sprint 100 (Stream B) — NBADraft.net big-board scraper.

URL: https://www.nbadraft.net/ranking/nbabigboard/

The longest-running public mock board; layout is stable and Cloudflare
tolerates a friendly UA. Each prospect row carries rank, name, school,
position, height, weight, and class.

We extract rank, name, school, position, and an inferred tier (NBADraft.net
groups visually but not semantically — we infer from rank like ESPN).
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


class NBADraftNetScraper(HttpScraper):
    BASE_URL = "https://www.nbadraft.net"
    DELAY_SECONDS = 2.5
    FIXTURE_PREFIX = "nbadraft_net"

    def fetch_board(
        self,
        draft_year: int,
        fixture_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        path = "/ranking/nbabigboard/"
        html = self.get(path, fixture_name=fixture_name)
        rankings = self._parse_board(html)
        if len(rankings) < 20:
            raise ScraperError(
                "nbadraft_net: only {0} prospects parsed — selector changed".format(len(rankings))
            )
        return {
            "source": "nbadraft_net",
            "source_url": "https://www.nbadraft.net/ranking/nbabigboard/",
            "as_of": datetime.now(timezone.utc).isoformat(),
            "draft_year": draft_year,
            "rankings": rankings,
        }

    def _parse_board(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        out: List[Dict[str, Any]] = []
        # Big board is in a table.tablesorter; column 0 = rank, 1 = name+school,
        # 2 = position, 3 = height, 4 = weight, 5 = class.
        for table in soup.find_all("table"):
            classes = " ".join(table.get("class", []))
            if "tablesorter" not in classes and "rankings" not in classes:
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
                # Cell 1 contains the player name (often anchor) and school
                # in a <small> or <span class="school">.
                name_cell = cells[1]
                anchor = name_cell.find("a")
                name = anchor.get_text(strip=True) if anchor else name_cell.get_text(strip=True)
                if not name:
                    continue
                school_el = name_cell.find("small") or name_cell.find("span", class_="school")
                school = school_el.get_text(strip=True) if school_el else None
                position = cells[2].get_text(strip=True) if len(cells) > 2 else None
                if position == "":
                    position = None
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


__all__ = ["NBADraftNetScraper"]
