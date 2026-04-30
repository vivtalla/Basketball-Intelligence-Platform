"""Spotrac NBA contract scraper.

Fetches per-team cap pages from ``https://www.spotrac.com/nba/{team-slug}/cap``,
parses the player-contract tables, and returns rows in the normalized shape
that ``salary_ingestion_service`` expects (matches the seed CSV columns).

Spotrac sits behind Cloudflare and may serve JS-challenge pages to plain
``requests`` calls. When that happens (or any other parse failure occurs),
we raise ``ScraperError`` and the caller falls back to the seed CSV.

Usage::

    rows = SpotracScraper().fetch_contracts(season="2025-26")
    # -> [{"nba_player_id": 1628401, "team_abbr": "BOS", "season": "2025-26", ...}, ...]
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from data.scrapers._base import HttpScraper, ScraperError

logger = logging.getLogger(__name__)


# Spotrac team slugs keyed by NBA tricode. Stable since 2018.
_TEAM_SLUGS: Dict[str, str] = {
    "ATL": "atlanta-hawks",
    "BOS": "boston-celtics",
    "BKN": "brooklyn-nets",
    "CHA": "charlotte-hornets",
    "CHI": "chicago-bulls",
    "CLE": "cleveland-cavaliers",
    "DAL": "dallas-mavericks",
    "DEN": "denver-nuggets",
    "DET": "detroit-pistons",
    "GSW": "golden-state-warriors",
    "HOU": "houston-rockets",
    "IND": "indiana-pacers",
    "LAC": "los-angeles-clippers",
    "LAL": "los-angeles-lakers",
    "MEM": "memphis-grizzlies",
    "MIA": "miami-heat",
    "MIL": "milwaukee-bucks",
    "MIN": "minnesota-timberwolves",
    "NOP": "new-orleans-pelicans",
    "NYK": "new-york-knicks",
    "OKC": "oklahoma-city-thunder",
    "ORL": "orlando-magic",
    "PHI": "philadelphia-76ers",
    "PHX": "phoenix-suns",
    "POR": "portland-trail-blazers",
    "SAC": "sacramento-kings",
    "SAS": "san-antonio-spurs",
    "TOR": "toronto-raptors",
    "UTA": "utah-jazz",
    "WAS": "washington-wizards",
}


_MONEY_RE = re.compile(r"[\$,]")


def _parse_money(raw: str) -> Optional[int]:
    """Coerce '$38,000,000' or '38,000,000' to 38000000. Empty/'--' -> None."""
    if not raw:
        return None
    cleaned = _MONEY_RE.sub("", raw).strip()
    if not cleaned or cleaned in ("--", "-"):
        return None
    # Handle "$38.0M" shorthand if Spotrac ever switches.
    if cleaned.endswith(("M", "m")):
        try:
            return int(float(cleaned[:-1]) * 1_000_000)
        except (TypeError, ValueError):
            return None
    try:
        return int(float(cleaned))
    except (TypeError, ValueError):
        return None


def _classify_contract_type(years_remaining: Optional[int], salary: Optional[int]) -> str:
    """Heuristic mapping to the contract_type values our schema expects.

    The seed CSV uses {max, mid, vet_min, rookie, two_way, exhibit_10}. Spotrac
    doesn't expose this label directly; we infer from salary + years.
    """
    if salary is None:
        return "standard"
    if salary >= 35_000_000:
        return "max"
    if salary >= 12_000_000:
        return "mid"
    if salary <= 2_500_000:
        return "vet_min"
    return "standard"


class SpotracScraper(HttpScraper):
    """Pulls contracts for all 30 teams.

    A full league refresh issues 30 GETs at 2s/request = ~60s. Cron-friendly.
    """

    BASE_URL = "https://www.spotrac.com"
    DELAY_SECONDS = 2.0

    def fetch_contracts(self, season: str) -> List[Dict[str, Any]]:
        """Fetch contracts for ``season`` (e.g. ``"2025-26"``) across all teams.

        Raises ``ScraperError`` on any team page failure to keep the per-night
        cron behavior all-or-nothing — we don't want partial DB updates that
        leave half the league on stale rows.
        """
        all_rows: List[Dict[str, Any]] = []
        for team_abbr, slug in _TEAM_SLUGS.items():
            try:
                html = self.get("/nba/{0}/cap".format(slug))
                team_rows = self._parse_team_page(html, team_abbr=team_abbr, season=season)
            except ScraperError:
                raise
            except Exception as exc:  # noqa: BLE001 — convert anything to ScraperError
                raise ScraperError(
                    "spotrac parse failed for {0}: {1}".format(team_abbr, exc)
                ) from exc
            if not team_rows:
                # An empty team page is suspicious — Spotrac always lists at
                # least the rookie scale. Treat as a parse failure so we fall
                # back rather than wiping rows.
                raise ScraperError(
                    "spotrac returned 0 contracts for {0} — anti-bot or schema change suspected".format(team_abbr)
                )
            all_rows.extend(team_rows)
            logger.info("spotrac: fetched %d contracts for %s", len(team_rows), team_abbr)

        return all_rows

    def _parse_team_page(self, html: str, team_abbr: str, season: str) -> List[Dict[str, Any]]:
        """Parse a single team's cap page into normalized contract dicts.

        We look for any table whose header row contains "Player" + "Salary"
        substrings. Spotrac swaps table CSS classes occasionally so a content-
        based selector is more durable than a class-based one.
        """
        soup = BeautifulSoup(html, "html.parser")
        rows: List[Dict[str, Any]] = []

        for table in soup.find_all("table"):
            headers = [
                (th.get_text(strip=True) or "").lower()
                for th in table.find_all("th")
            ]
            if not headers:
                continue
            if not any("player" in h for h in headers) or not any(
                "salary" in h or "cap" in h or "contract" in h for h in headers
            ):
                continue

            # Map header text → column index for tolerant lookups.
            col_idx: Dict[str, int] = {}
            for idx, label in enumerate(headers):
                if "player" in label and "player" not in col_idx:
                    col_idx["player"] = idx
                elif label == "pos" or "position" in label:
                    col_idx["position"] = idx
                elif "age" in label and "age" not in col_idx:
                    col_idx["age"] = idx
                elif ("salary" in label or "base" in label) and "salary" not in col_idx:
                    col_idx["salary"] = idx
                elif "yrs" in label or "years" in label:
                    col_idx["years"] = idx
                elif "type" in label or "contract" in label:
                    col_idx["type"] = idx

            if "player" not in col_idx or "salary" not in col_idx:
                continue

            for tr in table.find_all("tr"):
                cells = tr.find_all("td")
                if not cells or len(cells) < max(col_idx.values()) + 1:
                    continue

                player_cell = cells[col_idx["player"]]
                # Spotrac wraps player names in <a> with a player-id slug. The
                # ID is on a data-attr or href like /nba/player/12345/...
                anchor = player_cell.find("a")
                player_name = (anchor or player_cell).get_text(strip=True) or None
                if not player_name:
                    continue

                # We don't get nba_player_id from Spotrac directly — the
                # ingestion service resolves names to player_id via the
                # ``players`` table, so we surface ``player_name`` for that lookup.
                salary_raw = cells[col_idx["salary"]].get_text(strip=True)
                salary = _parse_money(salary_raw)
                years_raw = (
                    cells[col_idx["years"]].get_text(strip=True)
                    if "years" in col_idx and len(cells) > col_idx["years"]
                    else ""
                )
                try:
                    years_remaining = int(re.sub(r"\D", "", years_raw) or "1")
                except ValueError:
                    years_remaining = 1

                type_raw = (
                    cells[col_idx["type"]].get_text(strip=True).lower()
                    if "type" in col_idx and len(cells) > col_idx["type"]
                    else ""
                )
                is_player_option = "player option" in type_raw or "po" in type_raw.split()
                is_team_option = "team option" in type_raw or "to" in type_raw.split()

                contract_type = _classify_contract_type(years_remaining, salary)
                if "rookie" in type_raw:
                    contract_type = "rookie"
                elif "two-way" in type_raw or "two way" in type_raw:
                    contract_type = "two_way"

                rows.append({
                    "player_name": player_name,
                    "team_abbr": team_abbr,
                    "season": season,
                    "salary": salary or 0,
                    "years_remaining": years_remaining,
                    "is_player_option": is_player_option,
                    "is_team_option": is_team_option,
                    "contract_type": contract_type,
                    "source": "spotrac",
                })

            # Take the first matching table on the page; Spotrac's first table
            # is the active roster, subsequent tables are dead cap / waived
            # which we don't want to surface as live contracts.
            break

        return rows
