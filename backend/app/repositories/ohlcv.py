# backend/app/repositories/ohlcv.py

from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import asc, func
from sqlalchemy.dialects.postgresql import insert

from app.repositories.base import BaseRepository
from app.models.ohlcv import OHLCV
from app.models.security import Security
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OHLCVRepository(BaseRepository):
    """Repository class for managing OHLCV data in the database."""

    def __init__(self, db: Session):
        super().__init__(OHLCV, db)

    def bulk_upsert(self, records: list[dict]) -> int:
        """Bulk upsert OHLCV records into DB"""
        if not records:
            return 0

        try:
            stmt = insert(OHLCV).values(records)
            stmt = stmt.on_conflict_do_update(constraint="uix_security_timestamp_timeframe", set_={ "open": stmt.excluded.open, "high": stmt.excluded.high, "low": stmt.excluded.low, "close": stmt.excluded.close, "volume": stmt.excluded.volume })
            result = self.db_session.execute(stmt)
            logger.info(f"Bulk upserted {len(records):,} OHLCV records.")

            return result.rowcount or len(records)
        except Exception as exc:
            logger.error(f"Failed to bulk upsert OHLCV records. {exc}", exc_info=True)
            self.db_session.rollback()
            return 0

    def get_by_timeframe(self, timeframe: str) -> List[OHLCV]:
        """Fetch OHLCV data for a specific timeframe."""
        return self.db_session.query(OHLCV).filter(OHLCV.timeframe == timeframe).order_by(asc(OHLCV.candle_timestamp)).all()

    def get_by_tickers_and_timeframe(self, tickers: list[str], timeframe: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[OHLCV]:
        """Fetch OHLCV data for specific tickers and timeframe, with optional date range."""
        query = self.db_session.query(OHLCV).join(Security, Security.id == OHLCV.security_id).options(joinedload(OHLCV.security)).filter(Security.ticker.in_(tickers), OHLCV.timeframe == timeframe)

        if start_date:
            query = query.filter(OHLCV.candle_timestamp >= start_date)
        if end_date:
            query = query.filter(OHLCV.candle_timestamp <= end_date)

        return (query.order_by(OHLCV.security_id, OHLCV.candle_timestamp).all())

    def get_recent_by_tickers_and_timeframe(self, tickers: list[str], timeframe: str, limit_per_ticker: int) -> List[OHLCV]:
        """Fetch only the most recent `limit_per_ticker` rows per ticker for the given
        timeframe, bounded at the SQL level via a window function — so a large tickers
        list never pulls each security's full history into memory just to be trimmed
        down in Python afterward (see feature_generation memory-kill fix)."""
        ranked = (self.db_session.query(OHLCV.id, func.row_number().over(partition_by=OHLCV.security_id, order_by=OHLCV.candle_timestamp.desc()).label("rn")).join(Security, Security.id == OHLCV.security_id).filter(Security.ticker.in_(tickers), OHLCV.timeframe == timeframe).subquery())

        return (self.db_session.query(OHLCV).join(ranked, OHLCV.id == ranked.c.id).filter(ranked.c.rn <= limit_per_ticker).options(joinedload(OHLCV.security)).order_by(OHLCV.security_id, OHLCV.candle_timestamp).all())

    def get_latest_candle_timestamp(self, security_id: int, timeframe: str) -> Optional[datetime]:
        """Get the latest candle timestamp for a given security and timeframe."""
        return self.db_session.query(func.max(OHLCV.candle_timestamp)).filter(OHLCV.security_id == security_id, OHLCV.timeframe == timeframe).scalar()

    def get_by_security_and_timeframe(self, security_id: int, timeframe: str = '1d', start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, limit: Optional[int] = None) -> List[OHLCV]:
        """Fetch OHLCV data for a specific security and timeframe, with optional date range and limit."""
        query = self.db_session.query(OHLCV).filter(OHLCV.security_id == security_id, OHLCV.timeframe == timeframe)

        if start_date:
            query = query.filter(OHLCV.candle_timestamp >= start_date)
        if end_date:
            query = query.filter(OHLCV.candle_timestamp <= end_date)

        query = query.order_by(asc(OHLCV.candle_timestamp))

        if limit:
            query = query.limit(limit)

        return query.all()
