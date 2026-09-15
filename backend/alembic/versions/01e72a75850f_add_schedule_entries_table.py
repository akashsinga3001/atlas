"""add_schedule_entries_table

Revision ID: 01e72a75850f
Revises: 2e295b61e2e7
Create Date: 2026-08-15

"""
import sqlalchemy as sa
from alembic import op

revision = '01e72a75850f'
down_revision = '2e295b61e2e7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schedule_entries",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("task", sa.String(length=255), nullable=False),
        sa.Column("minute", sa.String(length=100), nullable=False, server_default="*"),
        sa.Column("hour", sa.String(length=100), nullable=False, server_default="*"),
        sa.Column("day_of_week", sa.String(length=100), nullable=False, server_default="*"),
        sa.Column("day_of_month", sa.String(length=100), nullable=False, server_default="*"),
        sa.Column("month_of_year", sa.String(length=100), nullable=False, server_default="*"),
        sa.Column("kwargs", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("group", sa.String(length=50), nullable=False, server_default="trading"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_unique_constraint("uix_schedule_entries_name", "schedule_entries", ["name"])


def downgrade() -> None:
    op.drop_table("schedule_entries")
