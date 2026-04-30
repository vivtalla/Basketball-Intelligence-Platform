"""Sprint 81 — Spotrac scraper parser + ingestion fallback tests.

These tests exercise:
- HTML fixture parsing (no network required)
- ScraperError propagation when the page lacks the expected structure
- ``sync_salary_data(source="spotrac")`` fallback to the seed CSV when the
  scraper raises (anti-bot or any other failure)
- Idempotency on (player_id, season) — re-running upserts in place
"""
from __future__ import annotations

import os
import sys
from typing import List
from unittest.mock import patch

import pytest

# Ensure backend/ is on the path so ``data.scrapers.spotrac`` and friends import.
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from data.scrapers._base import ScraperError  # noqa: E402
from data.scrapers.spotrac import SpotracScraper, _parse_money  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture: a minimal HTML snapshot of a Spotrac team cap page. We only need
# the table structure; the parser is content-based (matches header text), so
# real Spotrac CSS classes are not required.
# ---------------------------------------------------------------------------

_FIXTURE_TEAM_PAGE = """
<html><body>
<h1>Boston Celtics</h1>
<table>
  <thead>
    <tr><th>Player</th><th>Pos</th><th>Age</th>
        <th>Base Salary</th><th>Yrs Remaining</th><th>Type</th></tr>
  </thead>
  <tbody>
    <tr>
      <td><a href="/nba/player/12345/derrick-white/">Derrick White</a></td>
      <td>G</td><td>30</td>
      <td>$38,000,000</td><td>3</td><td>Standard</td>
    </tr>
    <tr>
      <td><a href="/nba/player/67890/jaylen-brown/">Jaylen Brown</a></td>
      <td>G/F</td><td>29</td>
      <td>$53,142,264</td><td>4</td><td>Standard</td>
    </tr>
    <tr>
      <td><a href="/nba/player/11111/jrue-holiday/">Jrue Holiday</a></td>
      <td>G</td><td>34</td>
      <td>$32,400,000</td><td>2</td><td>Player Option</td>
    </tr>
    <tr>
      <td>Two-Way Player</td>
      <td>G</td><td>22</td>
      <td>$578,577</td><td>1</td><td>Two-Way</td>
    </tr>
  </tbody>
</table>
<table>
  <thead><tr><th>Dead Cap</th><th>Salary</th></tr></thead>
  <tbody><tr><td>Bygone Player</td><td>$1,500,000</td></tr></tbody>
</table>
</body></html>
"""


_FIXTURE_NO_TABLE = "<html><body><p>Cloudflare challenge page</p></body></html>"


def test_parse_money_basic() -> None:
    assert _parse_money("$38,000,000") == 38_000_000
    assert _parse_money("12,500,000") == 12_500_000
    assert _parse_money("$0") == 0
    assert _parse_money("") is None
    assert _parse_money("--") is None
    assert _parse_money("$38.0M") == 38_000_000


def test_parser_extracts_active_roster_only() -> None:
    """Spotrac pages have multiple tables. We only want the first (active roster)."""
    scraper = SpotracScraper()
    rows = scraper._parse_team_page(
        _FIXTURE_TEAM_PAGE, team_abbr="BOS", season="2025-26"
    )

    assert len(rows) == 4, "should pick up all 4 active-roster rows but not dead-cap"

    derrick = next(r for r in rows if r["player_name"] == "Derrick White")
    assert derrick["team_abbr"] == "BOS"
    assert derrick["season"] == "2025-26"
    assert derrick["salary"] == 38_000_000
    assert derrick["years_remaining"] == 3
    assert derrick["contract_type"] == "max"
    assert derrick["is_player_option"] is False
    assert derrick["source"] == "spotrac"

    jrue = next(r for r in rows if r["player_name"] == "Jrue Holiday")
    assert jrue["is_player_option"] is True

    two_way = next(r for r in rows if r["player_name"] == "Two-Way Player")
    assert two_way["contract_type"] == "two_way"

    # Dead-cap row from second table must NOT leak in
    assert not any(r["player_name"] == "Bygone Player" for r in rows)


def test_fetch_contracts_raises_when_all_teams_lack_table() -> None:
    """Anti-bot challenge page on every team should bubble up as ScraperError."""
    scraper = SpotracScraper()
    with patch.object(scraper, "get", return_value=_FIXTURE_NO_TABLE):
        with pytest.raises(ScraperError):
            scraper.fetch_contracts(season="2025-26")


def test_fetch_contracts_raises_when_all_teams_empty() -> None:
    """Empty roster on every team treated as full failure → fallback."""
    empty_table = """
    <html><body><table>
        <thead><tr><th>Player</th><th>Salary</th></tr></thead>
        <tbody></tbody>
    </table></body></html>
    """
    scraper = SpotracScraper()
    with patch.object(scraper, "get", return_value=empty_table):
        with pytest.raises(ScraperError):
            scraper.fetch_contracts(season="2025-26")


