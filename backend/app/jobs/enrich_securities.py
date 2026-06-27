# backend/app/jobs/enrich_securities.py

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.security import SecurityService
from app.utils.logger import get_logger
from app.celery.tasks import SecuritiesEnrichmentTask

from app.jobs.registry import register, JobDefinition

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.enrich_securities.enrich_securities", bind=True, base=SecuritiesEnrichmentTask)
def enrich_securities(self) -> dict:
    """Enrich securities data via scheduled Celery beat task."""
    db = SessionLocal()
    try:
        service = SecurityService(db)
        response = service.enrich_securities()

        if not response.success:
            raise RuntimeError(response.message)

        logger.info("Scheduled securities enrichment completed.")
        return response.model_dump()
    except Exception as e:
        logger.error(f"Scheduled securities enrichment failed: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()


register(JobDefinition(name="SECURITIES_ENRICHMENT", display_name="Securities Enrichment", description="Enriches securities with sector and industry metadata", group="data_pipeline", task=enrich_securities))
