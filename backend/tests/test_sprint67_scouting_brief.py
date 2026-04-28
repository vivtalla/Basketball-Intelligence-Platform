"""Sprint 67 (B7/B9b) — scouting brief composition tests.

Covers:
  - archetype-powered Role and Strengths cards render
  - brief is graceful when sources are missing (cards skipped, warnings populated)
  - card ordering matches spec §2.8
  - deep_link fields exist and are non-empty
"""
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models.archetype import ArchetypeContributor, ArchetypeSample, PlayerArchetype  # noqa: E402
from models.scouting_brief import ScoutingBriefResponse  # noqa: E402
from services.scouting_brief_service import (  # noqa: E402
    METHODOLOGY_VERSION,
    _role_card,
    _strengths_card,
    build_scouting_brief,
)


def _archetype(
    archetype_key: str = "heliocentric_creator",
    label: str = "Heliocentric Creator",
    confidence: str = "high",
) -> PlayerArchetype:
    return PlayerArchetype(
        player_id=1, season="2024-25",
        archetype_key=archetype_key, label=label, confidence=confidence,
        reason="High usage, elite playmaking, and above-average efficiency.",
        contributors=[
            ArchetypeContributor(feature_key="usg_z", label="Usage rate", value=32.0, z=1.80, direction="above"),
            ArchetypeContributor(feature_key="ast_rate_z", label="Assists per 36", value=9.5, z=1.50, direction="above"),
            ArchetypeContributor(feature_key="obpm_z", label="Offensive BPM", value=7.0, z=1.40, direction="above"),
            ArchetypeContributor(feature_key="ftr_z", label="Free-throw rate", value=0.12, z=-0.90, direction="below"),
        ],
        sample=ArchetypeSample(gp=70, min_pg=34.0, peer_pool_size=340),
        methodology_version="player_archetype_v2",
    )


# --- Unit tests on the card builders ---------------------------------------


def test_role_card_populates_summary_and_evidence():
    card = _role_card(_archetype())
    assert card is not None
    assert card.card_type == "role"
    assert card.title == "Role"
    assert "Heliocentric Creator" in card.summary
    assert card.confidence == "high"
    assert len(card.evidence) == 3  # top 3 contributors
    assert card.deep_link.startswith("/players/")


def test_role_card_skipped_for_developmental():
    arch = _archetype(archetype_key="developmental", label="Developmental", confidence="low")
    assert _role_card(arch) is None


def test_strengths_card_renders_one_up_one_down():
    card = _strengths_card(_archetype())
    assert card is not None
    assert card.card_type == "strengths"
    assert "Leans into" in card.summary
    assert "lags" in card.summary


# --- End-to-end brief build -------------------------------------------------


def test_brief_is_graceful_when_all_sources_fail(monkeypatch):
    """If every downstream service raises, the brief still returns a valid
    response with zero cards and one warning per skipped card."""

    # Mock classify_player_archetype to raise
    import services.scouting_brief_service as module

    def _raise_arch(*args, **kwargs):
        raise RuntimeError("archetype service down")

    def _raise_opp(*args, **kwargs):
        raise RuntimeError("opportunity service down")

    def _raise_traj(*args, **kwargs):
        raise RuntimeError("trajectory service down")

    # Patch at the import sites used inside build_scouting_brief.
    monkeypatch.setattr(
        "services.player_archetype_service.classify_player_archetype",
        _raise_arch,
    )
    monkeypatch.setattr(
        "services.opportunity_service.build_opportunity_report",
        _raise_opp,
    )
    monkeypatch.setattr(
        "services.trajectory_service.build_trajectory_report",
        _raise_traj,
    )

    # Use a null DB-like object; every downstream call raises before touching db.
    class _NullDB:
        def query(self, *a, **kw):
            raise RuntimeError("no db")

    result: ScoutingBriefResponse = build_scouting_brief(
        _NullDB(), player_id=999, season="2024-25"
    )
    assert result.methodology_version == METHODOLOGY_VERSION
    assert result.cards == []
    assert any("archetype" in w for w in result.warnings)
    assert any("usage_efficiency" in w for w in result.warnings)
    assert any("shot_profile" in w for w in result.warnings)
    assert any("trajectory" in w for w in result.warnings)


def test_brief_card_ordering_matches_spec(monkeypatch):
    """When every source succeeds, cards render in spec §2.8 order:
    role → strengths → usage_efficiency → shot_profile → trajectory."""
    arch = _archetype()

    monkeypatch.setattr(
        "services.player_archetype_service.classify_player_archetype",
        lambda db, pid, season: arch,
    )
    # Opportunity + trajectory + shot services return None/fail — those cards
    # get skipped, but we at least verify role + strengths order.
    monkeypatch.setattr(
        "services.opportunity_service.build_opportunity_report",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "services.trajectory_service.build_trajectory_report",
        lambda **kwargs: None,
    )

    class _NullDB:
        def query(self, *a, **kw):
            class _Q:
                def filter(self, *a, **kw): return self
                def first(self): return None
            return _Q()

    result = build_scouting_brief(_NullDB(), player_id=1, season="2024-25")
    types = [c.card_type for c in result.cards]
    # Only role + strengths survive this mock setup; both are archetype-powered.
    assert types == ["role", "strengths"]
