# backend/app/jobs/feature_generation.py

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.feature import FeatureService
from app.utils.logger import get_logger
from app.celery.tasks import FeatureGenerationTask

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.feature_generation.generate_features", bind=True, base=FeatureGenerationTask)
def generate_features(self, type: str, securities: list = None, start_date: str = None, end_date: str = None, timeframe: str = None) -> dict:
    """Generate features for securities via scheduled Celery beat task."""
    db = SessionLocal()
    try:
        service = FeatureService(db)
        response = service.generate_security_features(type=type, securities=securities, start_date=start_date, end_date=end_date, timeframe=timeframe)

        if not response.success:
            raise RuntimeError(response.message)

        logger.info("Scheduled feature generation completed.")
        return response.model_dump()
    except Exception as e:
        logger.error(f"Scheduled feature generation failed: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()
