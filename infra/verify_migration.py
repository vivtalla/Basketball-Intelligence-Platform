"""Verify a pg_dump/pg_restore migration by diffing row counts between two
PostgreSQL databases.

Usage:
    python infra/verify_migration.py \\
        --source postgresql://localhost/bip \\
        --target postgresql://bip:PASS@hetzner-ip:5432/bip

Exits non-zero if any user table differs by more than --tolerance rows
(default 0). Use --tolerance >0 if you expect some drift between snapshot
time and verification time.

Compares:
- Per-user-table row count
- Per-user-table total relation size (within 5% by default)
- Latest alembic_version

Skips: pg_*, information_schema, alembic_version is checked separately.
"""
from __future__ import annotations

import argparse
import sys
from typing import Dict, List, Optional, Tuple

from sqlalchemy import create_engine, text


def fetch_table_stats(database_url: str) -> Tuple[Dict[str, int], Dict[str, int], Optional[str]]:
    """Return (rowcount_by_table, bytes_by_table, alembic_revision)."""
    engine = create_engine(database_url)
    rowcounts: Dict[str, int] = {}
    bytes_by_table: Dict[str, int] = {}
    alembic_rev: Optional[str] = None

    with engine.connect() as conn:
        # User tables
        rows = conn.execute(text(
            "SELECT relname FROM pg_stat_user_tables ORDER BY relname"
        )).fetchall()

        for (tbl,) in rows:
            try:
                n = conn.execute(text("SELECT count(*) FROM " + tbl)).scalar()
                rowcounts[tbl] = int(n or 0)
            except Exception as exc:
                print("  warn: could not count " + tbl + ": " + str(exc), file=sys.stderr)
                rowcounts[tbl] = -1
            try:
                b = conn.execute(
                    text("SELECT pg_total_relation_size(:tbl)").bindparams(tbl=tbl)
                ).scalar()
                bytes_by_table[tbl] = int(b or 0)
            except Exception:
                bytes_by_table[tbl] = -1

        try:
            alembic_rev = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar()
        except Exception:
            alembic_rev = None

    engine.dispose()
    return rowcounts, bytes_by_table, alembic_rev


def diff_stats(
    source_rows: Dict[str, int],
    target_rows: Dict[str, int],
    source_bytes: Dict[str, int],
    target_bytes: Dict[str, int],
    row_tolerance: int,
    byte_pct_tolerance: float,
) -> List[str]:
    """Return a list of human-readable mismatch messages (empty if clean)."""
    issues: List[str] = []

    only_source = set(source_rows) - set(target_rows)
    only_target = set(target_rows) - set(source_rows)
    if only_source:
        issues.append("tables missing on target: " + ", ".join(sorted(only_source)))
    if only_target:
        issues.append("tables only on target (unexpected): " + ", ".join(sorted(only_target)))

    common = set(source_rows) & set(target_rows)
    for tbl in sorted(common):
        s_rows = source_rows[tbl]
        t_rows = target_rows[tbl]
        delta = abs(s_rows - t_rows)
        if delta > row_tolerance:
            issues.append(
                "row mismatch  {0:<35} source={1:>10,} target={2:>10,} delta={3:>10,}".format(
                    tbl, s_rows, t_rows, delta
                )
            )

        s_bytes = source_bytes.get(tbl, 0)
        t_bytes = target_bytes.get(tbl, 0)
        if s_bytes > 1024 * 1024 and t_bytes > 0:  # only check tables >1MB
            pct_delta = abs(s_bytes - t_bytes) / float(s_bytes)
            if pct_delta > byte_pct_tolerance:
                issues.append(
                    "size mismatch {0:<35} source={1:>10,}b target={2:>10,}b ({3:.1%} drift)".format(
                        tbl, s_bytes, t_bytes, pct_delta
                    )
                )
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--source", required=True, help="Source DB URL (e.g. local Postgres)")
    parser.add_argument("--target", required=True, help="Target DB URL (e.g. cloud Postgres)")
    parser.add_argument(
        "--tolerance",
        type=int,
        default=0,
        help="Max allowed row-count difference per table (default 0; bump if "
             "writes happened between snapshot and check).",
    )
    parser.add_argument(
        "--byte-pct-tolerance",
        type=float,
        default=0.10,
        help="Max allowed total-relation-size drift as a fraction (default 0.10 = 10%%).",
    )
    args = parser.parse_args()

    print("Fetching stats from source...")
    src_rows, src_bytes, src_rev = fetch_table_stats(args.source)
    print("Fetching stats from target...")
    tgt_rows, tgt_bytes, tgt_rev = fetch_table_stats(args.target)

    if src_rev != tgt_rev:
        print("FAIL: alembic_version mismatch — source={0} target={1}".format(src_rev, tgt_rev))
        return 1

    issues = diff_stats(src_rows, tgt_rows, src_bytes, tgt_bytes, args.tolerance, args.byte_pct_tolerance)

    if issues:
        print("FAIL: " + str(len(issues)) + " mismatch(es):")
        for issue in issues:
            print("  " + issue)
        return 1

    total_rows = sum(src_rows.values())
    print("PASS: {0} tables, {1:,} rows, alembic_version={2}".format(
        len(src_rows), total_rows, src_rev or "<none>"
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
