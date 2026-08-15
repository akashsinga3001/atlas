# backend/app/jobs/option_chain_import.py

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.options_chain import OptionsChainService
from app.celery.tasks import OptionChainImportTask
from app.utils.logger import get_logger

from app.jobs.registry import register, JobDefinition

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.option_chain_import.import_option_chain", bind=True, base=OptionChainImportTask)
def import_option_chain(self, name: str = "NIFTY") -> dict:
    """Refresh the NFO option-contract universe (weekly + monthly) for the given underlying — shared by any options strategy trading it."""
    db = SessionLocal()
    try:
        service = OptionsChainService(db)
        response = service.import_nifty_option_chain(name=name)

        if not response.success:
            raise RuntimeError(response.message)

        logger.info(f"Option chain import completed for {name}.")
        return response.model_dump()
    except Exception as e:
        logger.error(f"Option chain import failed for {name}: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()


register(JobDefinition(name="OPTION_CHAIN_IMPORT", display_name="Option Chain Import", description="Refreshes the NFO option-contract universe — shared by any options strategy trading the underlying, not just one", group="trading", task=import_option_chain))
