# backend/app/services/security.py

from sqlalchemy.orm import Session
import yfinance as yf

from app.services.brokers.kite import KiteService
from app.schemas.base import APIResponse
from app.repositories.security import SecurityRepository
from app.enums.security import SecurityType

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

    def enrich_securities(self) -> APIResponse:
        """Enrich securities data with additional information and update the database"""
        try:
            securities = self.security_repo.get_by_fields({ "type": SecurityType.EQUITY.value }, limit=None)
            enriched_data = []
            success = 0
            failed_tickers = []
            partial_tickers = []

            for index, security in enumerate(securities):
                logger.info(f"Enriching security {index + 1}/{len(securities)}: {security.ticker} ({security.exchange})")
                ticker = security.ticker
                try:
                    data = yf.Ticker(f"{ticker}.NS")
                    info = data.info

                    if not info.get("longName") or not info.get("sector") or not info.get("industry"):
                        partial_tickers.append(ticker)
                        logger.warning(f"Partial data for ticker {ticker}. Missing fields: {[field for field in ['longName', 'sector', 'industry'] if not info.get(field)]}")

                    enriched_data.append({ "ticker": ticker, "exchange": security.exchange, "display_name": info.get("longName"), "sector": info.get("sector"), "industry": info.get("industry") })
                    success += 1
                except Exception as e:
                    failed_tickers.append(ticker)
                    logger.warning(f"Failed to fetch data for ticker {ticker}. Error: {str(e)}", exc_info=True)

            self.security_repo.bulk_update_metadata(enriched_data)
            return APIResponse(success=True, message="SECURITIES_ENRICHED", data={ "enriched_securities": success, "failed_securities": failed_tickers, "partial_securities": partial_tickers })
        except Exception as e:
            logger.error(f"Failed to enrich securities data. Error: {str(e)}", exc_info=True)
            raise
