# backend/app/jobs/daily_account_snapshot.py

from datetime import date

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.brokers.kite import KiteService
from app.services.fund import FundService
from app.celery.tasks import DailyAccountSnapshotTask
from app.utils.logger import get_logger

from app.jobs.registry import register, JobDefinition

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.daily_account_snapshot.run_daily_account_snapshot", bind=True, base=DailyAccountSnapshotTask)
def run_daily_account_snapshot(self) -> dict:
    """Capture today's account value (cash + holdings) from Kite into account_snapshots."""
    db = SessionLocal()
    try:
        kite_service = KiteService()
        service = FundService(db, kite_service)
        snapshot = service.record_daily_snapshot(snapshot_date=date.today())
        summary = service.build_daily_summary(snapshot)

        logger.info(f"Daily account snapshot recorded for {snapshot.snapshot_date}.")
        return { "success": True, "message": "ACCOUNT_SNAPSHOT_RECORDED", "data": { "snapshot_date": str(snapshot.snapshot_date), "cash_balance": float(snapshot.cash_balance), "holdings_value": float(snapshot.holdings_value), "total_value": float(snapshot.total_value), **summary, }, }
    except Exception as e:
        logger.error(f"Daily account snapshot failed: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()


register(JobDefinition(name="DAILY_ACCOUNT_SNAPSHOT", display_name="Daily Account Snapshot", description="Records end-of-day account value (cash + holdings) for the NAV curve", group="trading", task=run_daily_account_snapshot))
