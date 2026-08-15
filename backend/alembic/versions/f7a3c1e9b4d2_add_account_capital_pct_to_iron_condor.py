"""add_account_capital_pct_to_iron_condor_config

Revision ID: f7a3c1e9b4d2
Revises: d4e8b6c2a9f3
Create Date: 2026-08-15

"""
import json

from alembic import op
import sqlalchemy as sa


revision = 'f7a3c1e9b4d2'
down_revision = 'd4e8b6c2a9f3'
branch_labels = None
depends_on = None

STRATEGY_CODE = "nifty_iron_condor"
NEW_KEY = "account_capital_pct"
NEW_VALUE = 1.0  # default = whole account, identical to current behaviour until deliberately lowered


def upgrade() -> None:
    conn = op.get_bind()

    row = conn.execute(
        sa.text(
            "SELECT sv.id, sv.config FROM strategy_versions sv "
            "JOIN strategies s ON s.id = sv.strategy_id "
            "WHERE s.code = :code"
        ),
        {"code": STRATEGY_CODE},
    ).fetchone()

    if not row:
        return

    strategy_version_id, config = row
    if NEW_KEY in config:
        return

    config[NEW_KEY] = NEW_VALUE
    conn.execute(
        sa.text("UPDATE strategy_versions SET config = :config WHERE id = :id"),
        {"config": json.dumps(config), "id": strategy_version_id},
    )
    print(f"[add_account_capital_pct_to_iron_condor] strategy_versions.id={strategy_version_id} "
          f"config now includes {NEW_KEY}={NEW_VALUE}, other keys preserved: {config}")


def downgrade() -> None:
    conn = op.get_bind()

    row = conn.execute(
        sa.text(
            "SELECT sv.id, sv.config FROM strategy_versions sv "
            "JOIN strategies s ON s.id = sv.strategy_id "
            "WHERE s.code = :code"
        ),
        {"code": STRATEGY_CODE},
    ).fetchone()

    if not row:
        return

    strategy_version_id, config = row
    config.pop(NEW_KEY, None)
    conn.execute(
        sa.text("UPDATE strategy_versions SET config = :config WHERE id = :id"),
        {"config": json.dumps(config), "id": strategy_version_id},
    )
