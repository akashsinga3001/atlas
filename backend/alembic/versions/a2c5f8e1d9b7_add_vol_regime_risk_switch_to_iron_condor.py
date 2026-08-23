"""add_vol_regime_risk_switch_to_iron_condor_config

Revision ID: a2c5f8e1d9b7
Revises: f4a8c1e6b930
Create Date: 2026-08-23

"""
import json

from alembic import op
import sqlalchemy as sa


revision = 'a2c5f8e1d9b7'
down_revision = 'f4a8c1e6b930'
branch_labels = None
depends_on = None

STRATEGY_CODE = "nifty_iron_condor"
OLD_KEY = "capital_pct"
NEW_KEYS = {
    "capital_pct_calm": 0.35,
    "capital_pct_elevated": 0.75,
    "vol_regime_lookback_days": 60,
    "liquidity_lookback_days": 5,
    "liquidity_participation_pct": 0.05,
}


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
    if "capital_pct_calm" in config:
        return

    config.pop(OLD_KEY, None)
    config.update(NEW_KEYS)
    conn.execute(
        sa.text("UPDATE strategy_versions SET config = :config WHERE id = :id"),
        {"config": json.dumps(config), "id": strategy_version_id},
    )
    print(f"[add_vol_regime_risk_switch_to_iron_condor] strategy_versions.id={strategy_version_id} "
          f"config now includes {list(NEW_KEYS.keys())}, {OLD_KEY} removed: {config}")


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
    for key in NEW_KEYS:
        config.pop(key, None)
    config[OLD_KEY] = 0.35
    conn.execute(
        sa.text("UPDATE strategy_versions SET config = :config WHERE id = :id"),
        {"config": json.dumps(config), "id": strategy_version_id},
    )
    print(f"[add_vol_regime_risk_switch_to_iron_condor] strategy_versions.id={strategy_version_id} "
          f"reverted to flat {OLD_KEY}=0.35, new keys removed: {config}")
