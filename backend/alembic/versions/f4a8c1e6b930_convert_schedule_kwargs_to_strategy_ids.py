"""convert_schedule_kwargs_to_strategy_ids

Revision ID: f4a8c1e6b930
Revises: b3d67f19a5c2
Create Date: 2026-08-15

DO NOT run this against the live system as part of a routine deploy. It
converts schedule_entries.kwargs from {"strategy_id": N} to {"strategy_ids":
[N]} for the 3 generic-job rows (strategy_execution / trade_entry /
trade_exit) — see the "Make strategy-execution / trade-entry / trade-exit
truly strategy-agnostic" plan's Stage B: run only after the new job code
(which accepts strategy_ids, with a legacy strategy_id shim absorbing the
old kwargs shape) has run live through at least one full cycle, then
immediately call POST /schedule/resync (RedBeat's Redis state is not
auto-refreshed from Postgres — proven gap, see Stage B verification).
"""
import json

import sqlalchemy as sa
from alembic import op

revision = 'f4a8c1e6b930'
down_revision = 'b3d67f19a5c2'
branch_labels = None
depends_on = None

_TARGET_TASKS = {
    "app.jobs.strategy_execution.execute_strategy",
    "app.jobs.trade_entry.run_trade_entry",
    "app.jobs.trade_exit.run_trade_exit",
}


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, name, task, kwargs FROM schedule_entries")).fetchall()

    converted, already_new = [], []
    for row in rows:
        if row.task not in _TARGET_TASKS:
            continue
        kwargs = row.kwargs or {}
        if "strategy_ids" in kwargs:
            already_new.append(row.name)
            continue
        if "strategy_id" not in kwargs:
            raise RuntimeError(f"[convert_schedule_kwargs] schedule_entries.name='{row.name}' (id={row.id}, task='{row.task}') "
                                f"has neither 'strategy_id' nor 'strategy_ids' in kwargs — refusing to guess.")
        new_kwargs = {k: v for k, v in kwargs.items() if k != "strategy_id"}
        new_kwargs["strategy_ids"] = [kwargs["strategy_id"]]
        conn.execute(sa.text("UPDATE schedule_entries SET kwargs = :kwargs WHERE id = :id"), {"kwargs": json.dumps(new_kwargs), "id": row.id})
        converted.append(row.name)

    # kwargs is JSON, not JSONB — no `?` containment operator available, so re-check in Python.
    recheck = conn.execute(sa.text("SELECT id, name, task, kwargs FROM schedule_entries")).fetchall()
    leftover = [row.name for row in recheck if row.task in _TARGET_TASKS and "strategy_id" in (row.kwargs or {})]
    if leftover:
        raise RuntimeError(f"[convert_schedule_kwargs] Migration incomplete — rows still carry singular 'strategy_id': {', '.join(leftover)}")

    print(f"[convert_schedule_kwargs] Converted {len(converted)} row(s): {converted}. Already-new: {already_new}.")


def downgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, name, task, kwargs FROM schedule_entries")).fetchall()
    for row in rows:
        if row.task not in _TARGET_TASKS:
            continue
        kwargs = row.kwargs or {}
        ids = kwargs.get("strategy_ids")
        if not ids:
            continue
        if len(ids) != 1:
            raise RuntimeError(f"[convert_schedule_kwargs] Cannot downgrade '{row.name}' — strategy_ids has {len(ids)} "
                                f"entries, the singular kwargs shape can't represent it. Resolve manually before downgrading.")
        new_kwargs = {k: v for k, v in kwargs.items() if k != "strategy_ids"}
        new_kwargs["strategy_id"] = ids[0]
        conn.execute(sa.text("UPDATE schedule_entries SET kwargs = :kwargs WHERE id = :id"), {"kwargs": json.dumps(new_kwargs), "id": row.id})
