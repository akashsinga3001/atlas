"""fix_trade_enum_values

Revision ID: fix_trade_enum_values
Revises: 11e117c627f6
Create Date: 2026-06-26

"""
from alembic import op
import sqlalchemy as sa

revision = 'fix_trade_enum_values'
down_revision = '11e117c627f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fix tradestatus enum: drop old (PENDING/COMPLETED/FAILED) and recreate with correct values
    op.execute("ALTER TABLE trades ALTER COLUMN status TYPE VARCHAR(50)")
    op.execute("DROP TYPE IF EXISTS tradestatus")
    op.execute("CREATE TYPE tradestatus AS ENUM ('pending', 'open', 'closed')")
    op.execute("ALTER TABLE trades ALTER COLUMN status TYPE tradestatus USING status::tradestatus")

    # Fix exitreason enum: drop old (ATR_STOP/TIMEOUT/MANUAL) and recreate with lowercase values
    op.execute("ALTER TABLE trades ALTER COLUMN exit_reason TYPE VARCHAR(50)")
    op.execute("DROP TYPE IF EXISTS exitreason")
    op.execute("CREATE TYPE exitreason AS ENUM ('atr_stop', 'timeout', 'manual')")
    op.execute("ALTER TABLE trades ALTER COLUMN exit_reason TYPE exitreason USING exit_reason::exitreason")


def downgrade() -> None:
    op.execute("ALTER TABLE trades ALTER COLUMN status TYPE VARCHAR(50)")
    op.execute("DROP TYPE IF EXISTS tradestatus")
    op.execute("CREATE TYPE tradestatus AS ENUM ('PENDING', 'COMPLETED', 'FAILED')")
    op.execute("ALTER TABLE trades ALTER COLUMN status TYPE tradestatus USING status::tradestatus")

    op.execute("ALTER TABLE trades ALTER COLUMN exit_reason TYPE VARCHAR(50)")
    op.execute("DROP TYPE IF EXISTS exitreason")
    op.execute("CREATE TYPE exitreason AS ENUM ('ATR_STOP', 'TIMEOUT', 'MANUAL')")
    op.execute("ALTER TABLE trades ALTER COLUMN exit_reason TYPE exitreason USING exit_reason::exitreason")
