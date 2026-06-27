# backend/jobs/refresh_broker_token.py

from app.celery_app import celery_app
from app.services.brokers.kite import KiteService
from app.utils.logger import get_logger
from app.celery.tasks import BrokerTokenRefreshTask
from app.jobs.registry import register, JobDefinition

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.refresh_broker_token.refresh_kite_token", bind=True, base=BrokerTokenRefreshTask)
def refresh_kite_token(self) -> dict:
    """Refresh Kite token via scheduled Celery beat task."""
    try:
        service = KiteService()
        response = service.refresh_token()
        if not response.success:
            raise RuntimeError(response.message)
        logger.info("Scheduled Kite token refresh completed.")
        return response.model_dump()
    except Exception as e:
        logger.error(f"Scheduled Kite token refresh failed: {str(e)}", exc_info=True)
        raise


register(JobDefinition(name="KITE_TOKEN_REFRESH", display_name="Kite Token Refresh", description="Refreshes Kite API access token via Selenium", group="data_pipeline", task=refresh_kite_token))
