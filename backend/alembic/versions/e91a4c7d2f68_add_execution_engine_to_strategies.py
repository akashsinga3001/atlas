"""add_execution_engine_to_strategies

Revision ID: e91a4c7d2f68
Revises: c3f8a2e1b7d4
Create Date: 2026-08-15

"""
import sqlalchemy as sa
from alembic import op

revision = 'e91a4c7d2f68'
down_revision = 'c3f8a2e1b7d4'
branch_labels = None
depends_on = None

# Maps known strategy codes to the execution engine that should run their
# entry/exit. Extend this when a new strategy is added with an engine type
# that already exists (equity or options_iron_condor) — a genuinely new
# engine shape still needs its own ExecutionEngineRegistry entry in code.
_ENGINE_BY_STRATEGY_CODE = {
    "dummy": "equity",
    "momentum_screener": "equity",
    "nifty_iron_condor": "options_iron_condor",
}


def upgrade() -> None:
    op.add_column("strategies", sa.Column("execution_engine", sa.String(length=50), nullable=True))

    conn = op.get_bind()
    for code, engine in _ENGINE_BY_STRATEGY_CODE.items():
        conn.execute(sa.text("UPDATE strategies SET execution_engine = :engine WHERE code = :code"), {"engine": engine, "code": code})

    remaining = conn.execute(sa.text("SELECT code FROM strategies WHERE execution_engine IS NULL")).fetchall()
    if remaining:
        codes = [r[0] for r in remaining]
        raise RuntimeError(f"[add_execution_engine_to_strategies] Unmapped strategies: {codes} — add an entry to _ENGINE_BY_STRATEGY_CODE before this migration can proceed.")

    op.alter_column("strategies", "execution_engine", nullable=False)


def downgrade() -> None:
    op.drop_column("strategies", "execution_engine")
