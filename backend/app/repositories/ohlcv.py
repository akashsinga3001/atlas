# backend/app/repositories/ohlcv.py

from typing import Optional, List, Dict, Any, Set
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import asc, func
from sqlalchemy.dialects.postgresql import insert

from app.repositories.base import BaseRepository
from app.models.ohlcv import OHLCV
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OHLCVRepository(BaseRepository):
    """Repository class for managing OHLCV data in the database."""

    def __init__(self, db: Session):
        self.db = db
        super().__init__(OHLCV, db)

    def bulk_upsert(self, records: list[dict]) -> int:
        """Bulk upsert OHLCV records into DB"""
        if not records:
            return 0

        try:
            stmt = insert(OHLCV).values(records)
            stmt = stmt.on_conflict_do_update(constraint="uix_security_timestamp_timeframe", set_={ "open": stmt.excluded.open, "high": stmt.excluded.high, "low": stmt.excluded.low, "close": stmt.excluded.close, "volume": stmt.excluded.volume })
            result = self.db.execute(stmt)
            logger.info(f"Bulk upserted {len(records):,} OHLCV records.")

            return result.rowcount or len(records)
        except Exception as exc:
            logger.error(f"Failed to bulk upsert OHLCV records. {exc}", exc_info=True)
            self.db.rollback()
            return 0

    def get_latest_candle_timestamp(self, security_id: int, timeframe: str) -> Optional[datetime]:
        """Get the latest candle timestamp for a given security and timeframe."""
        return self.db.query(func.max(OHLCV.candle_timestamp)).filter(OHLCV.security_id == security_id, OHLCV.timeframe == timeframe).scalar()

    def get_by_security_and_timeframe(self, security_id: int, timeframe: str = '1d', start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, limit: Optional[int] = None) -> List[OHLCV]:
        """Fetch OHLCV data for a specific security and timeframe, with optional date range and limit."""
        query = self.db.query(OHLCV).filter(OHLCV.security_id == security_id, OHLCV.timeframe == timeframe)

        if start_date:
            query = query.filter(OHLCV.candle_timestamp >= start_date)
        if end_date:
            query = query.filter(OHLCV.candle_timestamp <= end_date)

        query = query.order_by(asc(OHLCV.candle_timestamp))

        if limit:
            query = query.limit(limit)

        return query.all()
