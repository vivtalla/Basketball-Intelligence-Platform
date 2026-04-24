"""Sprint 65 — scouting claim inference confidence + opponent-aware ranking.

These tests exercise the pure helper functions `_compute_claim_confidence` and
`_rank_claims_by_confidence` — they do not need a DB because they operate on
already-assembled ScoutingClaim/ScoutingSection objects.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models.scouting import ScoutingClaim, ScoutingEvidence, ScoutingSection  # noqa: E402
from routers.scouting import (  # noqa: E402
    _compute_claim_confidence,
    _rank_claims_by_confidence,
)


def _claim(claim_id: str, evidence_count: int = 2) -> ScoutingClaim:
    return ScoutingClaim(
        claim_id=claim_id,
        title=f"Claim {claim_id}",
        summary=f"Summary for {claim_id}",
        evidence=[
            ScoutingEvidence(label=f"ev-{i}", value=float(i), context=f"ctx-{i}")
            for i in range(evidence_count)
        ],
    )


def test_confidence_high_requires_anchors_opponent_and_diverse_linkage():
    claim = _claim("c1", evidence_count=2)
    conf = _compute_claim_confidence(
        claim=claim,
        anchored_event_count=4,
        opponent_specific_event_count=2,
        linkage_tiers={"derived", "timeline"},
    )
    assert conf.level == "high"
    assert conf.anchored_event_count == 4
    assert conf.opponent_specific_event_count == 2
    # Reasons should mention both the play count and opponent specificity.
    joined = " ".join(conf.reasons)
    assert "4 matching plays" in joined
    assert "2 from direct" in joined


def test_confidence_medium_for_single_anchored_event_without_opponent_support():
    claim = _claim("c2", evidence_count=1)
    conf = _compute_claim_confidence(
        claim=claim,
        anchored_event_count=1,
        opponent_specific_event_count=0,
        linkage_tiers={"derived"},
    )
    assert conf.level == "medium"
    assert any("matching" in r for r in conf.reasons)


def test_confidence_medium_for_opponent_support_without_anchored_events():
    claim = _claim("c3", evidence_count=2)
    conf = _compute_claim_confidence(
        claim=claim,
        anchored_event_count=0,
        opponent_specific_event_count=1,
        linkage_tiers=set(),
    )
    assert conf.level == "medium"


def test_confidence_low_when_no_anchors_and_sparse_evidence():
    claim = _claim("c4", evidence_count=0)
    conf = _compute_claim_confidence(
        claim=claim,
        anchored_event_count=0,
        opponent_specific_event_count=0,
        linkage_tiers=set(),
    )
    assert conf.level == "low"
    joined = " ".join(conf.reasons)
    assert "no event-level plays matched" in joined
    assert "limited season-level evidence records" in joined


def test_rank_claims_promotes_opponent_specific_above_higher_general_n():
    """A claim with 2 opponent-specific events should outrank a higher-general-N claim."""
    general = _claim("general")
    opp_specific = _claim("opp")
    general.inference_confidence = _compute_claim_confidence(
        claim=general,
        anchored_event_count=5,
        opponent_specific_event_count=0,
        linkage_tiers={"derived"},
    )
    opp_specific.inference_confidence = _compute_claim_confidence(
        claim=opp_specific,
        anchored_event_count=3,
        opponent_specific_event_count=2,
        linkage_tiers={"derived", "timeline"},
    )
    # opp_specific has the prereqs for "high"; general is stuck at "medium" (no opponent).
    assert opp_specific.inference_confidence.level == "high"
    assert general.inference_confidence.level == "medium"

    section = ScoutingSection(eyebrow="E", title="T", claims=[general, opp_specific])
    _rank_claims_by_confidence([section])
    assert section.claims[0].claim_id == "opp"
    assert section.claims[1].claim_id == "general"


def test_rank_claims_falls_back_to_anchored_count_at_equal_confidence():
    a = _claim("a", evidence_count=1)
    b = _claim("b", evidence_count=1)
    a.inference_confidence = _compute_claim_confidence(
        claim=a, anchored_event_count=1, opponent_specific_event_count=0, linkage_tiers={"derived"}
    )
    b.inference_confidence = _compute_claim_confidence(
        claim=b, anchored_event_count=2, opponent_specific_event_count=0, linkage_tiers={"derived"}
    )
    assert a.inference_confidence.level == b.inference_confidence.level == "medium"
    section = ScoutingSection(eyebrow="E", title="T", claims=[a, b])
    _rank_claims_by_confidence([section])
    assert [c.claim_id for c in section.claims] == ["b", "a"]


def test_rank_claims_handles_missing_confidence_gracefully():
    a = _claim("a")
    # Intentionally leave inference_confidence=None on one claim.
    b = _claim("b")
    b.inference_confidence = _compute_claim_confidence(
        claim=b, anchored_event_count=3, opponent_specific_event_count=1, linkage_tiers={"derived", "timeline"}
    )
    section = ScoutingSection(eyebrow="E", title="T", claims=[a, b])
    _rank_claims_by_confidence([section])
    # b is high confidence; a has no record — a should sort to the bottom.
    assert section.claims[0].claim_id == "b"
    assert section.claims[1].claim_id == "a"
