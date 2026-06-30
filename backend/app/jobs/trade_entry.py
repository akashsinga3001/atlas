# backend/app/jobs/trade_entry.py

from datetime import date

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.strategy import StrategyVersion
from app.services.brokers.kite import KiteService
from app.services.trade import TradeService
from app.celery.tasks import TradeEntryTask
from app.utils.logger import get_logger

from app.schemas.strategy import TradeEntryRequest
from app.jobs.registry import register, JobDefinition

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.trade_entry.run_trade_entry", bind=True, base=TradeEntryTask)
def run_trade_entry(self, strategy_version_id: int, allow_stale_signals: bool = False) -> dict:
    """Evaluate signals and open new trades up to available slot count."""
    db = SessionLocal()
    try:
        strategy_version = db.query(StrategyVersion).filter(StrategyVersion.id == strategy_version_id).first()
        if not strategy_version:
            raise ValueError(f"StrategyVersion {strategy_version_id} not found")

        kite_service = KiteService()
        service = TradeService(db, kite_service)
        response = service.run_entry(strategy_version=strategy_version, as_of_date=date.today(), allow_stale_signals=allow_stale_signals)

        if not response.success:
            raise RuntimeError(response.message)

        logger.info(f"Trade entry completed for strategy version {strategy_version_id}.")
        return response.model_dump()
    except Exception as e:
        logger.error(f"Trade entry failed for version {strategy_version_id}: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()


register(JobDefinition(name="TRADE_ENTRY", display_name="Trade Entry", description="Places buy orders for new signals", group="trading", task=run_trade_entry, parameters_schema=TradeEntryRequest))
