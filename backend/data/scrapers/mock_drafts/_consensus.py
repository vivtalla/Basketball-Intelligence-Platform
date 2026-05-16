"""Sprint 100 (Stream B) — mock-draft consensus aggregator.

Pure function: takes a list of ``{source, rankings: [...]}`` payloads and
returns per-prospect-name aggregates suitable for writing onto
``DraftProspect.consensus_rank_float`` and ``consensus_variance``.

Name matching uses the same normalization as draft_linkage_service: lower-
case, punctuation stripped, suffixes (Jr./Sr./III) removed. We deliberately
fuzzy-match by normalized name rather than ID because mock-draft sources
don't share player IDs.

Missing prospects on a source are treated as "rank = N+1" where N is the
deepest ranking that source produced — i.e., "unranked" pushes variance
up rather than letting that source disappear silently. This rewards
consensus across sources and penalizes prospects ranked by only one site.
"""
from __future__ import annotations

import logging
import re
import statistics
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def normalize_name(name: str) -> str:
    s = (name or "").strip()
    s = re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def compute_consensus(
    source_payloads: List[Dict[str, Any]],
    treat_unranked_as_deepest_plus_one: bool = True,
) -> Dict[str, Dict[str, Any]]:
    """Aggregate multiple mock-draft sources into per-prospect consensus.

    Args:
        source_payloads: list of ``{source, source_url, as_of, rankings}``
            dicts. ``rankings`` items must have ``name`` and ``rank``.
        treat_unranked_as_deepest_plus_one: when True (default), prospects
            ranked by some sources but not others are assigned
            ``deepest_rank + 1`` on the missing sources before aggregating.
            This inflates variance for partially-ranked prospects and
            keeps the math comparable across sources.

    Returns:
        ``{normalized_name: {
            "display_name": str,             # most-common spelling
            "mean_rank": float,
            "stddev_rank": float,            # population stddev; 0.0 if 1 source
            "source_count": int,             # actual rankings (not includes inferred)
            "sources_ranked": List[str],     # source ids that had a real rank
            "per_source_ranks": Dict[str, int],
        }}``

    Empty input or per-source ``rankings: []`` returns ``{}``.
    """
    if not source_payloads:
        return {}

    # Pass 1 — build {normalized_name: {source: rank}} + figure out the deepest
    # rank seen on each source so unranked can be inferred.
    per_prospect: Dict[str, Dict[str, Any]] = {}
    deepest_per_source: Dict[str, int] = {}
    for payload in source_payloads:
        source = payload.get("source")
        if not source:
            continue
        rankings = payload.get("rankings") or []
        if not rankings:
            logger.warning("compute_consensus: source=%s returned 0 rankings", source)
            continue
        # Track deepest rank for this source.
        deepest = max(int(r["rank"]) for r in rankings if r.get("rank"))
        deepest_per_source[source] = deepest
        for entry in rankings:
            name = entry.get("name")
            rank = entry.get("rank")
            if not name or rank is None:
                continue
            key = normalize_name(name)
            slot = per_prospect.setdefault(
                key,
                {"display_name": name, "name_votes": {}, "per_source_ranks": {}},
            )
            # Choose the most-common original spelling.
            slot["name_votes"][name] = slot["name_votes"].get(name, 0) + 1
            slot["per_source_ranks"][source] = int(rank)

    # Pass 2 — compute mean/stddev. If treat_unranked_as_deepest_plus_one,
    # fill missing sources with deepest_for_that_source + 1.
    sources_present = list(deepest_per_source.keys())
    output: Dict[str, Dict[str, Any]] = {}
    for key, slot in per_prospect.items():
        ranks_for_stats: List[int] = []
        for source in sources_present:
            r = slot["per_source_ranks"].get(source)
            if r is not None:
                ranks_for_stats.append(r)
            elif treat_unranked_as_deepest_plus_one:
                ranks_for_stats.append(deepest_per_source[source] + 1)
            # else: skip this source for this prospect

        if not ranks_for_stats:
            continue
        mean_rank = statistics.fmean(ranks_for_stats)
        # Population stddev (matches "spread across sources" intuition);
        # with N=1 sample defaults to 0.0.
        if len(ranks_for_stats) > 1:
            stddev_rank = statistics.pstdev(ranks_for_stats)
        else:
            stddev_rank = 0.0

        # Most-common original spelling — fall back to first seen if tie.
        display_name = max(slot["name_votes"].items(), key=lambda kv: kv[1])[0]
        sources_ranked = sorted(slot["per_source_ranks"].keys())

        output[key] = {
            "display_name": display_name,
            "mean_rank": round(mean_rank, 2),
            "stddev_rank": round(stddev_rank, 2),
            "source_count": len(slot["per_source_ranks"]),
            "sources_ranked": sources_ranked,
            "per_source_ranks": dict(slot["per_source_ranks"]),
        }
    return output


__all__ = ["compute_consensus", "normalize_name"]
