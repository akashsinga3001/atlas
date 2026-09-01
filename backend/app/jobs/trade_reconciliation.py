# backend/app/jobs/trade_reconciliation.py

from datetime import date

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.brokers.kite import KiteService
from app.services.trade import TradeService
from app.services.options_trade import OptionsTradeService
from app.celery.tasks import TradeReconciliationTask
from app.utils.logger import get_logger

from app.jobs.registry import register, JobDefinition

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.trade_reconciliation.run_trade_reconciliation", bind=True, base=TradeReconciliationTask)
def run_trade_reconciliation(self) -> dict:
    """Cross-check pending equity trades and options legs against Kite order history and resolve any unconfirmed fills."""
    db = SessionLocal()
    try:
        kite_service = KiteService()

        equity_response = TradeService(db, kite_service).run_reconciliation()
        if not equity_response.success:
            raise RuntimeError(equity_response.message)

        options_response = OptionsTradeService(db, kite_service).run_reconciliation(as_of_date=date.today())
        if not options_response.success:
            raise RuntimeError(options_response.message)

        logger.info("Trade reconciliation completed.")
        return {
            "success": True,
            "message": "TRADE_RECONCILIATION_COMPLETED",
            "data": {
                "resolved_equity": equity_response.data["resolved"],
                "resolved_options": options_response.data["resolved"],
            },
        }
    except Exception as e:
        logger.error(f"Trade reconciliation failed: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()


register(JobDefinition(name="TRADE_RECONCILIATION", display_name="Trade Reconciliation", description="Resolves pending equity trades and options legs against Kite order history", group="trading", task=run_trade_reconciliation))
