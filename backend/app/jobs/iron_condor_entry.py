# backend/app/jobs/iron_condor_entry.py

from datetime import date

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.repositories.strategy import StrategyVersionRepository
from app.services.brokers.kite import KiteService
from app.services.options_trade import OptionsTradeService
from app.celery.tasks import IronCondorEntryTask
from app.utils.logger import get_logger

from app.schemas.strategy import StrategyExecutionRequest
from app.jobs.registry import register, JobDefinition

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.iron_condor_entry.run_iron_condor_entry", bind=True, base=IronCondorEntryTask)
def run_iron_condor_entry(self, strategy_id: int) -> dict:
    """Enter the week's 4-leg iron condor if today is the entry day for an unconsumed signal."""
    db = SessionLocal()
    try:
        strategy_version = StrategyVersionRepository(db).get_active_for_strategy(strategy_id)
        if not strategy_version:
            raise ValueError(f"No active StrategyVersion found for strategy {strategy_id}")

        kite_service = KiteService()
        service = OptionsTradeService(db, kite_service)
        response = service.run_entry(strategy_version=strategy_version, as_of_date=date.today())

        if not response.success:
            raise RuntimeError(response.message)

        logger.info(f"Iron condor entry completed for strategy {strategy_id}.")
        return response.model_dump()
    except Exception as e:
        logger.error(f"Iron condor entry failed for strategy {strategy_id}: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()


register(JobDefinition(name="IRON_CONDOR_ENTRY", display_name="Iron Condor Entry", description="Places the 4-leg iron condor entry orders", group="trading", task=run_iron_condor_entry, parameters_schema=StrategyExecutionRequest))
