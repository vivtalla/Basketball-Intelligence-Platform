"""Apply legacy schema drift as audited migrations."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text


revision = "0002_legacy_schema_drift"
down_revision = "0001_base_schema"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if _has_column(table_name, column.name):
        return
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.add_column(column)


def _has_unique_constraint(table_name: str, constraint_name: str) -> bool:
    inspector = inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return any(constraint["name"] == constraint_name for constraint in inspector.get_unique_constraints(table_name))


def upgrade() -> None:
    season_stats_columns = [
        sa.Column("darko", sa.Float(), nullable=True),
        sa.Column("epm", sa.Float(), nullable=True),
        sa.Column("rapm", sa.Float(), nullable=True),
        sa.Column("lebron", sa.Float(), nullable=True),
        sa.Column("raptor", sa.Float(), nullable=True),
        sa.Column("pipm", sa.Float(), nullable=True),
        sa.Column("obpm", sa.Float(), nullable=True),
        sa.Column("dbpm", sa.Float(), nullable=True),
        sa.Column("ftr", sa.Float(), nullable=True),
        sa.Column("par3", sa.Float(), nullable=True),
        sa.Column("ast_tov", sa.Float(), nullable=True),
        sa.Column("oreb_pct", sa.Float(), nullable=True),
        sa.Column("clutch_pts", sa.Float(), nullable=True),
        sa.Column("clutch_fga", sa.Integer(), nullable=True),
        sa.Column("clutch_fg_pct", sa.Float(), nullable=True),
        sa.Column("clutch_plus_minus", sa.Float(), nullable=True),
        sa.Column("second_chance_pts", sa.Float(), nullable=True),
        sa.Column("fast_break_pts", sa.Float(), nullable=True),
    ]
    for column in season_stats_columns:
        _add_column_if_missing("season_stats", column)

    _add_column_if_missing("team_standings", sa.Column("snapshot_date", sa.Date(), nullable=True))
    _add_column_if_missing("shot_lab_snapshots", sa.Column("route_path", sa.String(length=255), nullable=True))

    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if _has_table("team_standings") and _has_column("team_standings", "snapshot_date"):
        if dialect_name == "sqlite":
            bind.execute(
                text(
                    """
                    UPDATE team_standings
                    SET snapshot_date = COALESCE(snapshot_date, date(updated_at))
                    WHERE snapshot_date IS NULL
                    """
                )
            )
            with op.batch_alter_table("team_standings", recreate="always") as batch_op:
                batch_op.alter_column("snapshot_date", existing_type=sa.Date(), nullable=False)
                if not _has_unique_constraint("team_standings", "uq_team_standing_season_date"):
                    batch_op.create_unique_constraint(
                        "uq_team_standing_season_date",
                        ["team_id", "season", "snapshot_date"],
                    )
        else:
            bind.execute(
                text(
                    """
                    UPDATE team_standings
                    SET snapshot_date = COALESCE(snapshot_date, updated_at::date)
                    WHERE snapshot_date IS NULL
                    """
                )
            )
            with op.batch_alter_table("team_standings") as batch_op:
                batch_op.alter_column("snapshot_date", existing_type=sa.Date(), nullable=False)
            bind.execute(text("ALTER TABLE team_standings DROP CONSTRAINT IF EXISTS uq_team_standing_season"))
            bind.execute(
                text(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1
                            FROM pg_constraint
                            WHERE conname = 'uq_team_standing_season_date'
                              AND conrelid = 'team_standings'::regclass
                        ) THEN
                            ALTER TABLE team_standings
                                ADD CONSTRAINT uq_team_standing_season_date
                                UNIQUE (team_id, season, snapshot_date);
                        END IF;
                    END $$;
                    """
                )
            )


def downgrade() -> None:
    pass
