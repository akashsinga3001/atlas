"""add_trade_entry_15_15_retry_schedule

Adds the 15:15 same-day trade-entry retry for the NIFTY Iron Condor strategy. Without
it, a position closing exactly on its planned_exit_date frees its slot only at the
15:10 exit tick — after the 09:20-14:50 entry window has already ended for the day —
letting that week's signal expire unconsumed. This was created live via POST /schedule
on 2026-08-24 (see ScheduleEntry id 23 / RedBeat key "redbeat:trade-entry-15:15-retry");
this migration exists so a fresh database rebuild doesn't silently lose it.

Note: inserting the row here only makes it durable in Postgres. RedBeat's Redis-backed
schedule (what Celery beat actually reads) is populated by ScheduleService on create/update,
not by this migration — after a fresh rebuild, call POST /schedule/resync once to push
every Postgres row (including this one) into Redis.

Revision ID: c3e9d7a1f204
Revises: b8f3d6a1c452
Create Date: 2026-08-24

"""
import json

from alembic import op
import sqlalchemy as sa

revision = 'c3e9d7a1f204'
down_revision = 'b8f3d6a1c452'
branch_labels = None
depends_on = None

ENTRY_NAME = "trade-entry-15:15-retry"


def upgrade() -> None:
    conn = op.get_bind()

    exists = conn.execute(sa.text("SELECT 1 FROM schedule_entries WHERE name = :name"), {"name": ENTRY_NAME}).fetchone()
    if exists:
        return

    conn.execute(
        sa.text(
            "INSERT INTO schedule_entries (name, task, minute, hour, day_of_week, day_of_month, month_of_year, kwargs, enabled, description, group, created_at, updated_at) "
            "VALUES (:name, :task, :minute, :hour, :day_of_week, :day_of_month, :month_of_year, :kwargs, :enabled, :description, :group, now(), now())"
        ),
        {
            "name": ENTRY_NAME,
            "task": "app.jobs.trade_entry.run_trade_entry",
            "minute": "15",
            "hour": "15",
            "day_of_week": "1-5",
            "day_of_month": "*",
            "month_of_year": "*",
            "kwargs": json.dumps({"strategy_ids": [3]}),
            "enabled": True,
            "description": "Same-day re-entry retry after the 15:10 exit tick. A position closing exactly on its planned_exit_date frees the slot too late for the 09:20-14:50 entry window, letting that week's signal expire unconsumed.",
            "group": "trading",
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM schedule_entries WHERE name = :name"), {"name": ENTRY_NAME})
