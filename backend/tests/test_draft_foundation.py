"""Sprint 100 (Stream A) — schema, classifier, and linkage-service tests.

Scope: pure-logic tests + ORM-class shape. The scraper + ingest tests
live in Stream B (`test_draft_scrapers.py`); the v2 service tests live
in Stream C (`test_draft_services.py`).
"""

from __future__ import annotations

import pytest

from services.draft_outcome_classifier import classify_outcome, tier_rank
from services.draft_linkage_service import normalize_name, resolve_player_id


# ── classify_outcome ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        # Empty input → bust.
        ({}, "bust"),
        # Played a bit, never started → role_player.
        ({"career_games": 250, "career_minutes": 4000, "career_ws": 8.0}, "role_player"),
        # Long-tenured but never started → role_player by games threshold.
        ({"career_games": 500, "career_minutes": 6000, "career_ws": 3.0}, "role_player"),
        # Starter — 30+ WS, 8000+ minutes, no All-Star.
        ({"career_games": 600, "career_minutes": 18000, "career_ws": 60.0}, "starter"),
        # Star — at least 3 All-Stars but no All-NBA.
        ({"career_games": 700, "career_ws": 90.0, "all_star_selections": 4}, "star"),
        # Star — at least 1 All-NBA selection.
        ({"career_ws": 90.0, "all_nba_selections": 1, "all_star_selections": 2}, "star"),
        # Superstar — 3+ All-NBA selections.
        ({"career_ws": 130.0, "all_nba_selections": 3, "all_star_selections": 5}, "superstar"),
        # Superstar — 8+ All-Star appearances.
        ({"career_ws": 120.0, "all_star_selections": 9}, "superstar"),
    ],
)
def test_classify_outcome_table_driven(kwargs, expected):
    assert classify_outcome(**kwargs) == expected


def test_classify_outcome_handles_none_as_zero():
    assert classify_outcome(career_games=None, career_minutes=None, career_ws=None) == "bust"


def test_tier_rank_ordering():
    """Tier rank should produce a strict ordering for sorts."""
    tiers = ["superstar", "star", "starter", "role_player", "bust"]
    ranks = [tier_rank(t) for t in tiers]
    assert ranks == sorted(ranks, reverse=True)
    assert tier_rank(None) == 0
    assert tier_rank("nonsense") == 0


# ── normalize_name ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("P.J. Washington Jr.", "pj washington"),
        ("PJ Washington Jr.", "pj washington"),
        ("P.J. Washington", "pj washington"),
        ("PJ Washington", "pj washington"),
        ("Mohamed Diawara", "mohamed diawara"),
        ("Luka Dončić", "luka dončić"),  # unicode preserved
        ("Marcus Smart  ", "marcus smart"),
        ("RAYMOND Felton III", "raymond felton"),
    ],
)
def test_normalize_name_strips_punctuation_and_suffixes(raw, expected):
    assert normalize_name(raw) == expected


# ── resolve_player_id ─────────────────────────────────────────────────


def test_resolve_player_id_exact_match(test_db_session):
    """Exact normalized-name match returns the player with auto_name_year confidence."""
    from db.models import Player

    p = Player(id=999_001, full_name="P.J. Washington", position="F")
    test_db_session.add(p)
    test_db_session.commit()

    pid, method, conf = resolve_player_id(
        test_db_session, "PJ Washington Jr.", draft_year=2019
    )
    assert pid == 999_001
    assert method == "auto_name_year"
    assert conf == 1.00


def test_resolve_player_id_no_match(test_db_session):
    """A name with no candidate returns unmatched."""
    pid, method, conf = resolve_player_id(
        test_db_session, "Nonexistent Prospect McName", draft_year=2026
    )
    assert pid is None
    assert method == "unmatched"
    assert conf == 0.0


def test_resolve_player_id_ambiguous_returns_unmatched(test_db_session):
    """Multiple exact matches → returns unmatched (never silently links).

    The service also emits a WARNING log for operator visibility; we don't
    assert on caplog here because pytest's caplog capture depends on the
    project's logging setup (structlog via utils/logging_setup.py) and the
    behavioural contract (don't silently link) is what protects the comp
    model from contamination.
    """
    from db.models import Player

    test_db_session.add(Player(id=999_010, full_name="Marcus Williams"))
    test_db_session.add(Player(id=999_011, full_name="Marcus Williams"))
    test_db_session.commit()

    pid, method, conf = resolve_player_id(test_db_session, "Marcus Williams")
    assert pid is None
    assert method == "unmatched"
    assert conf == 0.0


def test_resolve_player_id_empty_name(test_db_session):
    pid, method, conf = resolve_player_id(test_db_session, "   ", draft_year=2026)
    assert pid is None
    assert method == "unmatched"


# ── ORM shape (smoke) ─────────────────────────────────────────────────


def test_new_orm_classes_importable():
    """All four new ORM classes from Sprint 100 Stream A import + have a __tablename__."""
    from db.models import (
        DraftMockRanking,
        DraftOutcome,
        DraftProspectLinkage,
        DraftInternationalStat,
    )

    assert DraftMockRanking.__tablename__ == "draft_mock_rankings"
    assert DraftOutcome.__tablename__ == "draft_outcomes"
    assert DraftProspectLinkage.__tablename__ == "draft_prospect_linkage"
    assert DraftInternationalStat.__tablename__ == "draft_international_stats"


def test_draft_prospect_new_columns_present():
    """The additive Sprint 100 columns appear on the ORM model."""
    from db.models import DraftProspect

    cols = {c.name for c in DraftProspect.__table__.columns}
    assert "draft_pick_number" in cols
    assert "draft_pick_team_id" in cols
    assert "is_historical" in cols
    assert "consensus_rank_float" in cols
    assert "consensus_variance" in cols


def test_measurement_new_attribution_columns():
    from db.models import DraftProspectMeasurement

    cols = {c.name for c in DraftProspectMeasurement.__table__.columns}
    for expected in ("combine_year", "source_url", "as_of"):
        assert expected in cols, f"missing {expected}"
