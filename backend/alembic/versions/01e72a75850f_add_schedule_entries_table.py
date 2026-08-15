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


def _get_strategy_id(conn, code: str) -> int:
    row = conn.execute(sa.text("SELECT id FROM strategies WHERE code = :code"), { "code": code }).fetchone()
    if not row:
        raise RuntimeError(f"[add_schedule_entries_table] strategies.code = '{code}' not found — cannot seed schedule_entries.kwargs.strategy_id")
    return row[0]


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

    conn = op.get_bind()
    iron_condor_id = _get_strategy_id(conn, "nifty_iron_condor")
    momentum_id = _get_strategy_id(conn, "momentum_screener")

    entries = [
        # -- data_pipeline --
        dict(name="kite-daily-token-refresh-07:45", task="app.jobs.refresh_broker_token.refresh_kite_token", minute="45", hour="7", day_of_week="*", day_of_month="*", month_of_year="*", kwargs={}, enabled=True, group="data_pipeline", description="Refreshes the Kite API access token."),
        dict(name="securities-monthly-import-08:00", task="app.jobs.securities_import.import_securities", minute="0", hour="8", day_of_week="*", day_of_month="1", month_of_year="*", kwargs={}, enabled=True, group="data_pipeline", description="Imports the NIFTY 500 securities universe."),
        dict(name="securities-monthly-enrichment-08:30", task="app.jobs.enrich_securities.enrich_securities", minute="30", hour="8", day_of_week="*", day_of_month="1", month_of_year="*", kwargs={}, enabled=True, group="data_pipeline", description="Enriches securities with sector/industry metadata."),
        dict(name="ohlcv-import-live-refresh", task="app.jobs.ohlcv_import.import_ohlcv_data", minute="*/10", hour="9-15", day_of_week="1-5", day_of_month="*", month_of_year="*", kwargs={"type": "live_refresh"}, enabled=True, group="data_pipeline", description="Live intraday OHLCV refresh."),
        dict(name="feature-generation-live-refresh", task="app.jobs.feature_generation.generate_features", minute="2-59/10", hour="9-15", day_of_week="1-5", day_of_month="*", month_of_year="*", kwargs={"type": "live_refresh", "timeframe": "1d"}, enabled=True, group="data_pipeline", description="Live intraday feature refresh."),
        dict(name="ohlcv-daily-import-08:00", task="app.jobs.ohlcv_import.import_ohlcv_data", minute="0", hour="8", day_of_week="1-5", day_of_month="*", month_of_year="*", kwargs={"type": "incremental", "timeframe": "1d"}, enabled=True, group="data_pipeline", description="Daily incremental OHLCV import."),
        dict(name="feature-generation-daily-import-16:30", task="app.jobs.feature_generation.generate_features", minute="30", hour="16", day_of_week="1-5", day_of_month="*", month_of_year="*", kwargs={"type": "incremental", "timeframe": "1d"}, enabled=True, group="data_pipeline", description="Daily incremental feature generation."),
        # -- trading --
        dict(name="trade-position-sync-15:15", task="app.jobs.position_sync.run_position_sync", minute="15", hour="15", day_of_week="1-5", day_of_month="*", month_of_year="*", kwargs={}, enabled=True, group="trading", description="Syncs open trades against Kite holdings."),
        dict(name="trade-reconciliation-16:00", task="app.jobs.trade_reconciliation.run_trade_reconciliation", minute="0", hour="16", day_of_week="1-5", day_of_month="*", month_of_year="*", kwargs={}, enabled=True, group="trading", description="Resolves pending orders against Kite order history."),
        dict(name="daily-account-snapshot-16:05", task="app.jobs.daily_account_snapshot.run_daily_account_snapshot", minute="5", hour="16", day_of_week="1-5", day_of_month="*", month_of_year="*", kwargs={}, enabled=True, group="trading", description="Records end-of-day account snapshot."),
        dict(name="iron-condor-option-chain-import-08:10", task="app.jobs.iron_condor_option_chain_import.import_iron_condor_option_chain", minute="10", hour="8", day_of_week="1-5", day_of_month="*", month_of_year="*", kwargs={}, enabled=True, group="trading", description="Refreshes the NIFTY weekly option-contract universe."),
        dict(name="iron-condor-signal-15:21", task="app.jobs.strategy_execution.execute_strategy", minute="21", hour="15", day_of_week="1", day_of_month="*", month_of_year="*", kwargs={"strategy_id": iron_condor_id}, enabled=True, group="trading", description="NIFTY iron condor weekly signal generation."),
        dict(name="iron-condor-entry-09:20-to-14:50", task="app.jobs.iron_condor_entry.run_iron_condor_entry", minute="20,50", hour="9-14", day_of_week="1-5", day_of_month="*", month_of_year="*", kwargs={"strategy_id": iron_condor_id}, enabled=True, group="trading", description="Places the iron condor's 4-leg entry orders."),
        dict(name="iron-condor-exit-15:10", task="app.jobs.iron_condor_exit.run_iron_condor_exit", minute="10", hour="15", day_of_week="1-5", day_of_month="*", month_of_year="*", kwargs={"strategy_id": iron_condor_id}, enabled=True, group="trading", description="Evaluates and executes iron condor exits."),
        # -- momentum screener: disabled, was commented-out code in celery_schedule.py --
        dict(name="strategy-execution-15:20", task="app.jobs.strategy_execution.execute_strategy", minute="20", hour="15", day_of_week="1-5", day_of_month="*", month_of_year="*", kwargs={"strategy_id": momentum_id}, enabled=False, group="trading", description="Momentum screener signal generation (disabled 2026-08-14 in favour of the iron condor)."),
        dict(name="trade-exit-15:25", task="app.jobs.trade_exit.run_trade_exit", minute="25", hour="15", day_of_week="1-5", day_of_month="*", month_of_year="*", kwargs={"strategy_id": momentum_id}, enabled=False, group="trading", description="Momentum screener exit evaluation (disabled 2026-08-14 in favour of the iron condor)."),
        dict(name="trade-entry-15:27", task="app.jobs.trade_entry.run_trade_entry", minute="27", hour="15", day_of_week="1-5", day_of_month="*", month_of_year="*", kwargs={"strategy_id": momentum_id}, enabled=False, group="trading", description="Momentum screener trade entry (disabled 2026-08-14 in favour of the iron condor)."),
    ]

    table = sa.table(
        "schedule_entries",
        sa.column("name", sa.String), sa.column("task", sa.String),
        sa.column("minute", sa.String), sa.column("hour", sa.String), sa.column("day_of_week", sa.String), sa.column("day_of_month", sa.String), sa.column("month_of_year", sa.String),
        sa.column("kwargs", sa.JSON), sa.column("enabled", sa.Boolean), sa.column("description", sa.Text), sa.column("group", sa.String),
    )
    op.bulk_insert(table, entries)

    print(f"[add_schedule_entries_table] Seeded {len(entries)} schedule_entries rows (iron_condor strategy_id={iron_condor_id}, momentum strategy_id={momentum_id}).")


def downgrade() -> None:
    op.drop_table("schedule_entries")
