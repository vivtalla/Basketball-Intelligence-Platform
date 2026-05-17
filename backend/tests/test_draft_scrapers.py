"""Sprint 100 (Stream B) — scraper + ingestion tests.

All scraper tests run with ``BIP_SCRAPER_FIXTURE_MODE=1`` so no live
network calls are made. Fixtures live under
``backend/tests/fixtures/scrapers/<scraper>/``.

The consensus aggregator is pure-function, so it gets fully covered
without any scraper at all.
"""
from __future__ import annotations

import os
import pytest

from data.scrapers.mock_drafts._consensus import compute_consensus, normalize_name
from data.scrapers.nba_combine import NBACombineScraper


@pytest.fixture(autouse=True)
def _fixture_mode_env(monkeypatch):
    """Force every scraper.get() call to route to fixture files for these tests."""
    monkeypatch.setenv("BIP_SCRAPER_FIXTURE_MODE", "1")
    yield


# ── consensus aggregator ──────────────────────────────────────────────


def test_normalize_name_matches_linkage_service():
    """Consensus name normalization should match the linkage-service one
    so prospects line up across sources without surprise mismatches."""
    assert normalize_name("P.J. Washington Jr.") == "pj washington"
    assert normalize_name("Mohamed Diawara") == "mohamed diawara"


def test_compute_consensus_single_source():
    payload = [{
        "source": "espn",
        "rankings": [
            {"rank": 1, "name": "Cooper Flagg"},
            {"rank": 2, "name": "Dylan Harper"},
        ],
    }]
    result = compute_consensus(payload)
    flagg = result["cooper flagg"]
    assert flagg["mean_rank"] == 1.0
    assert flagg["stddev_rank"] == 0.0
    assert flagg["source_count"] == 1
    assert flagg["sources_ranked"] == ["espn"]


def test_compute_consensus_two_sources_agree():
    payloads = [
        {"source": "espn", "rankings": [{"rank": 1, "name": "Cooper Flagg"}, {"rank": 2, "name": "Dylan Harper"}]},
        {"source": "cbs", "rankings": [{"rank": 1, "name": "Cooper Flagg"}, {"rank": 2, "name": "Dylan Harper"}]},
    ]
    result = compute_consensus(payloads)
    assert result["cooper flagg"]["mean_rank"] == 1.0
    assert result["cooper flagg"]["stddev_rank"] == 0.0
    assert result["cooper flagg"]["source_count"] == 2


def test_compute_consensus_two_sources_disagree():
    payloads = [
        {"source": "espn", "rankings": [{"rank": 1, "name": "Cooper Flagg"}, {"rank": 3, "name": "Dylan Harper"}]},
        {"source": "cbs", "rankings": [{"rank": 3, "name": "Cooper Flagg"}, {"rank": 1, "name": "Dylan Harper"}]},
    ]
    result = compute_consensus(payloads)
    flagg = result["cooper flagg"]
    # (1 + 3) / 2 = 2.0; spread is 1.0.
    assert flagg["mean_rank"] == 2.0
    assert flagg["stddev_rank"] == 1.0
    assert flagg["source_count"] == 2


def test_compute_consensus_missing_source_treated_as_deepest_plus_one():
    """A prospect ranked by ESPN but missed by CBS should get a CBS rank
    of ``deepest_CBS_rank + 1``, inflating their variance vs prospects
    on every source."""
    payloads = [
        {"source": "espn", "rankings": [{"rank": 1, "name": "Cooper Flagg"}, {"rank": 30, "name": "Late Bloomer"}]},
        {"source": "cbs", "rankings": [{"rank": 1, "name": "Cooper Flagg"}]},  # CBS only lists Flagg
    ]
    result = compute_consensus(payloads)
    # Cooper Flagg: ranked 1 by both → mean=1, stddev=0.
    assert result["cooper flagg"]["mean_rank"] == 1.0
    # Late Bloomer: ESPN=30, CBS=(deepest_CBS=1)+1=2 → mean=16.0, large stddev.
    late = result["late bloomer"]
    assert late["mean_rank"] == 16.0
    assert late["stddev_rank"] > 13.0  # large because of the spread
    assert late["source_count"] == 1  # only one source actually ranked them


def test_compute_consensus_display_name_uses_majority_spelling():
    payloads = [
        {"source": "espn", "rankings": [{"rank": 1, "name": "PJ Washington Jr."}]},
        {"source": "cbs", "rankings": [{"rank": 1, "name": "P.J. Washington"}]},
        {"source": "nbadraft_net", "rankings": [{"rank": 1, "name": "P.J. Washington"}]},
    ]
    result = compute_consensus(payloads)
    # Majority spelling is "P.J. Washington".
    assert result["pj washington"]["display_name"] == "P.J. Washington"


def test_compute_consensus_empty():
    assert compute_consensus([]) == {}


# ── NBA Combine scraper (fixture-mode) ────────────────────────────────


def test_nba_combine_parses_fixture():
    scraper = NBACombineScraper()
    measurements = scraper.fetch_combine(draft_year=2026, fixture_name="2026_response.json")
    assert len(measurements) == 3
    flagg = measurements[0]
    assert flagg["full_name"] == "Cooper Flagg"
    assert flagg["normalized_name"] == "cooper flagg"
    assert flagg["combine_year"] == 2026
    assert flagg["height_with_shoes"] == 80.0
    assert flagg["wingspan"] == 84.5
    assert flagg["max_vert"] == 38.5
    assert flagg["source"] == "nba_combine"
    assert flagg["source_url"].startswith("https://www.nba.com/")
    # Bench press is null in the fixture; ensure conversion didn't blow up.
    assert flagg["bench_press_135"] is None


def test_nba_combine_attribution_present_on_every_row():
    scraper = NBACombineScraper()
    measurements = scraper.fetch_combine(draft_year=2026, fixture_name="2026_response.json")
    for m in measurements:
        assert m.get("source")
        assert m.get("source_url")
        assert m.get("combine_year") == 2026


# ── fixture-mode plumbing in scraper base ─────────────────────────────


def test_fixture_mode_raises_when_fixture_missing():
    """A scraper asked for a fixture that doesn't exist should raise
    ScraperError loudly rather than silently falling back to HTTP."""
    from data.scrapers._base import ScraperError
    scraper = NBACombineScraper()
    with pytest.raises(ScraperError):
        scraper.fetch_combine(draft_year=2026, fixture_name="does_not_exist.json")
