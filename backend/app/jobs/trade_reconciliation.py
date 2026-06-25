# backend/app/jobs/trade_reconciliation.py

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.brokers.kite import KiteService
from app.services.trade import TradeService
from app.celery.tasks import TradeReconciliationTask
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.trade_reconciliation.run_trade_reconciliation", bind=True, base=TradeReconciliationTask)
def run_trade_reconciliation(self) -> dict:
    """Cross-check pending trades against Kite order history and resolve any unconfirmed fills."""
    db = SessionLocal()
    try:
        kite_service = KiteService()
        service = TradeService(db, kite_service)
        response = service.run_reconciliation()

        if not response.success:
            raise RuntimeError(response.message)

        logger.info("Trade reconciliation completed.")
        return response.model_dump()
    except Exception as e:
        logger.error(f"Trade reconciliation failed: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()
