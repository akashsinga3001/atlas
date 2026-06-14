# backend/jobs/refresh_broker_token.py

from app.celery_app import celery_app
from app.services.brokers.kite import KiteService
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.refresh_broker_token.refresh_kite_token")
def refresh_kite_token() -> dict:
    """Refresh Kite token via scheduled Celery beat task."""
    service = KiteService()
    response = service.refresh_token()
    logger.info("Scheduled Kite token refresh completed.")
    return { "success": response.success, "message": response.message, "data": response.data }
