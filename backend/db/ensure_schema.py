"""Compatibility wrapper for the new Alembic-backed migration workflow.

This module remains importable for older local scripts, but the canonical
schema path is now `python -m db.migrations`.
"""

from __future__ import annotations

from db.migrations import upgrade_database


def apply_schema_updates() -> None:
    upgrade_database()


if __name__ == "__main__":
    upgrade_database()
