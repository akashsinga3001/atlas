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

    def bulk_upsert(self, securities_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Bulk upsert securities data into the database."""
        inserted = 0
        updated = 0

        for sec_data in securities_data:
            ticker = sec_data.get('ticker')
            exchange = sec_data.get('exchange')

            if not ticker or not exchange:
                logger.warning(f"Skipping security with missing ticker or exchange: {sec_data}")
                continue

            existing = self.get_by_ticker_exchange(ticker, exchange)

            if existing:
                # Update existing record
                update_fields = { 'broker_token': sec_data.get('broker_token'), 'exchange_token': sec_data.get('exchange_token'), 'type': sec_data.get('type'), 'lot_size': sec_data.get('lot_size'), 'tick_size': sec_data.get('tick_size'), 'strike_price': sec_data.get('strike_price'), 'expiry_date': sec_data.get('expiry_date'), 'is_active': sec_data.get('is_active', True) }

                # Only update if not user-added metadata
                if not existing.display_name:
                    update_fields['display_name'] = sec_data.get('display_name')

                self.update(existing, update_fields)
                updated += 1
            else:
                new_security = Security(**sec_data)
                self.create(new_security)
                inserted += 1
        logger.info(f"Bulk upsert completed: {inserted} inserted, {updated} updated.")
        return { "inserted": inserted, "updated": updated }
