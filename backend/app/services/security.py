# backend/app/services/security.py

from sqlalchemy.orm import Session

from app.services.brokers.kite import KiteService
from app.schemas.base import APIResponse
from app.repositories.security import SecurityRepository

from app.utils.logger import get_logger

logger = get_logger(__name__)


class SecurityService:
    """Service class to manage securities data and interactions with the Kite API."""

    def __init__(self, db: Session):
        self.db = db
        self.kite_service = KiteService()
        self.security_repo = SecurityRepository(db)

    def import_securities(self) -> APIResponse:
        """Synchronize securities data from the Kite API and update the database."""
        try:
            securities_df = self.kite_service.fetch_instruments()
            upsert_result = self.security_repo.bulk_upsert(securities_df.to_dict(orient="records"))
            return APIResponse(success=True, message="SECURITIES_IMPORTED", data={ "count": len(securities_df), "upsert_result": upsert_result })
        except Exception:
            logger.error("Failed to import securities data.", exc_info=True)
            raise
