# backend/app/seeders/schedule_seeder.py

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.schedule import ScheduleEntry
from app.models.strategy import Strategy
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _strategy_id(db: Session, code: str) -> int:
    """Look up a strategy's PK by code — resolved at seed-time rather than hardcoded, since a
    strategy's id isn't known until strategy_seeder.seed() has run (which main.py's lifespan
    always does first)."""
    strategy = db.query(Strategy).filter(Strategy.code == code).first()
    if not strategy:
        raise RuntimeError(f"[schedule_seeder] strategies.code = '{code}' not found — seed strategies before schedule entries.")
    return strategy.id


def build_schedule_entries(db: Session) -> list[dict]:
    momentum_id = _strategy_id(db, "momentum_screener")
    relative_leadership_id = _strategy_id(db, "relative_leadership_v1")

    return [
        # -- data_pipeline --
        {"name": "kite-daily-token-refresh-07:45", "task": "app.jobs.refresh_broker_token.refresh_kite_token", "minute": "45", "hour": "7", "day_of_week": "*", "day_of_month": "*", "month_of_year": "*", "kwargs": {}, "enabled": True, "group": "data_pipeline", "description": "Refreshes the Kite API access token."},
        {"name": "securities-monthly-import-08:00", "task": "app.jobs.securities_import.import_securities", "minute": "0", "hour": "8", "day_of_week": "*", "day_of_month": "1", "month_of_year": "*", "kwargs": {}, "enabled": True, "group": "data_pipeline", "description": "Imports the NIFTY 500 securities universe."},
        {"name": "securities-monthly-enrichment-08:30", "task": "app.jobs.enrich_securities.enrich_securities", "minute": "30", "hour": "8", "day_of_week": "*", "day_of_month": "1", "month_of_year": "*", "kwargs": {}, "enabled": True, "group": "data_pipeline", "description": "Enriches securities with sector/industry metadata."},
        {"name": "ohlcv-import-live-refresh", "task": "app.jobs.ohlcv_import.import_ohlcv_data", "minute": "*/10", "hour": "9-15", "day_of_week": "1-5", "day_of_month": "*", "month_of_year": "*", "kwargs": {"type": "live_refresh"}, "enabled": True, "group": "data_pipeline", "description": "Live intraday OHLCV refresh."},
        {"name": "feature-generation-live-refresh", "task": "app.jobs.feature_generation.generate_features", "minute": "2-59/10", "hour": "9-15", "day_of_week": "1-5", "day_of_month": "*", "month_of_year": "*", "kwargs": {"type": "live_refresh", "timeframe": "1d"}, "enabled": True, "group": "data_pipeline", "description": "Live intraday feature refresh."},
        {"name": "ohlcv-daily-import-08:00", "task": "app.jobs.ohlcv_import.import_ohlcv_data", "minute": "0", "hour": "8", "day_of_week": "1-5", "day_of_month": "*", "month_of_year": "*", "kwargs": {"type": "incremental", "timeframe": "1d"}, "enabled": True, "group": "data_pipeline", "description": "Daily incremental OHLCV import."},
        {"name": "feature-generation-daily-import-16:30", "task": "app.jobs.feature_generation.generate_features", "minute": "30", "hour": "16", "day_of_week": "1-5", "day_of_month": "*", "month_of_year": "*", "kwargs": {"type": "incremental", "timeframe": "1d"}, "enabled": True, "group": "data_pipeline", "description": "Daily incremental feature generation."},
        # -- trading --
        {"name": "trade-position-sync-15:15", "task": "app.jobs.position_sync.run_position_sync", "minute": "15", "hour": "15", "day_of_week": "1-5", "day_of_month": "*", "month_of_year": "*", "kwargs": {}, "enabled": True, "group": "trading", "description": "Syncs open trades against Kite holdings."},
        # 5-min cadence during market hours, not once-daily — a delayed fill on entry (or any
        # PENDING trade) should be resolved within minutes, not sit unconfirmed for hours.
        # Re-derived from CLAUDE.md's job-cadence history (established 2026-09-01) after this
        # entry's data was moved out of a migration and initially copied that migration's
        # original, pre-optimization once-daily values verbatim. Name kept as "-16:00" (now a
        # misnomer) rather than renamed, since seeding is idempotent by name and the update API
        # has no way to rename an existing row — renaming here would insert a duplicate instead
        # of updating the live entry on any future fresh seed.
        {"name": "trade-reconciliation-16:00", "task": "app.jobs.trade_reconciliation.run_trade_reconciliation", "minute": "*/5", "hour": "9-15", "day_of_week": "1-5", "day_of_month": "*", "month_of_year": "*", "kwargs": {}, "enabled": True, "group": "trading", "description": "Resolves pending orders against Kite order history (5-min cadence during market hours)."},
        {"name": "daily-account-snapshot-16:05", "task": "app.jobs.daily_account_snapshot.run_daily_account_snapshot", "minute": "5", "hour": "16", "day_of_week": "1-5", "day_of_month": "*", "month_of_year": "*", "kwargs": {}, "enabled": True, "group": "trading", "description": "Records end-of-day account snapshot."},
        # -- momentum screener: disabled, was commented-out code in celery_schedule.py --
        {"name": "strategy-execution-15:20", "task": "app.jobs.strategy_execution.execute_strategy", "minute": "20", "hour": "15", "day_of_week": "1-5", "day_of_month": "*", "month_of_year": "*", "kwargs": {"strategy_id": momentum_id}, "enabled": False, "group": "trading", "description": "Momentum screener signal generation (disabled 2026-08-14 in favour of the iron condor)."},
        {"name": "trade-exit-15:25", "task": "app.jobs.trade_exit.run_trade_exit", "minute": "25", "hour": "15", "day_of_week": "1-5", "day_of_month": "*", "month_of_year": "*", "kwargs": {"strategy_id": momentum_id}, "enabled": False, "group": "trading", "description": "Momentum screener exit evaluation (disabled 2026-08-14 in favour of the iron condor)."},
        {"name": "trade-entry-15:27", "task": "app.jobs.trade_entry.run_trade_entry", "minute": "27", "hour": "15", "day_of_week": "1-5", "day_of_month": "*", "month_of_year": "*", "kwargs": {"strategy_id": momentum_id}, "enabled": False, "group": "trading", "description": "Momentum screener trade entry (disabled 2026-08-14 in favour of the iron condor)."},
        # -- relative_leadership_v1: disabled until historical data is backfilled and the user
        # is ready to go live. Signal generation runs after end-of-day features are ready;
        # entry executes at next session's open with allow_stale_signals=True since the run
        # feeding it is dated yesterday, not today, by design (see run_entry's staleness check).
        {"name": "relative-leadership-v1-strategy-execution-16:35", "task": "app.jobs.strategy_execution.execute_strategy", "minute": "35", "hour": "16", "day_of_week": "1-5", "day_of_month": "*", "month_of_year": "*", "kwargs": {"strategy_ids": [relative_leadership_id]}, "enabled": False, "group": "trading", "description": "Relative Leadership V1 signal generation, run after end-of-day feature generation completes."},
        {"name": "relative-leadership-v1-trade-entry-09:16", "task": "app.jobs.trade_entry.run_trade_entry", "minute": "16", "hour": "9", "day_of_week": "1-5", "day_of_month": "*", "month_of_year": "*", "kwargs": {"strategy_ids": [relative_leadership_id], "allow_stale_signals": True}, "enabled": False, "group": "trading", "description": "Relative Leadership V1 entry at next session's open, executing yesterday's signals."},
        {"name": "relative-leadership-v1-trade-exit-15:20", "task": "app.jobs.trade_exit.run_trade_exit", "minute": "20", "hour": "15", "day_of_week": "1-5", "day_of_month": "*", "month_of_year": "*", "kwargs": {"strategy_ids": [relative_leadership_id]}, "enabled": False, "group": "trading", "description": "Relative Leadership V1 3-session deterioration exit evaluation."},
    ]


def seed_schedule_entry(db: Session, *, name: str, **fields) -> None:
    entry = db.query(ScheduleEntry).filter(ScheduleEntry.name == name).first()

    if entry is None:
        db.add(ScheduleEntry(name=name, **fields))
        db.commit()


def seed() -> None:
    """Seed schedule entries into the database.

    Only inserts into Postgres — Celery beat reads from RedBeat's Redis-backed schedule,
    which this does not touch. After running this against a fresh database, call
    POST /schedule/resync once to push every entry into Redis.
    """
    db = SessionLocal()
    try:
        for entry in build_schedule_entries(db):
            seed_schedule_entry(db, **entry)
        logger.info("Seeded schedule entries into the database.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
