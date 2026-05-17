"""Sprint 100 (Stream A) — draft analyzer data foundation.

Adds four tables + several columns that together extend the draft prospect
schema into a real ML-validatable analyzer:

  * ``draft_mock_rankings`` — one row per (prospect, source, as_of). Backs
    consensus-rank computation and per-source variance signals.
  * ``draft_outcomes`` — historical (2016-2025) career outcomes that anchor
    the comp service's "did this comp pan out?" weighting and the tier
    classifier's empirical priors.
  * ``draft_prospect_linkage`` — fuzzy-match override layer for resolving
    a ``DraftProspect`` to the canonical ``players.id``. Auto-match writes
    rows; admins can manually correct edge cases.
  * ``draft_international_stats`` — Euroleague / EuroCup / Adriatic / LNB /
    G-League per-season stats so non-NCAA prospects render with real data.

Plus additive columns:
  * ``draft_prospects.draft_pick_number``, ``draft_pick_team_id`` — set
    after the draft occurs; null for active 2026 class.
  * ``draft_prospects.is_historical`` — excludes 2016-2025 backfill rows
    from the live board (they're for training, not display).
  * ``draft_prospects.consensus_rank_float`` + ``consensus_variance`` —
    denormalized cache of mock-board aggregates for cheap board sort.
    Kept alongside the existing integer ``consensus_rank`` (which is the
    legacy single-source rank) to stay backwards-compatible.
  * ``draft_prospect_measurements.combine_year`` + ``source_url`` +
    ``as_of`` — proper attribution metadata.

Idempotent — follows the Sprint 88+ ``_has_table`` / ``_has_column``
pattern so re-running on a partially-applied DB is safe. Both SQLite
(tests) and Postgres (prod) must pass; ``sa.JSON`` is used in place of
``sa.JSONB`` for portability.
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa


revision = "0028_sprint100_draft_fd"
down_revision = "0027_sprint98_view"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in inspect(op.get_bind()).get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return column_name in {col["name"] for col in inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    # ── New tables ────────────────────────────────────────────────────
    if not _has_table("draft_mock_rankings"):
        op.create_table(
            "draft_mock_rankings",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("prospect_id", sa.Integer(), sa.ForeignKey("draft_prospects.id"), nullable=False),
            sa.Column("source", sa.String(32), nullable=False),
            sa.Column("source_url", sa.Text(), nullable=True),
            sa.Column("as_of", sa.DateTime(), nullable=False),
            sa.Column("rank", sa.Integer(), nullable=False),
            sa.Column("tier", sa.String(16), nullable=True),
            sa.Column("position_projected", sa.String(8), nullable=True),
            sa.Column("comp_player_name", sa.String(120), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
            sa.UniqueConstraint("prospect_id", "source", "as_of", name="uq_mock_prospect_source_asof"),
        )
        op.create_index("ix_mock_source_asof", "draft_mock_rankings", ["source", "as_of"])

    if not _has_table("draft_outcomes"):
        op.create_table(
            "draft_outcomes",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("prospect_id", sa.Integer(), sa.ForeignKey("draft_prospects.id"), nullable=True),
            sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=True),
            sa.Column("draft_year", sa.Integer(), nullable=False),
            sa.Column("draft_pick", sa.Integer(), nullable=True),
            sa.Column("draft_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
            sa.Column("career_games", sa.Integer(), nullable=True),
            sa.Column("career_minutes", sa.Float(), nullable=True),
            sa.Column("career_ppg", sa.Float(), nullable=True),
            sa.Column("career_ws", sa.Float(), nullable=True),
            sa.Column("career_vorp", sa.Float(), nullable=True),
            sa.Column("peak_per", sa.Float(), nullable=True),
            sa.Column("all_star_selections", sa.Integer(), server_default="0"),
            sa.Column("all_nba_selections", sa.Integer(), server_default="0"),
            sa.Column("outcome_tier", sa.String(16), nullable=True),
            sa.Column("as_of_season", sa.Integer(), nullable=True),
            sa.Column("external_metrics_meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index("ix_outcomes_draft_year", "draft_outcomes", ["draft_year"])
        op.create_index("ix_outcomes_player", "draft_outcomes", ["player_id"])
        op.create_index("ix_outcomes_tier", "draft_outcomes", ["outcome_tier"])

    if not _has_table("draft_prospect_linkage"):
        op.create_table(
            "draft_prospect_linkage",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("prospect_id", sa.Integer(), sa.ForeignKey("draft_prospects.id"), nullable=False),
            sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
            sa.Column("match_method", sa.String(16), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("verified_by", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.UniqueConstraint("prospect_id", "player_id", name="uq_linkage_prospect_player"),
        )
        op.create_index("ix_linkage_prospect", "draft_prospect_linkage", ["prospect_id"])
        op.create_index("ix_linkage_player", "draft_prospect_linkage", ["player_id"])

    if not _has_table("draft_international_stats"):
        op.create_table(
            "draft_international_stats",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("prospect_id", sa.Integer(), sa.ForeignKey("draft_prospects.id"), nullable=False),
            sa.Column("season", sa.String(16), nullable=False),
            sa.Column("league", sa.String(32), nullable=False),
            sa.Column("team_name", sa.String(120), nullable=True),
            sa.Column("games", sa.Integer(), nullable=True),
            sa.Column("minutes_per_game", sa.Float(), nullable=True),
            sa.Column("ppg", sa.Float(), nullable=True),
            sa.Column("rpg", sa.Float(), nullable=True),
            sa.Column("apg", sa.Float(), nullable=True),
            sa.Column("spg", sa.Float(), nullable=True),
            sa.Column("bpg", sa.Float(), nullable=True),
            sa.Column("fg_pct", sa.Float(), nullable=True),
            sa.Column("three_pct", sa.Float(), nullable=True),
            sa.Column("ft_pct", sa.Float(), nullable=True),
            sa.Column("usage_rate", sa.Float(), nullable=True),
            sa.Column("ts_pct", sa.Float(), nullable=True),
            sa.Column("source", sa.String(32), nullable=False, server_default="realgm"),
            sa.Column("source_url", sa.Text(), nullable=True),
            sa.Column("as_of", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.UniqueConstraint("prospect_id", "season", "league", name="uq_intl_prospect_season_league"),
        )
        op.create_index("ix_intl_prospect", "draft_international_stats", ["prospect_id"])

    # ── Additive columns on draft_prospects ───────────────────────────
    if not _has_column("draft_prospects", "draft_pick_number"):
        op.add_column("draft_prospects", sa.Column("draft_pick_number", sa.Integer(), nullable=True))
    if not _has_column("draft_prospects", "draft_pick_team_id"):
        # SQLite cannot ALTER a table to add a column with an inline FK
        # (alembic raises NotImplementedError). The ORM model still
        # declares the relationship via ForeignKey for documentation;
        # Postgres enforcement of this constraint is intentionally
        # deferred — the column is for after-the-fact draft results
        # and uniqueness is enforced upstream.
        op.add_column(
            "draft_prospects",
            sa.Column("draft_pick_team_id", sa.Integer(), nullable=True),
        )
    if not _has_column("draft_prospects", "is_historical"):
        op.add_column(
            "draft_prospects",
            sa.Column("is_historical", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        op.create_index("ix_draft_prospects_historical", "draft_prospects", ["is_historical"])
    if not _has_column("draft_prospects", "consensus_rank_float"):
        op.add_column("draft_prospects", sa.Column("consensus_rank_float", sa.Float(), nullable=True))
    if not _has_column("draft_prospects", "consensus_variance"):
        op.add_column("draft_prospects", sa.Column("consensus_variance", sa.Float(), nullable=True))

    # ── Additive columns on draft_prospect_measurements ───────────────
    if not _has_column("draft_prospect_measurements", "combine_year"):
        op.add_column(
            "draft_prospect_measurements",
            sa.Column("combine_year", sa.Integer(), nullable=True),
        )
    if not _has_column("draft_prospect_measurements", "source_url"):
        op.add_column(
            "draft_prospect_measurements",
            sa.Column("source_url", sa.Text(), nullable=True),
        )
    if not _has_column("draft_prospect_measurements", "as_of"):
        op.add_column(
            "draft_prospect_measurements",
            sa.Column("as_of", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    # Drop additive columns first (FK-free), then tables in reverse-FK order.
    if _has_column("draft_prospect_measurements", "as_of"):
        op.drop_column("draft_prospect_measurements", "as_of")
    if _has_column("draft_prospect_measurements", "source_url"):
        op.drop_column("draft_prospect_measurements", "source_url")
    if _has_column("draft_prospect_measurements", "combine_year"):
        op.drop_column("draft_prospect_measurements", "combine_year")

    if _has_column("draft_prospects", "consensus_variance"):
        op.drop_column("draft_prospects", "consensus_variance")
    if _has_column("draft_prospects", "consensus_rank_float"):
        op.drop_column("draft_prospects", "consensus_rank_float")
    if _has_column("draft_prospects", "is_historical"):
        op.drop_index("ix_draft_prospects_historical", table_name="draft_prospects")
        op.drop_column("draft_prospects", "is_historical")
    if _has_column("draft_prospects", "draft_pick_team_id"):
        op.drop_column("draft_prospects", "draft_pick_team_id")
    if _has_column("draft_prospects", "draft_pick_number"):
        op.drop_column("draft_prospects", "draft_pick_number")

    if _has_table("draft_international_stats"):
        op.drop_index("ix_intl_prospect", table_name="draft_international_stats")
        op.drop_table("draft_international_stats")
    if _has_table("draft_prospect_linkage"):
        op.drop_index("ix_linkage_player", table_name="draft_prospect_linkage")
        op.drop_index("ix_linkage_prospect", table_name="draft_prospect_linkage")
        op.drop_table("draft_prospect_linkage")
    if _has_table("draft_outcomes"):
        op.drop_index("ix_outcomes_tier", table_name="draft_outcomes")
        op.drop_index("ix_outcomes_player", table_name="draft_outcomes")
        op.drop_index("ix_outcomes_draft_year", table_name="draft_outcomes")
        op.drop_table("draft_outcomes")
    if _has_table("draft_mock_rankings"):
        op.drop_index("ix_mock_source_asof", table_name="draft_mock_rankings")
        op.drop_table("draft_mock_rankings")
