"""Sprint 81 — Sports Reference College Basketball scraper tests."""
from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from data.scrapers._base import ScraperError  # noqa: E402
from data.scrapers.sportsreference_cbb import (  # noqa: E402
    SportsReferenceCBBScraper,
    _height_to_inches,
    _normalize_position,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_height_to_inches() -> None:
    assert _height_to_inches("6-5") == 77.0
    assert _height_to_inches("6'5\"") == 77.0
    assert _height_to_inches("6′5″") == 77.0  # unicode primes
    assert _height_to_inches("") is None
    assert _height_to_inches("not-a-height") is None


def test_normalize_position() -> None:
    assert _normalize_position("G") == "G"
    assert _normalize_position("F") == "F"
    assert _normalize_position("C") == "C"
    assert _normalize_position("G-F") == "G"
    assert _normalize_position("F-C") == "F"
    assert _normalize_position("") == "F"  # safe default


# ---------------------------------------------------------------------------
# Page parsing — fixture-based
# ---------------------------------------------------------------------------

# Leaders-page fixture exercising the live `_parse_leaders_page` path.
_FIXTURE_LEADERS_PAGE = """
<html><body>
<div id="leaders_pts_per_g">
  <span class="who">
    <a href="/cbb/players/cooper-flagg-1.html">Cooper Flagg</a>
    <small>Duke</small>
  </span>
  <span class="value">19.2</span>
  <span class="who">
    <a href="/cbb/players/dylan-harper-1.html">Dylan Harper</a>
    <small>Rutgers</small>
  </span>
  <span class="value">19.4</span>
  <span class="who">
    <a href="/cbb/players/low-scorer-1.html">Low Scorer</a>
    <small>State</small>
  </span>
  <span class="value">8.1</span>
</div>
</body></html>
"""

_FIXTURE_LEADERS_PAGE_COMMENT_WRAPPED = (
    "<html><body><div><!--" + _FIXTURE_LEADERS_PAGE + "--></div></body></html>"
)


# Legacy per-game stats fixture — exercises the retained `_parse_per_game_page`
# back-compat path. We use the actual Sports Reference data-stat attributes so
# the parser exercises its real path.
_FIXTURE_PAGE = """
<html><body>
<table id="per_game_stats">
  <thead>
    <tr><th>Rk</th><th>Player</th><th>Pos</th><th>School</th></tr>
    <tr>
      <th data-stat="ranker">Rk</th>
      <th data-stat="player">Player</th>
      <th data-stat="pos">Pos</th>
      <th data-stat="school_name">School</th>
      <th data-stat="g">G</th>
      <th data-stat="mp_per_g">MP</th>
      <th data-stat="pts_per_g">PTS</th>
      <th data-stat="trb_per_g">TRB</th>
      <th data-stat="ast_per_g">AST</th>
      <th data-stat="fg_pct">FG%</th>
      <th data-stat="fg3_pct">3P%</th>
      <th data-stat="ts_pct">TS%</th>
      <th data-stat="usg_pct">USG%</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td data-stat="ranker">1</td>
      <td data-stat="player">Cooper Flagg</td>
      <td data-stat="pos">F</td>
      <td data-stat="school_name">Duke</td>
      <td data-stat="g">37</td>
      <td data-stat="mp_per_g">30.7</td>
      <td data-stat="pts_per_g">19.2</td>
      <td data-stat="trb_per_g">7.5</td>
      <td data-stat="ast_per_g">4.2</td>
      <td data-stat="fg_pct">0.483</td>
      <td data-stat="fg3_pct">0.387</td>
      <td data-stat="ts_pct">0.612</td>
      <td data-stat="usg_pct">0.273</td>
    </tr>
    <tr>
      <td data-stat="ranker">2</td>
      <td data-stat="player">Dylan Harper</td>
      <td data-stat="pos">G</td>
      <td data-stat="school_name">Rutgers</td>
      <td data-stat="g">29</td>
      <td data-stat="mp_per_g">31.2</td>
      <td data-stat="pts_per_g">19.4</td>
      <td data-stat="trb_per_g">4.6</td>
      <td data-stat="ast_per_g">4.0</td>
      <td data-stat="fg_pct">0.485</td>
      <td data-stat="fg3_pct">0.330</td>
      <td data-stat="ts_pct">0.602</td>
      <td data-stat="usg_pct">0.295</td>
    </tr>
    <tr>
      <td data-stat="ranker">3</td>
      <td data-stat="player">Bench Walk-on</td>
      <td data-stat="pos">G</td>
      <td data-stat="school_name">Duke</td>
      <td data-stat="g">15</td>
      <td data-stat="mp_per_g">8.0</td>
      <td data-stat="pts_per_g">3.5</td>
      <td data-stat="trb_per_g">1.2</td>
      <td data-stat="ast_per_g">0.8</td>
      <td data-stat="fg_pct">0.420</td>
      <td data-stat="fg3_pct">0.300</td>
      <td data-stat="ts_pct">0.500</td>
      <td data-stat="usg_pct">0.150</td>
    </tr>
  </tbody>
</table>
</body></html>
"""


def test_parser_extracts_top_scorers_and_filters_low_ppg() -> None:
    scraper = SportsReferenceCBBScraper()
    rows = scraper._parse_per_game_page(_FIXTURE_PAGE, season_year=2026)

    # All 3 rows pre-filter
    assert len(rows) == 3

    flagg = next(r for r in rows if r["full_name"] == "Cooper Flagg")
    assert flagg["school"] == "Duke"
    assert flagg["primary_position"] == "F"
    assert flagg["ppg"] == 19.2
    assert flagg["fg3_pct"] == 0.387
    assert flagg["source"] == "sportsreference"
    assert flagg["external_id"] == "sr-cbb-2026-duke-cooper-flagg"
    assert flagg["gp"] == 37
    assert flagg["min_pg"] == 30.7


def test_fetch_top_prospects_filters_to_high_ppg() -> None:
    """fetch_top_prospects() should drop the <10 PPG walk-on row."""
    scraper = SportsReferenceCBBScraper()

    def _side_effect(url, **kwargs):
        if "leaders" in url:
            return _FIXTURE_LEADERS_PAGE
        return "<html><body></body></html>"

    with patch.object(scraper, "get", side_effect=_side_effect):
        rows = scraper.fetch_top_prospects(season_year=2026, top_n=10)

    assert len(rows) == 2  # Flagg + Harper, walk-on filtered out
    assert all(r["ppg"] >= 10 for r in rows)
    # Should be sorted PPG desc — Harper edges Flagg
    assert rows[0]["full_name"] == "Dylan Harper"
    assert rows[1]["full_name"] == "Cooper Flagg"


def test_fetch_raises_when_table_missing() -> None:
    """No leaders div = ScraperError = upstream fallback."""
    scraper = SportsReferenceCBBScraper()
    bad_html = "<html><body><p>blocked</p></body></html>"
    with patch.object(scraper, "get", return_value=bad_html):
        with pytest.raises(ScraperError):
            scraper.fetch_top_prospects(season_year=2026)


def test_fetch_handles_html_comment_wrapped_table() -> None:
    """SR sometimes wraps tables in HTML comments as anti-scrape; we should still parse."""
    scraper = SportsReferenceCBBScraper()

    def _side_effect(url, **kwargs):
        if "leaders" in url:
            return _FIXTURE_LEADERS_PAGE_COMMENT_WRAPPED
        return "<html><body></body></html>"

    with patch.object(scraper, "get", side_effect=_side_effect):
        rows = scraper.fetch_top_prospects(season_year=2026, top_n=10)
    assert len(rows) >= 2
    assert any(r["full_name"] == "Cooper Flagg" for r in rows)


def test_parse_leaders_page_extracts_names_and_ppg() -> None:
    from data.scrapers.sportsreference_cbb import SportsReferenceCBBScraper
    scraper = SportsReferenceCBBScraper()
    entries = scraper._parse_leaders_page(_FIXTURE_LEADERS_PAGE)
    assert len(entries) == 3
    names = [e[0] for e in entries]
    assert "Cooper Flagg" in names
    assert "Dylan Harper" in names
    ppg_map = {e[0]: e[2] for e in entries}
    assert ppg_map["Cooper Flagg"] == pytest.approx(19.2, abs=0.01)


def test_parse_leaders_page_handles_comment_wrapping() -> None:
    from data.scrapers.sportsreference_cbb import SportsReferenceCBBScraper
    scraper = SportsReferenceCBBScraper()
    entries = scraper._parse_leaders_page(_FIXTURE_LEADERS_PAGE_COMMENT_WRAPPED)
    assert len(entries) == 3


def test_fetch_top_prospects_filters_low_ppg() -> None:
    from data.scrapers.sportsreference_cbb import SportsReferenceCBBScraper
    scraper = SportsReferenceCBBScraper()

    def _side_effect(url, **kwargs):
        if "leaders" in url:
            return _FIXTURE_LEADERS_PAGE
        return "<html><body></body></html>"

    with patch.object(scraper, "get", side_effect=_side_effect):
        rows = scraper.fetch_top_prospects(season_year=2026)

    names = [r["full_name"] for r in rows]
    assert "Low Scorer" not in names
    assert len(rows) == 2


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


def test_sync_uses_sportsreference_when_scrape_succeeds(in_memory_db) -> None:
    from data.sync_draft_prospects import sync_sportsreference
    from db.models import DraftProspect, DraftProspectStat

    fake_rows = [{
        "external_id": "sr-cbb-2026-duke-cooper-flagg",
        "full_name": "Cooper Flagg",
        "school": "Duke",
        "school_type": "ncaa",
        "primary_position": "F",
        "consensus_rank": None,
        "age": None,
        "height_inches": None,
        "weight_lbs": None,
        "wingspan": None,
        "ppg": 19.2,
        "rpg": 7.5,
        "apg": 4.2,
        "fg_pct": 0.483,
        "fg3_pct": 0.387,
        "ts_pct": 0.612,
        "usg_pct": 0.273,
        "gp": 37,
        "min_pg": 30.7,
        "source": "sportsreference",
    }]

    with patch(
        "data.sync_draft_prospects._fetch_sportsreference_rows",
        return_value=fake_rows,
    ):
        result = sync_sportsreference(
            in_memory_db, draft_year=2026, season="2025-26"
        )

    assert result["fallback_used"] is False
    assert result["prospects"] == 1
    prospect = in_memory_db.query(DraftProspect).first()
    assert prospect.full_name == "Cooper Flagg"
    stat = in_memory_db.query(DraftProspectStat).first()
    assert stat.source == "sportsreference"
    assert stat.gp == 37
    assert stat.pts_pg == 19.2


def test_sync_falls_back_to_seed_csv_on_scrape_error(in_memory_db, tmp_path) -> None:
    from data.sync_draft_prospects import sync_sportsreference
    from db.models import DraftProspect

    fallback_csv = tmp_path / "draft_prospects.csv"
    fallback_csv.write_text(
        "external_id,full_name,age,height_inches,weight_lbs,primary_position,school,school_type,consensus_rank,ppg,rpg,apg,fg_pct,fg3_pct,ts_pct,usg_pct,wingspan\n"
        "test-1,Test Prospect,19.0,78,210,F,Test U,ncaa,1,18.5,7.5,3.0,0.48,0.36,0.59,0.26,82\n"
    )

    with patch(
        "data.sync_draft_prospects._fetch_sportsreference_rows",
        side_effect=ScraperError("simulated SR block"),
    ):
        result = sync_sportsreference(
            in_memory_db,
            draft_year=2026,
            season="2025-26",
            fallback_csv_path=str(fallback_csv),
        )

    assert result["fallback_used"] is True
    assert result["source"] == "seed_csv"
    assert result["prospects"] == 1
    prospect = in_memory_db.query(DraftProspect).first()
    assert prospect.full_name == "Test Prospect"
