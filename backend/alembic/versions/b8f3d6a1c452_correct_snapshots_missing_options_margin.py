"""correct_snapshots_missing_options_margin

Corrects account_snapshots rows for 2026-08-18 through 2026-08-21, which understated
total_value by the full amount of margin blocked for the open NIFTY Iron Condor position.
record_daily_snapshot() only ever counted Atlas-tracked equity holdings, never margin
blocked for options (NRML) positions — see the accompanying fix in FundService. These four
rows were recorded through the buggy path (holdings_value=0.00 despite an open options
position) and made the NAV curve / true-return calculation show a ~50% false loss against
a real realized P&L of -Rs 546.

Uses the live span+exposure margin figure (Rs 111,843.70) observed for this position as the
correction amount for all four rows, since the position's lot size was unchanged across this
window (Kite doesn't expose historical per-day margin, so this is the best available proxy —
far closer to correct than the Rs 0 currently stored).

Revision ID: b8f3d6a1c452
Revises: a2c5f8e1d9b7
Create Date: 2026-08-24

"""
from alembic import op
import sqlalchemy as sa

revision = 'b8f3d6a1c452'
down_revision = 'a2c5f8e1d9b7'
branch_labels = None
depends_on = None

BLOCKED_MARGIN = 111843.70

# (snapshot_date, original_holdings_value, original_total_value)
AFFECTED_ROWS = [
    ('2026-08-18', 0.00, 115009.96),
    ('2026-08-19', 0.00, 114508.26),
    ('2026-08-20', 0.00, 113888.19),
    ('2026-08-21', 0.00, 113571.80),
]


def upgrade() -> None:
    conn = op.get_bind()
    for snapshot_date, original_holdings, original_total in AFFECTED_ROWS:
        # Idempotency guard: only touch rows still holding the known-buggy original value,
        # so re-running this migration (or running it after a manual fix) is a no-op.
        conn.execute(
            sa.text(
                "UPDATE account_snapshots "
                "SET holdings_value = holdings_value + :margin, total_value = total_value + :margin "
                "WHERE snapshot_date = :snapshot_date AND holdings_value = :original_holdings AND total_value = :original_total"
            ),
            {"margin": BLOCKED_MARGIN, "snapshot_date": snapshot_date, "original_holdings": original_holdings, "original_total": original_total},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for snapshot_date, original_holdings, original_total in AFFECTED_ROWS:
        corrected_total = original_total + BLOCKED_MARGIN
        conn.execute(
            sa.text(
                "UPDATE account_snapshots "
                "SET holdings_value = :original_holdings, total_value = :original_total "
                "WHERE snapshot_date = :snapshot_date AND total_value = :corrected_total"
            ),
            {"original_holdings": original_holdings, "original_total": original_total, "snapshot_date": snapshot_date, "corrected_total": corrected_total},
        )
