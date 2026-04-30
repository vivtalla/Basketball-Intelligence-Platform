"""Sprint 81 — CI guard: no service file may import the retired ``PlayByPlay`` model.

The legacy ``play_by_play`` table was dropped in migration
``0018_sprint81_drop_legacy_pbp``. Any future PR that re-introduces a
``from db.models import PlayByPlay`` (or ``db.query(PlayByPlay)``) will hit
a runtime ``ImportError`` because the model no longer exists — this test
fails earlier in CI so the regression is caught at review time rather than
at boot.

Allowed:
- ``PlayByPlayEvent`` references
- The string ``"play_by_play_events"`` table name
"""
from __future__ import annotations

import pathlib
import re

# Look for the standalone identifier ``PlayByPlay`` (not followed by ``Event``).
_LEGACY_RE = re.compile(r"\bPlayByPlay\b(?!Event)")

# Skip lines that are clearly string literals (NBA API response keys etc.) or
# comments — only the bare identifier as Python code is a real regression.
_STRING_KEY_RE = re.compile(r"""(?:'PlayByPlay'|"PlayByPlay")""")
_COMMENT_RE = re.compile(r"^\s*#")

# Files we deliberately keep — the migration that drops the table mentions
# the legacy name, and this test obviously does too.
_ALLOWED_PATHS = {
    "backend/alembic/versions/0018_sprint81_drop_legacy_pbp.py",
    "backend/tests/test_no_legacy_pbp_imports.py",
}

# Roots to scan. We don't traverse into venv or site-packages.
_SCAN_ROOTS = ("backend/services", "backend/routers", "backend/data", "backend/db")


def _repo_root() -> pathlib.Path:
    here = pathlib.Path(__file__).resolve()
    # backend/tests/test_*.py → backend/ → repo root
    return here.parent.parent.parent


def test_no_legacy_play_by_play_imports() -> None:
    root = _repo_root()
    offenders: list[str] = []

    for sub in _SCAN_ROOTS:
        base = root / sub
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            rel = path.relative_to(root).as_posix()
            if rel in _ALLOWED_PATHS:
                continue
            try:
                contents = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for line_no, line in enumerate(contents.splitlines(), start=1):
                if not _LEGACY_RE.search(line):
                    continue
                # Skip string-literal references (NBA API JSON keys etc.)
                if _STRING_KEY_RE.search(line):
                    continue
                # Skip comment-only lines that just mention the retired name.
                if _COMMENT_RE.match(line):
                    continue
                offenders.append("{0}:{1}: {2}".format(rel, line_no, line.strip()))

    assert not offenders, (
        "Sprint 81 retired the legacy `play_by_play` table. The following "
        "lines reference the dropped `PlayByPlay` model:\n  - "
        + "\n  - ".join(offenders)
        + "\nUse `PlayByPlayEvent` instead."
    )