def test_fetch_contracts_tolerates_a_few_team_failures() -> None:
    """Per-team partial failure (e.g. one 404) keeps the rest of the data."""
    call_count = {"n": 0}

    def _flaky_get(path):
        call_count["n"] += 1
        if call_count["n"] == 5:  # one team 404s
            raise ScraperError("HTTP 404 from " + path)
        return _FIXTURE_TEAM_PAGE

    scraper = SpotracScraper()
    with patch.object(scraper, "get", side_effect=_flaky_get):
        rows = scraper.fetch_contracts(season="2025-26")

    # 29 successful teams × 4 rows from the fixture = 116
    assert len(rows) == 29 * 4


# ---------------------------------------------------------------------------
# Ingestion-level fallback test — confirms sync_salary_data falls back to
# seed CSV when the scraper raises, and rows_upserted reflects CSV data.
# ---------------------------------------------------------------------------

@pytest.fixture
def in_memory_db():
    """Lightweight SQLite session with the schema applied via Alembic head."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from db.models import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


def _seed_one_team_and_player(session) -> None:
    """Insert minimal Player + Team so the seed CSV path can resolve at least one row."""
    from db.models import Player, Team
    session.add(Team(id=1610612738, abbreviation="BOS", name="Boston Celtics"))
    session.add(Player(id=1628401, full_name="Derrick White", first_name="Derrick", last_name="White"))
    session.commit()


def test_sync_falls_back_to_seed_csv_on_scrape_failure(in_memory_db, tmp_path) -> None:
    """When SpotracScraper raises, fall back to seed CSV without losing rows."""
    from services.salary_ingestion_service import sync_salary_data

    _seed_one_team_and_player(in_memory_db)

    # Minimal seed CSV with one row matching the seeded player + team.
    seed_csv = tmp_path / "contracts.csv"
    seed_csv.write_text(
        "nba_player_id,team_abbr,season,salary,years_remaining,is_player_option,is_team_option,contract_type,source\n"
        "1628401,BOS,2025-26,38000000,3,false,false,max,seed_csv\n"
    )

    # Force the scraper to fail.
    with patch(
        "services.salary_ingestion_service._fetch_spotrac_rows",
        side_effect=ScraperError("simulated anti-bot block"),
    ):
        result = sync_salary_data(
            in_memory_db,
            source="spotrac",
            seed_path=str(seed_csv),
            season="2025-26",
        )

    assert result["fallback_used"] is True
    assert result["source"] == "seed_csv"
    assert result["rows_upserted"] == 1


def test_sync_uses_spotrac_when_scrape_succeeds(in_memory_db, tmp_path) -> None:
    """Successful scrape should write rows with source='spotrac' and not touch seed CSV."""
    from services.salary_ingestion_service import sync_salary_data

    _seed_one_team_and_player(in_memory_db)

    fake_rows: List[dict] = [{
        "player_name": "Derrick White",
        "team_abbr": "BOS",
        "season": "2025-26",
        "salary": 38_000_000,
        "years_remaining": 3,
        "is_player_option": False,
        "is_team_option": False,
        "contract_type": "max",
        "source": "spotrac",
    }]

    with patch(
        "services.salary_ingestion_service._fetch_spotrac_rows",
        return_value=fake_rows,
    ):
        result = sync_salary_data(
            in_memory_db,
            source="spotrac",
            season="2025-26",
        )

    assert result["fallback_used"] is False
    assert result["source"] == "spotrac"
    assert result["rows_upserted"] == 1

    # Verify the row landed with source='spotrac', not 'seed_csv'
    from db.models import PlayerContract
    contract = (
        in_memory_db.query(PlayerContract)
        .filter(PlayerContract.player_id == 1628401)
        .first()
    )
    assert contract is not None
    assert contract.source == "spotrac"
    assert contract.salary == 38_000_000


def test_sync_idempotent_on_rerun(in_memory_db, tmp_path) -> None:
    """Re-running the same source should upsert in place, not duplicate rows."""
    from services.salary_ingestion_service import sync_salary_data
    from db.models import PlayerContract

    _seed_one_team_and_player(in_memory_db)

    seed_csv = tmp_path / "contracts.csv"
    seed_csv.write_text(
        "nba_player_id,team_abbr,season,salary,years_remaining,is_player_option,is_team_option,contract_type,source\n"
        "1628401,BOS,2025-26,38000000,3,false,false,max,seed_csv\n"
    )

    sync_salary_data(in_memory_db, source="seed_csv", seed_path=str(seed_csv))
    first_count = in_memory_db.query(PlayerContract).count()

    sync_salary_data(in_memory_db, source="seed_csv", seed_path=str(seed_csv))
    second_count = in_memory_db.query(PlayerContract).count()

    assert first_count == 1
    assert second_count == 1
