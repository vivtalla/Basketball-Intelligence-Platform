"""Sprint 100 (Stream B) — mock-draft consensus scrapers.

Three public sources, deliberately small. Paywalled sources (Ringer,
The Athletic) are out of scope — see ``specs/sprint-100-closeout.md``.

Each scraper returns a uniform shape::

    {
        "source": "espn" | "nbadraft_net" | "cbs",
        "source_url": str,
        "as_of": ISO datetime,
        "draft_year": int,
        "rankings": [
            {"rank": int, "name": str, "school": Optional[str],
             "position": Optional[str], "tier": Optional[str],
             "comp": Optional[str]},
            ...
        ],
    }

``_consensus.compute_consensus`` aggregates these into per-prospect
``(mean_rank, stddev_rank, source_count)`` used by Stream C's analysis
service and the denormalized ``DraftProspect.consensus_rank_float`` /
``consensus_variance`` columns.
"""
from .espn import ESPNMockDraftScraper
from .nbadraft_net import NBADraftNetScraper
from .cbs import CBSMockDraftScraper
from ._consensus import compute_consensus

__all__ = [
    "ESPNMockDraftScraper",
    "NBADraftNetScraper",
    "CBSMockDraftScraper",
    "compute_consensus",
]
