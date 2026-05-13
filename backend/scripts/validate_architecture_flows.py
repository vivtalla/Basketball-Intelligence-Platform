#!/usr/bin/env python3
"""Sprint 98 follow-on — validate ``specs/architecture-flows.html``.

The architecture-flows doc is only useful if it stays in sync with the
codebase. This script gives the "keep it current" rule teeth: it
asserts the embedded JSON catalog is well-formed and warns when it
looks out-of-date relative to the code (routers / services on disk
that no flow mentions).

Checks (failing):
  1. JSON inside the ``<script type="application/json" id="catalog">``
     block parses.
  2. Every node has the required fields (id, label, layer, x, y, w, h).
  3. Every layer entry has label / x / y.
  4. Every flow has id / category / label / summary / steps.
  5. Every step's ``from`` + ``to`` reference a known node id.
  6. Flow category is one of the four known values.

Checks (warning, non-failing):
  - Router files in backend/routers/ that no flow's step mentions in
    its action / note text. Surfaces routers added without doc updates.
  - Service files in backend/services/ that no flow mentions. Same idea.

Exit code: 0 on pass / warnings only, 1 on validation errors.

Run manually:
    python backend/scripts/validate_architecture_flows.py

CI:
    Wired into .github/workflows/ci.yml as a soft check.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


REQUIRED_NODE_FIELDS = {"id", "label", "layer", "x", "y", "w", "h"}
REQUIRED_LAYER_FIELDS = {"label", "x", "y"}
REQUIRED_FLOW_FIELDS = {"id", "category", "label", "summary", "steps"}
REQUIRED_STEP_FIELDS = {"from", "to"}
KNOWN_CATEGORIES = {"page-loads", "user-actions", "background-sync", "ops-monitoring"}


def _extract_json(html_path: Path) -> dict:
    html = html_path.read_text()
    m = re.search(
        r'<script type="application/json" id="catalog">(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not m:
        raise SystemExit("could not find catalog JSON block in HTML")
    return json.loads(m.group(1))


def _validate_structure(catalog: dict) -> List[str]:
    errors: List[str] = []

    for required_key in ("nodes", "layers", "flows"):
        if required_key not in catalog:
            errors.append(f"catalog missing top-level key: {required_key}")
            return errors

    nodes = catalog["nodes"]
    layers = catalog["layers"]
    flows = catalog["flows"]

    # Nodes
    for i, node in enumerate(nodes):
        missing = REQUIRED_NODE_FIELDS - set(node)
        if missing:
            errors.append(f"node #{i} ({node.get('id', '?')}) missing fields: {sorted(missing)}")
    seen_ids: Set[str] = set()
    for node in nodes:
        nid = node.get("id")
        if nid in seen_ids:
            errors.append(f"duplicate node id: {nid}")
        seen_ids.add(nid)

    # Layers
    for i, layer in enumerate(layers):
        missing = REQUIRED_LAYER_FIELDS - set(layer)
        if missing:
            errors.append(f"layer #{i} ({layer.get('label', '?')}) missing fields: {sorted(missing)}")

    # Flows
    seen_flow_ids: Set[str] = set()
    for flow in flows:
        fid = flow.get("id", "?")
        missing = REQUIRED_FLOW_FIELDS - set(flow)
        if missing:
            errors.append(f"flow {fid} missing fields: {sorted(missing)}")
            continue
        if fid in seen_flow_ids:
            errors.append(f"duplicate flow id: {fid}")
        seen_flow_ids.add(fid)
        if flow["category"] not in KNOWN_CATEGORIES:
            errors.append(
                f"flow {fid} has unknown category '{flow['category']}'; "
                f"expected one of {sorted(KNOWN_CATEGORIES)}"
            )
        for j, step in enumerate(flow["steps"]):
            missing_step = REQUIRED_STEP_FIELDS - set(step)
            if missing_step:
                errors.append(f"flow {fid} step #{j+1} missing fields: {sorted(missing_step)}")
                continue
            for end in ("from", "to"):
                if step[end] not in seen_ids:
                    errors.append(
                        f"flow {fid} step #{j+1} references unknown node id "
                        f"in `{end}`: {step[end]!r}"
                    )

    return errors


def _coverage_warnings(catalog: dict, repo_root: Path) -> List[str]:
    """Soft warnings — surface routers/services on disk that no flow mentions."""
    warnings: List[str] = []

    # Gather all action + note text per flow so we can grep-match file names.
    text_blob_lower = " ".join(
        (str(step.get("action", "")) + " " + str(step.get("note", "")))
        for flow in catalog["flows"]
        for step in flow["steps"]
    ).lower()
    flow_labels = " ".join(f.get("label", "") + " " + f.get("summary", "") for f in catalog["flows"]).lower()
    text_blob_lower += " " + flow_labels

    def _file_mentioned(stem: str) -> bool:
        # Match the bare stem or common variants ("/api/<stem>", "<stem>.py")
        return stem in text_blob_lower

    routers_dir = repo_root / "backend" / "routers"
    if routers_dir.is_dir():
        unmentioned_routers = [
            f.stem for f in sorted(routers_dir.glob("*.py"))
            if f.stem != "__init__" and not _file_mentioned(f.stem)
        ]
        if unmentioned_routers:
            warnings.append(
                f"WARN: {len(unmentioned_routers)} router file(s) not referenced in any flow: "
                f"{', '.join(unmentioned_routers[:10])}"
                + ("..." if len(unmentioned_routers) > 10 else "")
            )

    services_dir = repo_root / "backend" / "services"
    if services_dir.is_dir():
        # Stems with `_service` suffix tend to be the orchestration entry points;
        # surface unmentioned ones since they represent flow shapes.
        unmentioned_services = [
            f.stem for f in sorted(services_dir.glob("*_service.py"))
            if not _file_mentioned(f.stem.replace("_service", ""))
            and not _file_mentioned(f.stem)
        ]
        if unmentioned_services:
            warnings.append(
                f"WARN: {len(unmentioned_services)} service file(s) not referenced in any flow: "
                f"{', '.join(unmentioned_services[:10])}"
                + ("..." if len(unmentioned_services) > 10 else "")
            )

    return warnings


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    html_path = repo_root / "specs" / "architecture-flows.html"
    if not html_path.exists():
        print(f"ERROR: {html_path} not found", file=sys.stderr)
        return 1

    try:
        catalog = _extract_json(html_path)
    except json.JSONDecodeError as exc:
        print(f"ERROR: catalog JSON does not parse: {exc}", file=sys.stderr)
        return 1

    errors = _validate_structure(catalog)
    warnings = _coverage_warnings(catalog, repo_root)

    nodes = catalog.get("nodes", [])
    flows = catalog.get("flows", [])
    total_steps = sum(len(f.get("steps", [])) for f in flows)

    print(f"architecture-flows.html: {len(nodes)} nodes, {len(flows)} flows, {total_steps} steps")

    if warnings:
        print()
        for w in warnings:
            print(w, file=sys.stderr)

    if errors:
        print()
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print("structure: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
