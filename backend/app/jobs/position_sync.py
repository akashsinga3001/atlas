# backend/app/jobs/position_sync.py

from datetime import date

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.brokers.kite import KiteService
from app.services.trade import TradeService
from app.celery.tasks import PositionSyncTask
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.position_sync.run_position_sync", bind=True, base=PositionSyncTask)
def run_position_sync(self) -> dict:
    """Detect GTT-triggered exits by syncing Kite holdings against open trades"""
    db = SessionLocal()
    try:
        kite_service = KiteService()
        service = TradeService(db, kite_service=kite_service)
        service.sync_positions(as_of_date=date.today())
        logger.info("Position Sync Completed Successfully")
        return { "success": True, "message": "POSITION_SYNC_COMPLETED"}
    except Exception as e:
        logger.error(f"Position Sync Failed: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()
