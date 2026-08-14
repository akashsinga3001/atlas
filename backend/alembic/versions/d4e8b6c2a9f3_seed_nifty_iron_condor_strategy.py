"""seed_nifty_iron_condor_strategy

Revision ID: d4e8b6c2a9f3
Revises: c1a2f9d3e7b1
Create Date: 2026-08-14

"""
import json

from alembic import op
import sqlalchemy as sa


revision = 'd4e8b6c2a9f3'
down_revision = 'c1a2f9d3e7b1'
branch_labels = None
depends_on = None

STRATEGY_CODE = "nifty_iron_condor"

CONFIG = {
    "underlying_ticker": "NIFTY 50",
    "option_name": "NIFTY",
    "signal_day_of_week": 0,
    "strike_step": 50,
    "short_otm_pct": 0.03,
    "long_otm_pct": 0.06,
    "capital_pct": 0.20,
    "max_lots": 4,
    "hold_days": 5,
}


def upgrade() -> None:
    conn = op.get_bind()

    existing = conn.execute(sa.text("SELECT id FROM strategies WHERE code = :code"), {"code": STRATEGY_CODE}).fetchone()
    if existing:
        return

    strategy_id = conn.execute(
        sa.text("INSERT INTO strategies (code, name, is_active) VALUES (:code, :name, true) RETURNING id"),
        {"code": STRATEGY_CODE, "name": "NIFTY Iron Condor"},
    ).scalar()

    strategy_version_id = conn.execute(
        sa.text(
            "INSERT INTO strategy_versions (strategy_id, version, config, implementation_class, exit_evaluator_class, is_active) "
            "VALUES (:strategy_id, 1, :config, :implementation_class, NULL, true) RETURNING id"
        ),
        {"strategy_id": strategy_id, "config": json.dumps(CONFIG), "implementation_class": STRATEGY_CODE},
    ).scalar()

    print(f"[seed_nifty_iron_condor_strategy] Seeded strategy_versions.id={strategy_version_id} "
          f"— use this ID in celery_schedule.py for the iron condor schedule entries.")


def downgrade() -> None:
    conn = op.get_bind()
    row = conn.execute(sa.text("SELECT id FROM strategies WHERE code = :code"), {"code": STRATEGY_CODE}).fetchone()
    if not row:
        return
    strategy_id = row[0]
    conn.execute(sa.text("DELETE FROM strategy_versions WHERE strategy_id = :sid"), {"sid": strategy_id})
    conn.execute(sa.text("DELETE FROM strategies WHERE id = :sid"), {"sid": strategy_id})
