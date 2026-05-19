"""Golden-facts canary runner.

Loads qa/golden_facts.yaml, curls every fact's endpoint against the
production API, runs the jq_filter, asserts the operator. Prints a clean
result table and exits non-zero on any failure.

Designed to run unattended in a GitHub Action. Requires only `pyyaml`
beyond stdlib (jq is shelled out — installed by the workflow).

Run locally:
    pip install pyyaml
    python qa/check_golden_facts.py

Run against a different base URL:
    BASE_URL=http://localhost:8000 python qa/check_golden_facts.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

BASE_URL = os.environ.get("BASE_URL", "https://api.courtvue.app")
FACTS_PATH = Path(__file__).parent / "golden_facts.yaml"
HTTP_TIMEOUT_SECONDS = 20


def fetch(path: str) -> Any:
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "courtvue-golden-facts"})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_jq(payload: Any, filter_expr: str) -> Any:
    """Shell out to jq because rewriting a jq parser in Python is silly.

    Falls back to a parse error → returns the literal string output so the
    operator can decide what to do.
    """
    proc = subprocess.run(
        ["jq", "-c", filter_expr],
        input=json.dumps(payload).encode("utf-8"),
        capture_output=True,
        timeout=10,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"jq failed: {proc.stderr.decode('utf-8').strip()}")
    raw = proc.stdout.decode("utf-8").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def check_assertion(actual: Any, operator: str, expected: Any) -> Tuple[bool, str]:
    """Returns (passed, explanation)."""
    if operator == "equals":
        ok = actual == expected
        return ok, f"got {actual!r}, expected {expected!r}"

    if operator == "in_range":
        lo, hi = expected
        try:
            n = float(actual)
        except (TypeError, ValueError):
            return False, f"got non-numeric {actual!r}, expected number in [{lo}, {hi}]"
        ok = lo <= n <= hi
        return ok, f"got {n}, expected in [{lo}, {hi}]"

    if operator == "min_length":
        try:
            length = len(actual)
        except TypeError:
            return False, f"got non-iterable {actual!r}"
        ok = length >= expected
        return ok, f"got length {length}, expected >= {expected}"

    if operator == "contains_all":
        if not isinstance(actual, list):
            return False, f"got non-list {actual!r}"
        missing = [v for v in expected if v not in actual]
        return (not missing), f"missing {missing}" if missing else "all present"

    if operator == "contains_none":
        if not isinstance(actual, list):
            return False, f"got non-list {actual!r}"
        found = [v for v in expected if v in actual]
        return (not found), f"forbidden values present: {found}" if found else "none present (good)"

    if operator == "ascending":
        if not isinstance(actual, list):
            return False, f"got non-list {actual!r}"
        ok = all(actual[i] <= actual[i + 1] for i in range(len(actual) - 1))
        return ok, f"order: {actual}"

    if operator == "descending":
        if not isinstance(actual, list):
            return False, f"got non-list {actual!r}"
        ok = all(actual[i] >= actual[i + 1] for i in range(len(actual) - 1))
        return ok, f"order: {actual}"

    return False, f"unknown operator: {operator}"


def check_fact(fact: Dict[str, Any]) -> Dict[str, Any]:
    """Returns a result dict with keys: id, status, detail, stale."""
    result: Dict[str, Any] = {
        "id": fact["id"],
        "description": fact.get("description", ""),
        "status": "pass",
        "detail": "",
        "stale": False,
    }

    review_by = fact.get("review_by")
    if review_by:
        review_date = review_by if isinstance(review_by, date) else datetime.strptime(str(review_by), "%Y-%m-%d").date()
        if review_date < date.today():
            result["stale"] = True

    try:
        payload = fetch(fact["endpoint"])
    except urllib.error.HTTPError as e:
        result["status"] = "fail"
        result["detail"] = f"HTTP {e.code} on {fact['endpoint']}"
        return result
    except Exception as e:  # noqa: BLE001
        result["status"] = "fail"
        result["detail"] = f"fetch failed: {type(e).__name__}: {e}"
        return result

    try:
        actual = run_jq(payload, fact["jq_filter"])
    except Exception as e:  # noqa: BLE001
        result["status"] = "fail"
        result["detail"] = f"jq failed: {e}"
        return result

    passed, explanation = check_assertion(actual, fact["operator"], fact.get("value"))
    result["status"] = "pass" if passed else "fail"
    result["detail"] = explanation
    return result


def main() -> int:
    with FACTS_PATH.open() as fh:
        config = yaml.safe_load(fh)
    facts: List[Dict[str, Any]] = config["facts"]

    print(f"Golden-facts canary — {len(facts)} facts against {BASE_URL}")
    print("=" * 78)

    results = [check_fact(f) for f in facts]

    width = max(len(r["id"]) for r in results) + 2
    failed = []
    stale = []
    for r in results:
        marker = "✅" if r["status"] == "pass" else "❌"
        line = f"{marker} {r['id']:<{width}} {r['detail']}"
        if r["stale"]:
            line += "  ⚠ review_by past"
            stale.append(r["id"])
        print(line)
        if r["status"] != "pass":
            failed.append(r)

    print("=" * 78)
    print(f"passed: {len(results) - len(failed)} / {len(results)}")
    if stale:
        print(f"stale review_by ({len(stale)}): {', '.join(stale)}")

    if failed:
        # Surface a machine-readable summary for the GH Action issue-creator.
        with open("golden_facts_failures.json", "w") as fh:
            json.dump({"failures": failed, "stale": stale, "base_url": BASE_URL}, fh, indent=2)
        return 1

    if stale:
        # Stale review_by is a warning, not a failure — exit 0 but flag.
        with open("golden_facts_failures.json", "w") as fh:
            json.dump({"failures": [], "stale": stale, "base_url": BASE_URL}, fh, indent=2)

    return 0


if __name__ == "__main__":
    sys.exit(main())
