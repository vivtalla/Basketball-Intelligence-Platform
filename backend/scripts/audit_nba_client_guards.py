#!/usr/bin/env python3
"""Sprint 98 Stream C1 — Audit nba_client.py for unguarded user-fetch endpoints.

The ``_block_live_fetch_if_user_mode`` guard prevents user-request paths
from hitting ``stats.nba.com`` in production (cron explicitly sets
NBA_API_USER_FETCH_DISABLED=false so it's allowed for the daily sync).
Without the guard, a cold cache + a user request = a 3-30s live fetch
that can OOM a gunicorn worker.

This script walks ``backend/data/nba_client.py`` and reports every wrapper
function that performs a network IO (calls ``_fetch_*``, ``urlopen``, or
``_rate_limit``) but does NOT call ``_block_live_fetch_if_user_mode``
first. Run before-and-after the Sprint 98 C1 changes to confirm zero
unguarded endpoints remain.

Usage:
    python backend/scripts/audit_nba_client_guards.py
    # prints summary + per-function details to stdout
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import List


GUARD_CALL = "_block_live_fetch_if_user_mode"
NETWORK_CALL_PATTERNS = (
    "_fetch_live_json",
    "_fetch_static_json",
    "_fetch_nba_json",
    "_fetch_official_injury_report_payload",
    "urlopen",
    "_rate_limit",
    "requests.get",
)


# Private helper functions that don't need direct guards — they're
# called only by guarded wrappers and inherit the protection.
PRIVATE_HELPER_NAMES = {
    "_fetch", "_fetch_text", "_fetch_bytes",
    "_fetch_nba_json", "_fetch_live_json", "_fetch_static_json",
    "_current_schedule_game_ids", "_current_team_schedule_game_ids",
    "_historical_schedule_game_ids",
}

# Public endpoints that hit the public CDN (live-data + static-data
# feeds) rather than stats.nba.com. These are fast (<1s typically),
# rate-limit-free, and intentionally callable from user request paths.
# Documented as designed-unguarded since Sprint 82.
CDN_ONLY_PUBLIC = {
    "get_game_box_score", "get_game_box_score_payload",
    "get_play_by_play", "get_play_by_play_payload",
    "get_todays_scoreboard", "get_schedule_payload_for_season",
    "get_injuries_payload",
    # Experimental scrape; falls back to empty on failure.
    "get_inside_game_gravity_rows",
}


def _function_calls(node: ast.FunctionDef) -> List[str]:
    """Return every call name referenced in the function body."""
    names: List[str] = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            target = sub.func
            if isinstance(target, ast.Name):
                names.append(target.id)
            elif isinstance(target, ast.Attribute):
                # requests.get → "requests.get"
                if isinstance(target.value, ast.Name):
                    names.append(f"{target.value.id}.{target.attr}")
                else:
                    names.append(target.attr)
    return names


def audit(nba_client_path: Path) -> int:
    """Print the audit report. Returns the count of unguarded functions."""
    source = nba_client_path.read_text()
    tree = ast.parse(source)

    unguarded_concerns: List[str] = []
    private_helpers: List[str] = []
    cdn_only: List[str] = []
    guarded: List[str] = []
    no_network: List[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        calls = _function_calls(node)
        has_network = any(any(p in c for p in NETWORK_CALL_PATTERNS) for c in calls)
        if not has_network:
            no_network.append(node.name)
            continue
        if GUARD_CALL in calls:
            guarded.append(node.name)
        elif node.name in PRIVATE_HELPER_NAMES:
            private_helpers.append(node.name)
        elif node.name in CDN_ONLY_PUBLIC:
            cdn_only.append(node.name)
        else:
            unguarded_concerns.append(node.name)

    total_network = len(guarded) + len(unguarded_concerns) + len(private_helpers) + len(cdn_only)
    print(f"audit results for {nba_client_path}")
    print(f"  total network-calling functions: {total_network}")
    print(f"  guarded:               {len(guarded)}")
    print(f"  unguarded (concerns):  {len(unguarded_concerns)}")
    print(f"  private helpers:       {len(private_helpers)} (transitively protected)")
    print(f"  CDN-only public:       {len(cdn_only)} (designed-unguarded; fast public JSON)")
    print(f"  no-network helpers:    {len(no_network)}")
    print()

    if unguarded_concerns:
        print("UNGUARDED CONCERNS (need _block_live_fetch_if_user_mode):")
        for name in sorted(unguarded_concerns):
            print(f"  - {name}")
        print()
    else:
        print("All stats.nba.com wrappers are guarded. ✓")
        print()

    if private_helpers:
        print("Private helpers (inherited protection):")
        for name in sorted(private_helpers):
            print(f"  - {name}")
        print()

    if cdn_only:
        print("CDN-only public endpoints (designed-unguarded):")
        for name in sorted(cdn_only):
            print(f"  - {name}")
        print()

    if guarded:
        print(f"Guarded ({len(guarded)} functions, reference only).")

    return len(unguarded_concerns)


def main() -> int:
    backend_dir = Path(__file__).resolve().parents[1]
    target = backend_dir / "data" / "nba_client.py"
    if not target.exists():
        print(f"could not find {target}", file=sys.stderr)
        return 2
    return audit(target)


if __name__ == "__main__":
    raise SystemExit(0 if main() == 0 else 1)
