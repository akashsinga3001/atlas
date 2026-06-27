# backend/app/jobs/position_sync.py

from datetime import date

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.brokers.kite import KiteService
from app.services.trade import TradeService
from app.celery.tasks import PositionSyncTask
from app.utils.logger import get_logger

from app.jobs.registry import register, JobDefinition

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.position_sync.run_position_sync", bind=True, base=PositionSyncTask)
def run_position_sync(self) -> dict:
    """Detect GTT-triggered exits by syncing Kite holdings against open trades."""
    db = SessionLocal()
    try:
        kite_service = KiteService()
        service = TradeService(db, kite_service)
        response = service.run_position_sync(as_of_date=date.today())

        if not response.success:
            raise RuntimeError(response.message)

        logger.info("Position sync completed.")
        return response.model_dump()
    except Exception as e:
        logger.error(f"Position sync failed: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()


register(JobDefinition(name="POSITION_SYNC", display_name="Position Sync", description="Syncs open positions against Kite holdings", group="trading", task=run_position_sync))
