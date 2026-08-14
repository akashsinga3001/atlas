# backend/app/services/options_chain.py

from datetime import date
from sqlalchemy.orm import Session

from app.services.brokers.kite import KiteService
from app.schemas.base import APIResponse
from app.repositories.security import SecurityRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OptionsChainService:
    """Service class to keep the NFO option-contract universe in `securities` in sync with Kite.

    Mirrors SecurityService.import_securities(), but scoped to a single underlying's option
    chain (default NIFTY) and refreshed far more often — weekly options roll continuously,
    unlike the monthly equity universe.
    """

    def __init__(self, db: Session):
        self.db = db
        self.kite_service = KiteService()
        self.security_repo = SecurityRepository(db)

    def import_nifty_option_chain(self, name: str = "NIFTY") -> APIResponse:
        """Fetch all currently-listed NFO option contracts for `name` and upsert into securities.

        Deactivation runs two checks, scoped to OPTION-type rows only (never touching
        equity/index securities from the separate SecurityService.import_securities()
        pipeline): contracts no longer listed by Kite (deactivate_missing_options), and —
        as a deterministic safety net independent of this job actually running on time —
        any contract whose own expiry_date has already passed (deactivate_expired_options).
        """
        try:
            instruments = self.kite_service.fetch_nfo_option_instruments(name=name)

            if instruments.empty:
                logger.warning(f"No {name} option instruments returned from Kite API.")
                return APIResponse(success=False, message="NO_OPTION_INSTRUMENTS_FETCHED", data={ "total": 0 })

            securities_df = self.kite_service._to_option_security_row(instruments)
            active_tickers = set(securities_df['ticker'].tolist())

            upsert_result = self.security_repo.bulk_upsert(securities_df.to_dict(orient="records"))
            deactivated_missing = self.security_repo.deactivate_missing_options(active_tickers)
            deactivated_expired = self.security_repo.deactivate_expired_options(date.today())

            expiries = sorted(instruments['expiry'].unique().tolist())
            logger.info(f"Imported {len(securities_df)} {name} option contracts across {len(expiries)} expiries.")

            return APIResponse(
                success=True, message="OPTION_CHAIN_IMPORTED",
                data={ "total": len(securities_df), "expiries": [str(e) for e in expiries], "upsert_result": upsert_result, "deactivated_missing": deactivated_missing, "deactivated_expired": deactivated_expired, "deactivated": deactivated_missing + deactivated_expired },
            )
        except Exception:
            logger.error(f"Failed to import {name} option chain.", exc_info=True)
            raise
