"""Sprint 81 — ProSportsTransactions scraper tests."""
from __future__ import annotations

import os
import sys
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from data.scrapers._base import ScraperError  # noqa: E402
from data.scrapers.prosportstransactions import (  # noqa: E402
    ProSportsTransactionsScraper,
    _classify_body_part,
    _classify_severity,
    _parse_pst_date,
    _season_for,
)


def _make_playwright_mock(html_content: str):
    """Returns a context-manager mock for sync_playwright() that yields html_content."""
    page_mock = MagicMock()
    page_mock.content.return_value = html_content

    browser_mock = MagicMock()
    browser_mock.new_page.return_value = page_mock

    chromium_mock = MagicMock()
    chromium_mock.launch.return_value = browser_mock

    pw_mock = MagicMock()
    pw_mock.chromium = chromium_mock

    cm_mock = MagicMock()
    cm_mock.__enter__ = MagicMock(return_value=pw_mock)
    cm_mock.__exit__ = MagicMock(return_value=False)

    return cm_mock


def test_body_part_classification() -> None:
    assert _classify_body_part("placed on IL with sore left knee") == "knee"
    assert _classify_body_part("right ankle sprain") == "ankle"
    assert _classify_body_part("torn achilles") == "achilles"
    assert _classify_body_part("hamstring strain") == "hamstring"
    assert _classify_body_part("activated from IL") == "other"
    assert _classify_body_part("") == "other"


def test_severity_classification() -> None:
    assert _classify_severity("torn ACL — out for the season") == "season-ending"
    assert _classify_severity("fractured wrist; surgery scheduled") == "severe"
    assert _classify_severity("right ankle sprain") == "moderate"
    assert _classify_severity("sore knee") == "minor"
    assert _classify_severity("returned to lineup") is None


def test_season_for_aug_threshold() -> None:
    assert _season_for(date(2024, 10, 22)) == "2024-25"
    assert _season_for(date(2025, 4, 14)) == "2024-25"
    assert _season_for(date(2025, 8, 1)) == "2025-26"
    # Boundary: late July belongs to the season ending that year.
    assert _season_for(date(2025, 7, 31)) == "2024-25"


def test_parse_pst_date_handles_whitespace() -> None:
    assert _parse_pst_date("2024-10-22") == date(2024, 10, 22)
    assert _parse_pst_date(" 2024-10-22 ") == date(2024, 10, 22)
    assert _parse_pst_date("") is None
    assert _parse_pst_date("not-a-date") is None


# ---------------------------------------------------------------------------
# Page parsing — fixture-based, no network
# ---------------------------------------------------------------------------

_FIXTURE_RESULTS_PAGE = """
<html><body>
<table>
  <tr>
    <th>Date</th><th>Team</th><th>Acquired</th><th>Relinquished</th><th>Notes</th>
  </tr>
  <tr>
    <td>2024-10-22</td><td>BOS</td><td></td>
    <td>• Jrue Holiday</td>
    <td>placed on IL with right shoulder soreness</td>
  </tr>
  <tr>
    <td>2024-11-05</td><td>BOS</td>
    <td>• Jrue Holiday</td><td></td>
    <td>activated from IL</td>
  </tr>
  <tr>
    <td>2024-11-10</td><td>LAL</td><td></td>
    <td>• LeBron James</td>
    <td>placed on IL with strained left hamstring</td>
  </tr>
  <tr>
    <td>2024-12-15</td><td>BOS</td><td></td>
    <td>• Jrue Holiday</td>
    <td>placed on IL with sore left knee</td>
  </tr>
</table>
</body></html>
"""


def test_parse_page_extracts_relinquished_and_acquired_events() -> None:
    scraper = ProSportsTransactionsScraper()
    events, has_next = scraper._parse_page(_FIXTURE_RESULTS_PAGE)

    assert has_next is False  # no "Next" link in fixture
    assert len(events) == 4

    relinquished = [e for e in events if e["kind"] == "relinquished"]
    acquired = [e for e in events if e["kind"] == "acquired"]
    assert len(relinquished) == 3
    assert len(acquired) == 1


def test_pair_events_resolves_oldest_first() -> None:
    """Per-player FIFO pairing: first relinquished pairs with first acquired."""
    scraper = ProSportsTransactionsScraper()
    events, _ = scraper._parse_page(_FIXTURE_RESULTS_PAGE)
    paired = scraper._pair_events(events)

    # Jrue: 2 relinquished + 1 acquired → 1 paired (shoulder/Oct), 1 still-open (knee/Dec)
    # LeBron: 1 relinquished + 0 acquired → 1 still-open (hamstring/Nov)
    assert len(paired) == 3

    jrue_paired = [p for p in paired if p["player_name"] == "Jrue Holiday" and p["resolved_on"]]
    assert len(jrue_paired) == 1
    closed = jrue_paired[0]
    assert closed["body_part"] == "shoulder"  # the EARLIEST injury closes first
    assert closed["started_on"] == date(2024, 10, 22)
    assert closed["resolved_on"] == date(2024, 11, 5)
    assert closed["severity"] == "minor"  # "soreness" pattern

    jrue_open = [p for p in paired if p["player_name"] == "Jrue Holiday" and p["resolved_on"] is None]
    assert len(jrue_open) == 1
    assert jrue_open[0]["body_part"] == "knee"

    lebron_open = [p for p in paired if p["player_name"] == "LeBron James"]
    assert len(lebron_open) == 1
    assert lebron_open[0]["body_part"] == "hamstring"
    assert lebron_open[0]["resolved_on"] is None


