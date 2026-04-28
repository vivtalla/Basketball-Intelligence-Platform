"""Sprint 73 — playoffs data layer.

Adds the ``playoff_series`` bracket table, an ``is_playoff`` flag on
``lineup_stats`` (with a unique constraint that includes it), and
``season_type`` / ``series_id`` / ``series_game_num`` / ``playoff_seed``
columns on ``game_logs`` and the warehouse ``games`` table so postseason
games can be joined back to their bracket series.

The migration is idempotent so it can run cleanly against legacy schemas
(where ``Base.metadata.create_all`` has not been re-run) and against fresh
SQLite test databases (where ``0001_base_schema`` applies the current ORM
in one shot, so most of these objects already exist).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0012_playoffs_data_layer"
down_revision = "0011_player_analysis_contexts"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_table(table_name):
    inspector = inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _has_column(table_name, column_name):
    inspector = inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_index(table_name, index_name):
    inspector = inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def _has_unique_constraint(table_name, constraint_name):
    inspector = inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    if any(c["name"] == constraint_name for c in inspector.get_unique_constraints(table_name)):
        return True
    # Some dialects expose unique constraints as unique indexes.
    return any(
        idx.get("name") == constraint_name and idx.get("unique")
        for idx in inspector.get_indexes(table_name)
    )


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    # 1. playoff_series table -------------------------------------------------
    if not _has_table("playoff_series"):
        op.create_table(
            "playoff_series",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("season", sa.String(), nullable=False),
            sa.Column("round", sa.Integer(), nullable=False),
            sa.Column("series_id", sa.String(), nullable=False),
            sa.Column("top_seed_team_id", sa.Integer(), nullable=False),
            sa.Column("bottom_seed_team_id", sa.Integer(), nullable=False),
            sa.Column("top_seed", sa.Integer(), nullable=False),
            sa.Column("bottom_seed", sa.Integer(), nullable=False),
            sa.Column("top_wins", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("bottom_wins", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("winner_team_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.ForeignKeyConstraint(["top_seed_team_id"], ["teams.id"]),
            sa.ForeignKeyConstraint(["bottom_seed_team_id"], ["teams.id"]),
            sa.ForeignKeyConstraint(["winner_team_id"], ["teams.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("season", "series_id", name="uq_playoff_series_season_series"),
        )

    if _has_table("playoff_series"):
        if not _has_index("playoff_series", "ix_playoff_series_season"):
            op.create_index("ix_playoff_series_season", "playoff_series", ["season"])
        if not _has_index("playoff_series", "ix_playoff_series_round"):
            op.create_index("ix_playoff_series_round", "playoff_series", ["round"])
        if not _has_index("playoff_series", "ix_playoff_series_status"):
            op.create_index("ix_playoff_series_status", "playoff_series", ["status"])

    # 2. lineup_stats.is_playoff + updated unique constraint ------------------
    if _has_table("lineup_stats"):
        if not _has_column("lineup_stats", "is_playoff"):
            with op.batch_alter_table("lineup_stats") as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "is_playoff",
                        sa.Boolean(),
                        nullable=False,
                        server_default=sa.false(),
                    )
                )

        # Backfill explicitly so older rows have a concrete value (server_default
        # only applies to new rows on some dialects).
        op.execute("UPDATE lineup_stats SET is_playoff = FALSE WHERE is_playoff IS NULL")

        # Drop the legacy 2-col unique constraint and recreate the new 3-col one
        # so the same lineup can appear in both regular season and playoffs.
        has_old = _has_unique_constraint("lineup_stats", "uq_lineup_season")
        has_new = _has_unique_constraint("lineup_stats", "uq_lineup_season_playoff")
        if has_old or not has_new:
            if dialect_name == "sqlite":
                with op.batch_alter_table("lineup_stats", recreate="always") as batch_op:
                    if has_old:
                        batch_op.drop_constraint("uq_lineup_season", type_="unique")
                    if not has_new:
                        batch_op.create_unique_constraint(
                            "uq_lineup_season_playoff",
                            ["lineup_key", "season", "is_playoff"],
                        )
            else:
                if has_old:
                    op.drop_constraint("uq_lineup_season", "lineup_stats", type_="unique")
                if not has_new:
                    op.create_unique_constraint(
                        "uq_lineup_season_playoff",
                        "lineup_stats",
                        ["lineup_key", "season", "is_playoff"],
                    )

    # 3. game_logs playoff metadata -------------------------------------------
    if _has_table("game_logs"):
        if not _has_column("game_logs", "season_type"):
            op.add_column(
                "game_logs",
                sa.Column(
                    "season_type",
                    sa.String(),
                    nullable=False,
                    server_default="Regular Season",
                ),
            )
        if not _has_column("game_logs", "series_id"):
            op.add_column("game_logs", sa.Column("series_id", sa.String(), nullable=True))
        if not _has_column("game_logs", "series_game_num"):
            op.add_column("game_logs", sa.Column("series_game_num", sa.Integer(), nullable=True))
        if not _has_column("game_logs", "playoff_seed"):
            op.add_column("game_logs", sa.Column("playoff_seed", sa.Integer(), nullable=True))

        if _has_column("game_logs", "series_id") and not _has_index("game_logs", "ix_game_logs_series_id"):
            op.create_index("ix_game_logs_series_id", "game_logs", ["series_id"])

    # 4. warehouse games (table name "games") ---------------------------------
    if _has_table("games"):
        if not _has_column("games", "season_type"):
            op.add_column(
                "games",
                sa.Column(
                    "season_type",
                    sa.String(),
                    nullable=False,
                    server_default="Regular Season",
                ),
            )
        if not _has_column("games", "series_id"):
            op.add_column("games", sa.Column("series_id", sa.String(), nullable=True))
        if not _has_column("games", "series_game_num"):
            op.add_column("games", sa.Column("series_game_num", sa.Integer(), nullable=True))
        if not _has_column("games", "playoff_seed"):
            op.add_column("games", sa.Column("playoff_seed", sa.Integer(), nullable=True))

        if _has_column("games", "series_id") and not _has_index("games", "ix_games_series_id"):
            op.create_index("ix_games_series_id", "games", ["series_id"])


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    # warehouse games
    if _has_table("games"):
        if _has_index("games", "ix_games_series_id"):
            op.drop_index("ix_games_series_id", table_name="games")
        for col in ("playoff_seed", "series_game_num", "series_id", "season_type"):
            if _has_column("games", col):
                op.drop_column("games", col)

    # game_logs
    if _has_table("game_logs"):
        if _has_index("game_logs", "ix_game_logs_series_id"):
            op.drop_index("ix_game_logs_series_id", table_name="game_logs")
        for col in ("playoff_seed", "series_game_num", "series_id", "season_type"):
            if _has_column("game_logs", col):
                op.drop_column("game_logs", col)

    # lineup_stats — restore the legacy unique constraint
    if _has_table("lineup_stats"):
        if dialect_name == "sqlite":
            with op.batch_alter_table("lineup_stats", recreate="always") as batch_op:
                if _has_unique_constraint("lineup_stats", "uq_lineup_season_playoff"):
                    batch_op.drop_constraint("uq_lineup_season_playoff", type_="unique")
                if not _has_unique_constraint("lineup_stats", "uq_lineup_season"):
                    batch_op.create_unique_constraint(
                        "uq_lineup_season", ["lineup_key", "season"]
                    )
                if _has_column("lineup_stats", "is_playoff"):
                    batch_op.drop_column("is_playoff")
        else:
            if _has_unique_constraint("lineup_stats", "uq_lineup_season_playoff"):
                op.drop_constraint("uq_lineup_season_playoff", "lineup_stats", type_="unique")
            if not _has_unique_constraint("lineup_stats", "uq_lineup_season"):
                op.create_unique_constraint(
                    "uq_lineup_season", "lineup_stats", ["lineup_key", "season"]
                )
            if _has_column("lineup_stats", "is_playoff"):
                op.drop_column("lineup_stats", "is_playoff")

    # playoff_series
    if _has_table("playoff_series"):
        for idx in (
            "ix_playoff_series_status",
            "ix_playoff_series_round",
            "ix_playoff_series_season",
        ):
            if _has_index("playoff_series", idx):
                op.drop_index(idx, table_name="playoff_series")
        op.drop_table("playoff_series")
