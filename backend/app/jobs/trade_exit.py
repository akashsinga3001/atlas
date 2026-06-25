# backend/app/jobs/trade_exit.py

from datetime import date

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.strategy import StrategyVersion
from app.services.brokers.kite import KiteService
from app.services.trade import TradeService
from app.celery.tasks import TradeExitTask
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.trade_exit.run_trade_exit", bind=True, base=TradeExitTask)
def run_trade_exit(self, strategy_version_id: int) -> dict:
    """Evaluate exits for all open trades under a strategy version."""
    db = SessionLocal()
    try:
        strategy_version = db.query(StrategyVersion).filter(StrategyVersion.id == strategy_version_id).first()
        if not strategy_version:
            raise ValueError(f"StrategyVersion {strategy_version_id} not found")

        kite_service = KiteService()
        service = TradeService(db, kite_service)
        service.evaluate_exits(strategy_version=strategy_version, as_of_date=date.today())

        logger.info(f"Trade exit evaluation completed for strategy version {strategy_version_id}.")
        return { "success": True, "message": "TRADE_EXIT_COMPLETED", "data": { "strategy_version_id": strategy_version_id } }
    except Exception as e:
        logger.error(f"Trade exit evaluation failed for version {strategy_version_id}: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()
