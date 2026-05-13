#!/usr/bin/env python3
"""Sprint 98 Stream A6 — Analyze captured cron-env snapshots.

The Sprint 97 closeout left the cron env-propagation root cause unsolved:
self-source masks the symptom, but we don't know *why* the original
``set -a && . /etc/bip/env && set +a`` wrapper failed to export DATABASE_URL
under cron. ``daily_sync.sh`` now captures ``env`` to ``/var/log/bip-cron-env/``
at script entry; this script reads those snapshots and reports:

  - How many runs were captured.
  - Which runs would have *triggered* the self-source fallback (i.e. ran
    without DATABASE_URL set at script entry).
  - The diff between the "needed self-source" runs and the "had DATABASE_URL"
    runs — what env vars differ.
  - A summary of which env vars are stable across all runs vs. variable.

Run manually after one week of data:
    python backend/scripts/analyze_cron_env.py /var/log/bip-cron-env

When the root cause is identified, disable capture by:
    sudo touch /etc/bip/no-env-capture
and remove the captured snapshots:
    sudo rm -rf /var/log/bip-cron-env
"""
from __future__ import annotations

import argparse
import collections
import os
from pathlib import Path
from typing import Dict, List, Tuple


def _read_env_file(path: Path) -> Dict[str, str]:
    """Parse a captured `env` output into a {KEY: value} dict.

    Lines without `=` are skipped (e.g. multi-line continuations from
    BASH_FUNC_*). Values may contain `=`; we split on the first one only.
    """
    out: Dict[str, str] = {}
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return out
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key or key.startswith("BASH_FUNC_") or not key.replace("_", "").isalnum():
            continue
        out[key] = value
    return out


def _classify_runs(snapshots: List[Tuple[Path, Dict[str, str]]]) -> Dict[str, List[Path]]:
    """Bucket runs by whether DATABASE_URL was already set at script entry.

    Returns a dict with keys:
      - "had_db_url": runs where DATABASE_URL was present (cron env propagation worked)
      - "needed_fallback": runs where DATABASE_URL was missing (self-source fired)
    """
    buckets: Dict[str, List[Path]] = {"had_db_url": [], "needed_fallback": []}
    for path, env in snapshots:
        if env.get("DATABASE_URL"):
            buckets["had_db_url"].append(path)
        else:
            buckets["needed_fallback"].append(path)
    return buckets


def _diff_env_groups(
    group_a: List[Dict[str, str]],
    group_b: List[Dict[str, str]],
) -> Tuple[List[str], List[str], List[str]]:
    """Compare two groups of env dicts.

    Returns (a_only_keys, b_only_keys, value_differs_keys). Stable across
    a group means: the key appears in *every* dict in that group with
    the same value.
    """
    if not group_a or not group_b:
        return [], [], []

    def _stable_keys(group: List[Dict[str, str]]) -> Dict[str, str]:
        """Keys present in every dict with the same value."""
        if not group:
            return {}
        candidate = dict(group[0])
        for env in group[1:]:
            for k in list(candidate):
                if env.get(k) != candidate[k]:
                    del candidate[k]
        return candidate

    stable_a = _stable_keys(group_a)
    stable_b = _stable_keys(group_b)
    a_only = sorted(set(stable_a) - set(stable_b))
    b_only = sorted(set(stable_b) - set(stable_a))
    differs = sorted(
        k for k in (set(stable_a) & set(stable_b)) if stable_a[k] != stable_b[k]
    )
    return a_only, b_only, differs


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze captured cron-env snapshots")
    parser.add_argument(
        "capture_dir",
        nargs="?",
        default="/var/log/bip-cron-env",
        help="Directory of captured env files (default: /var/log/bip-cron-env)",
    )
    args = parser.parse_args()

    capture_dir = Path(args.capture_dir)
    if not capture_dir.exists():
        print(f"No capture directory at {capture_dir}")
        return 1

    files = sorted(capture_dir.glob("run-*.env"))
    if not files:
        print(f"No capture files in {capture_dir}")
        return 1

    snapshots: List[Tuple[Path, Dict[str, str]]] = [(p, _read_env_file(p)) for p in files]
    buckets = _classify_runs(snapshots)

    print(f"Total captured runs: {len(snapshots)}")
    print(f"  Had DATABASE_URL at entry: {len(buckets['had_db_url'])}")
    print(f"  Needed self-source fallback: {len(buckets['needed_fallback'])}")
    print()

    if not buckets["needed_fallback"]:
        print("No runs needed the fallback — cron env propagation is consistently working.")
        return 0

    if not buckets["had_db_url"]:
        print("Every run needed the fallback — investigate the cron wrapper.")
        # Show a sample of what's in the env for these runs.
        sample = snapshots[0][1]
        print(f"Sample of env keys from {snapshots[0][0].name}:")
        for k in sorted(sample)[:30]:
            print(f"  {k}={sample[k][:40]}")
        return 0

    had_envs = [env for path, env in snapshots if path in buckets["had_db_url"]]
    fallback_envs = [env for path, env in snapshots if path in buckets["needed_fallback"]]

    a_only, b_only, differs = _diff_env_groups(had_envs, fallback_envs)

    print(f"Diff (stable keys per group):")
    print(f"  In had_db_url runs but not in fallback runs: {len(a_only)}")
    for k in a_only[:30]:
        print(f"    {k}")
    print(f"  In fallback runs but not in had_db_url: {len(b_only)}")
    for k in b_only[:30]:
        print(f"    {k}")
    print(f"  Different values across groups: {len(differs)}")
    for k in differs[:30]:
        a_val = had_envs[0].get(k, "<missing>")[:30]
        b_val = fallback_envs[0].get(k, "<missing>")[:30]
        print(f"    {k}: had={a_val!r} fallback={b_val!r}")
    print()
    print("Look at the 'In had_db_url but not in fallback' list — those are the")
    print("env vars that signal a successful cron-env propagation. The cron")
    print("wrapper or shell-init that sets them is the answer to the root cause.")

    # Also tally cron-specific keys most likely to differ.
    cron_keys = ("PATH", "SHELL", "HOME", "USER", "LOGNAME", "BASH_VERSION", "PWD")
    print("\nCron-typical key value distribution:")
    for k in cron_keys:
        had_vals = collections.Counter(env.get(k, "") for env in had_envs)
        fall_vals = collections.Counter(env.get(k, "") for env in fallback_envs)
        print(f"  {k}: had={dict(had_vals)} fallback={dict(fall_vals)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
