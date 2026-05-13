#!/usr/bin/env python3
"""Sprint 99 — Pre-warm /api/mvp/race so users never hit a cold cache.

The MVP race composite takes ~10s on a cold backend cache. Cloudflare
edge-caches the response for 4 hours, but the first user after a deploy
or after the TTL expires still pays the full origin cost. Sprint 99's
in-process TTL cache helps within a single gunicorn worker, but the
cron warmer is what eliminates the user-visible cold entirely: hit the
public endpoint a few times so Cloudflare AND both gunicorn workers
have a hot cache.

Designed to run from ``daily_sync.sh`` after the daily run completes,
and from its own cron entry every 3 hours (within the 4-hour TTL).

Usage:
    python backend/scripts/warm_mvp_cache.py
    python backend/scripts/warm_mvp_cache.py --base-url https://api.courtvue.app
    python backend/scripts/warm_mvp_cache.py --season 2025-26

Idempotent. Non-fatal on individual request failures — logs and moves on
so a transient network blip doesn't break the cron tick.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from typing import List, Tuple
from urllib.parse import urlencode

import requests


DEFAULT_BASE_URL = os.environ.get("BIP_API_BASE", "https://api.courtvue.app")
# Two requests per variant — enough to warm both gunicorn workers in
# production (round-robin'd by Caddy). Cloudflare caches on the first
# successful response.
# 3 passes: first two hit MISS as both gunicorn workers warm up; the third
# typically lands on the Cloudflare-cached response (HIT). Verified
# empirically during Sprint 99 deployment.
WARM_PASSES = 3
REQUEST_TIMEOUT = 60  # cold-cache compute is ~10s; allow headroom


def _resolve_default_season() -> str:
    """Mirror the season resolution from daily_sync.sh + nba_client."""
    from datetime import datetime

    now = datetime.utcnow()
    start_year = now.year if now.month >= 8 else now.year - 1
    return f"{start_year}-{str((start_year + 1) % 100).zfill(2)}"


def _build_variants(season: str) -> List[Tuple[str, dict]]:
    """Request shapes to warm. Each tuple is (label, query_params).

    The frontend defaults are top=10 + season_type=Regular Season; the
    same season also rolls a Playoffs view during postseason. Warming
    both keeps the page snappy regardless of which the user clicks.
    """
    return [
        ("regular-season-default", {"season": season, "top": 10}),
        ("playoffs-default", {"season": season, "top": 10, "season_type": "Playoffs"}),
    ]


def warm_endpoint(
    base_url: str,
    season: str,
    *,
    passes: int = WARM_PASSES,
    timeout: int = REQUEST_TIMEOUT,
    log=logging.getLogger("warm_mvp_cache"),
) -> dict:
    """Hit /api/mvp/race ``passes`` times for each variant. Returns a summary."""
    base_url = base_url.rstrip("/")
    summary = {"requests": 0, "successes": 0, "failures": 0, "variants": []}

    for label, params in _build_variants(season):
        for pass_index in range(passes):
            url = f"{base_url}/api/mvp/race?{urlencode(params)}"
            start = time.perf_counter()
            summary["requests"] += 1
            try:
                resp = requests.get(url, timeout=timeout)
                duration = time.perf_counter() - start
                resp.raise_for_status()
                cf_status = resp.headers.get("cf-cache-status", "—")
                age = resp.headers.get("age", "—")
                size = resp.headers.get("content-length", "?")
                log.info(
                    "warmed %s (pass %d/%d) in %.2fs cf=%s age=%s size=%s",
                    label, pass_index + 1, passes, duration, cf_status, age, size,
                )
                summary["successes"] += 1
                summary["variants"].append(
                    {"label": label, "pass": pass_index + 1, "duration_s": round(duration, 2),
                     "cf_status": cf_status, "age": age}
                )
            except Exception as exc:  # noqa: BLE001 — non-fatal
                duration = time.perf_counter() - start
                log.warning("warm %s pass %d failed after %.2fs: %s",
                            label, pass_index + 1, duration, exc)
                summary["failures"] += 1
                summary["variants"].append(
                    {"label": label, "pass": pass_index + 1, "error": str(exc)[:200]}
                )

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-warm /api/mvp/race")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL,
                        help=f"API base URL (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--season", default=None,
                        help="Season string e.g. 2025-26 (default: auto-detect)")
    parser.add_argument("--passes", type=int, default=WARM_PASSES,
                        help=f"Requests per variant (default: {WARM_PASSES})")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("warm_mvp_cache")

    season = args.season or _resolve_default_season()
    log.info("warming MVP race cache for season=%s via %s", season, args.base_url)

    summary = warm_endpoint(args.base_url, season, passes=args.passes, log=log)
    log.info("done: %d/%d successes, %d failures",
             summary["successes"], summary["requests"], summary["failures"])

    # Write a freshness marker so /api/health/sync-status surfaces this
    # in the Sprint 98 syncs map. Non-fatal.
    try:
        from services.sync_freshness import record_sync

        record_sync(
            "mvp_race_warm",
            count=summary["successes"],
            source="warm_mvp_cache.py",
            error=None if summary["failures"] == 0 else f"{summary['failures']} request(s) failed",
        )
    except Exception:
        pass

    return 0 if summary["failures"] == 0 else 1


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    raise SystemExit(main())
