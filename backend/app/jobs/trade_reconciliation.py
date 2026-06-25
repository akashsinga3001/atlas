# backend/app/jobs/trade_reconciliation.py

from datetime import date

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.brokers.kite import KiteService
from app.services.trade import TradeService
from app.repositories.trade import TradeRepository
from app.enums.trade import TradeStatus
from app.celery.tasks import TradeReconciliationTask
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.trade_reconciliation.run_trade_reconciliation", bind=True, base=TradeReconciliationTask)
def run_trade_reconciliation(self) -> dict:
    """Cross-check pending trades against Kite order history and resolve any unconfirmed fills."""
    db = SessionLocal()
    try:
        kite_service = KiteService()
        trade_repo = TradeRepository(db)
        trade_service = TradeService(db, kite_service)

        pending_trades = trade_repo.get_pending_trades()
        resolved = 0

        for trade in pending_trades:
            ticker = trade.security.ticker
            try:
                fill_price, fill_quantity = trade_service._poll_fill(trade.kite_entry_order_id)
                if fill_price is None:
                    logger.warning(f"Reconciliation: fill still not confirmed for trade {trade.id} ({ticker})")
                    continue

                gtt_id = trade_service._place_gtt(ticker, fill_price, fill_quantity)
                trade_repo.update(trade, { "status": TradeStatus.OPEN, "fill_price": fill_price, "fill_quantity": fill_quantity, "kite_gtt_id": str(gtt_id), })
                resolved += 1
                logger.info(f"Reconciliation: resolved PENDING trade {trade.id} ({ticker})")
            except Exception as e:
                logger.error(f"Reconciliation failed for trade {trade.id} ({ticker}): {e}", exc_info=True)

        logger.info(f"Trade reconciliation completed. Resolved {resolved} pending trade(s).")
        return { "success": True, "message": "TRADE_RECONCILIATION_COMPLETED", "data": { "resolved": resolved } }
    except Exception as e:
        logger.error(f"Trade reconciliation failed: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()
