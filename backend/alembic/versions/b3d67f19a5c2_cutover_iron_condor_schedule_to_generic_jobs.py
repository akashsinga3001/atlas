"""cutover_iron_condor_schedule_to_generic_jobs

Revision ID: b3d67f19a5c2
Revises: e91a4c7d2f68
Create Date: 2026-08-15

DO NOT run this against the live system as part of a routine deploy. It
repoints the live iron-condor schedule_entries rows at the new generic
trade_entry/trade_exit tasks — see the "Unify Strategy Execution" plan's
rollout section (§6, live-migration checkpoint) for the required sequencing:
run this only after the generic-pipeline code deploy has run live through at
least one full iron-condor cycle, then immediately call POST /schedule/resync
(RedBeat's Redis state is not auto-refreshed from Postgres).

"""
import sqlalchemy as sa
from alembic import op

revision = 'b3d67f19a5c2'
down_revision = 'e91a4c7d2f68'
branch_labels = None
depends_on = None

_OLD_ENTRY_TASK = "app.jobs.iron_condor_entry.run_iron_condor_entry"
_NEW_ENTRY_TASK = "app.jobs.trade_entry.run_trade_entry"
_OLD_EXIT_TASK = "app.jobs.iron_condor_exit.run_iron_condor_exit"
_NEW_EXIT_TASK = "app.jobs.trade_exit.run_trade_exit"


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE schedule_entries SET task = :new_task WHERE task = :old_task"), {"new_task": _NEW_ENTRY_TASK, "old_task": _OLD_ENTRY_TASK})
    conn.execute(sa.text("UPDATE schedule_entries SET task = :new_task WHERE task = :old_task"), {"new_task": _NEW_EXIT_TASK, "old_task": _OLD_EXIT_TASK})


def downgrade() -> None:
    conn = op.get_bind()
    # Scoped by name, not just task string — trade_entry.run_trade_entry may
    # legitimately also serve momentum-screener rows by the time this runs.
    conn.execute(sa.text("UPDATE schedule_entries SET task = :old_task WHERE task = :new_task AND name LIKE 'iron-condor-entry%'"), {"old_task": _OLD_ENTRY_TASK, "new_task": _NEW_ENTRY_TASK})
    conn.execute(sa.text("UPDATE schedule_entries SET task = :old_task WHERE task = :new_task AND name LIKE 'iron-condor-exit%'"), {"old_task": _OLD_EXIT_TASK, "new_task": _NEW_EXIT_TASK})
