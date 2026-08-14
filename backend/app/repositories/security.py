# backend/app/repositories/security.py

from typing import Optional, List, Dict, Any
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.repositories.base import BaseRepository
from app.models.security import Security
from app.enums.security import SecurityType, SecurityExchange
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SecurityRepository(BaseRepository):
    """Repository class for managing Security entities in the database."""

    def __init__(self, db: Session):
        super().__init__(Security, db)

    def get_by_ticker_exchange(self, ticker: str, exchange: str) -> Optional[Security]:
        """Fetch a security by its ticker and exchange."""
        matches = self.get_by_fields({ 'ticker': ticker, 'exchange': exchange })
        return matches[0] if matches else None

    def bulk_upsert(self, securities_data: List[Dict[str, Any]], active_tickers: set[str] | None = None) -> Dict[str, int]:
        """Bulk upsert securities data into the database.

        If active_tickers is provided, any security currently marked is_active=True whose
        ticker is not in that set will be deactivated — handles constituent removals.
        """
        inserted = 0
        updated = 0
        deactivated = 0

        for sec_data in securities_data:
            ticker = sec_data.get('ticker')
            exchange = sec_data.get('exchange')

            if not ticker or not exchange:
                logger.warning(f"Skipping security with missing ticker or exchange: {sec_data}")
                continue

            existing = self.get_by_ticker_exchange(ticker, exchange)

            if existing:
                update_fields = { 'broker_token': sec_data.get('broker_token'), 'exchange_token': sec_data.get('exchange_token'), 'type': sec_data.get('type'), 'lot_size': sec_data.get('lot_size'), 'tick_size': sec_data.get('tick_size'), 'expiry_date': sec_data.get('expiry_date'), 'is_active': True, }
                if not existing.display_name:
                    update_fields['display_name'] = sec_data.get('display_name')
                self.update(existing, update_fields)
                updated += 1
            else:
                new_security = Security(**sec_data)
                self.create(new_security)
                inserted += 1

        if active_tickers is not None:
            currently_active = self.db_session.query(Security).filter(Security.is_active == True).all()
            for security in currently_active:
                if security.ticker not in active_tickers:
                    self.update(security, { 'is_active': False })
                    deactivated += 1
                    logger.info(f"Deactivated security {security.ticker} — no longer in universe.")

        logger.info(f"Bulk upsert completed: {inserted} inserted, {updated} updated, {deactivated} deactivated.")
        return { "inserted": inserted, "updated": updated, "deactivated": deactivated }

    def deactivate_missing_options(self, active_tickers: set[str]) -> int:
        """Deactivate OPTION-type securities not present in active_tickers.

        Scoped to type == OPTION only, unlike bulk_upsert's active_tickers deactivation
        (which sweeps every currently-active security) — options contracts roll weekly and
        expired ones must not touch equity/index rows imported by a separate pipeline.
        """
        deactivated = 0
        currently_active = self.get_by_fields({ 'type': SecurityType.OPTION.value, 'is_active': True }, limit=None)
        for security in currently_active:
            if security.ticker not in active_tickers:
                self.update(security, { 'is_active': False })
                deactivated += 1
        logger.info(f"Deactivated {deactivated} expired/delisted option contracts.")
        return deactivated

    def deactivate_expired_options(self, as_of_date: date) -> int:
        """Deactivate OPTION-type securities whose expiry_date has passed.

        Deterministic safety net alongside deactivate_missing_options: that method only
        catches expiry indirectly (a contract disappearing from Kite's daily fetch), so it
        silently stops working if the option-chain import job fails to run for a day or more.
        This one is correct purely from the stored expiry_date, independent of import health.
        """
        deactivated = 0
        currently_active = self.get_by_fields({ 'type': SecurityType.OPTION.value, 'is_active': True }, limit=None)
        for security in currently_active:
            if security.expiry_date and security.expiry_date.date() < as_of_date:
                self.update(security, { 'is_active': False })
                deactivated += 1
        logger.info(f"Deactivated {deactivated} option contracts past their expiry date.")
        return deactivated

    def bulk_update_metadata(self, securities_metadata: List[Dict[str, Any]]) -> Dict[str, int]:
        """Bulk update user-added metadata for securities."""
        updated = 0

        for meta in securities_metadata:
            ticker = meta.get('ticker')
            exchange = meta.get('exchange')

            if not ticker or not exchange:
                logger.warning(f"Skipping metadata update with missing ticker or exchange: {meta}")
                continue

            existing = self.get_by_ticker_exchange(ticker, exchange)

            if existing:
                update_fields = { 'display_name': meta.get('display_name') or existing.display_name, 'sector': meta.get('sector') or existing.sector, 'industry': meta.get('industry') or existing.industry }
                self.update(existing, update_fields)
                updated += 1
            else:
                logger.warning(f"No existing security found for ticker {ticker} and exchange {exchange}. Skipping metadata update.")
        logger.info(f"Bulk metadata update completed: {updated} updated.")
        return { "updated": updated }