def test_fetch_handles_empty_results_window() -> None:
    """No matching results table = empty list, NOT an error."""
    empty_html = "<html><body><p>No results found.</p></body></html>"
    scraper = ProSportsTransactionsScraper()
    with patch.object(scraper, "get", return_value=empty_html):
        result = scraper.fetch_injuries(date(2020, 1, 1), date(2020, 1, 7))
        assert result == []


def test_scraper_error_propagates_on_http_failure() -> None:
    """HTTP errors in HttpScraper.get → ScraperError surfaces to caller."""
    scraper = ProSportsTransactionsScraper()
    with patch.object(scraper, "get", side_effect=ScraperError("blocked")):
        with pytest.raises(ScraperError):
            scraper.fetch_injuries(date(2020, 1, 1), date(2020, 1, 7))


# ---------------------------------------------------------------------------
# Ingestion-level fallback test
# ---------------------------------------------------------------------------

@pytest.fixture
def in_memory_db():
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


def _seed_player(session) -> int:
    from db.models import Player
    player = Player(id=2544, full_name="LeBron James", first_name="LeBron", last_name="James")
    session.add(player)
    session.commit()
    return player.id


def test_pst_ingestion_writes_paired_rows(in_memory_db) -> None:
    """When the scrape returns rows, ingestion writes them with source='prosportstransactions'."""
    from data.sync_injury_history import upsert_from_prosportstransactions
    from db.models import PlayerInjuryHistory

    _seed_player(in_memory_db)

    fake_rows = [{
        "player_name": "LeBron James",
        "body_part": "hamstring",
        "severity": "moderate",
        "started_on": date(2024, 11, 10),
        "resolved_on": date(2024, 12, 1),
        "team_abbr": "LAL",
        "diagnosis": "strained left hamstring",
        "source": "prosportstransactions",
    }]

    with patch(
        "data.sync_injury_history._fetch_pst_rows",
        return_value=fake_rows,
    ):
        result = upsert_from_prosportstransactions(
            in_memory_db, start_date=date(2024, 10, 1), end_date=date(2025, 6, 30), verbose=False
        )

    assert result["fallback_used"] is False
    assert result["inserted"] == 1
    row = in_memory_db.query(PlayerInjuryHistory).first()
    assert row.source == "prosportstransactions"
    assert row.body_part == "hamstring"
    assert row.season == "2024-25"
    assert row.games_missed is not None and row.games_missed > 0


def test_pst_ingestion_falls_back_to_seed_on_scrape_error(in_memory_db, tmp_path) -> None:
    """Scrape failure should silently fall back to seed CSV path."""
    from data.sync_injury_history import upsert_from_prosportstransactions, SEED_CSV_PATH

    _seed_player(in_memory_db)

    # Patch SEED_CSV_PATH to point at our test file.
    seed_csv = tmp_path / "seed.csv"
    seed_csv.write_text(
        "player_id,season,body_part,severity,started_on,resolved_on,games_missed,age_at_start,is_recurring,source\n"
        "2544,2023-24,knee,minor,2024-01-15,2024-01-25,5,39.0,false,seed_synthetic\n"
    )

    with patch(
        "data.sync_injury_history._fetch_pst_rows",
        side_effect=ScraperError("simulated PST block"),
    ), patch(
        "data.sync_injury_history.SEED_CSV_PATH", seed_csv
    ):
        result = upsert_from_prosportstransactions(
            in_memory_db, verbose=False
        )

    assert result["fallback_used"] is True
    assert result["inserted"] == 1


# ---------------------------------------------------------------------------
# Playwright integration — mocked browser, no network
# ---------------------------------------------------------------------------


def test_playwright_fetch_success_returns_html() -> None:
    """PlaywrightScraper.get() returns HTML content from mocked browser."""
    scraper = ProSportsTransactionsScraper()
    mock_cm = _make_playwright_mock("<html><body>Test content</body></html>")
    with patch("data.scrapers._base._sync_playwright", return_value=mock_cm):
        with patch.object(scraper, "_sleep_for_rate_limit"):
            result = scraper.get("https://prosportstransactions.com/basketball/Search/test")
    assert "Test content" in result


def test_playwright_timeout_raises_scraper_error() -> None:
    """PlaywrightScraper.get() wraps PlaywrightTimeoutError in ScraperError."""
    from data.scrapers._base import PlaywrightTimeoutError as PTError
    scraper = ProSportsTransactionsScraper()

    page_mock = MagicMock()
    page_mock.goto.side_effect = PTError("timed out")

    browser_mock = MagicMock()
    browser_mock.new_page.return_value = page_mock

    pw_mock = MagicMock()
    pw_mock.chromium.launch.return_value = browser_mock

    cm_mock = MagicMock()
    cm_mock.__enter__ = MagicMock(return_value=pw_mock)
    cm_mock.__exit__ = MagicMock(return_value=False)

    with patch("data.scrapers._base._sync_playwright", return_value=cm_mock):
        with patch.object(scraper, "_sleep_for_rate_limit"):
            with pytest.raises(ScraperError, match="(?i)timeout"):
                scraper.get("https://prosportstransactions.com/basketball/Search/test")


def test_playwright_generic_exception_raises_scraper_error() -> None:
    """PlaywrightScraper.get() wraps any unexpected exception in ScraperError."""
    scraper = ProSportsTransactionsScraper()

    pw_mock = MagicMock()
    pw_mock.chromium.launch.side_effect = RuntimeError("browser crash")

    cm_mock = MagicMock()
    cm_mock.__enter__ = MagicMock(return_value=pw_mock)
    cm_mock.__exit__ = MagicMock(return_value=False)

    with patch("data.scrapers._base._sync_playwright", return_value=cm_mock):
        with patch.object(scraper, "_sleep_for_rate_limit"):
            with pytest.raises(ScraperError):
                scraper.get("https://prosportstransactions.com/basketball/Search/test")
