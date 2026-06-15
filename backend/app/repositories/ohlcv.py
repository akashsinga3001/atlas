# backend/app/repositories/ohlcv.py

from typing import Optional, List, Dict, Any, Set
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, asc

from app.repositories.base import BaseRepository
from app.models.ohlcv import OHLCV
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OHLCVRepository(BaseRepository):
    """Repository class for managing OHLCV data in the database."""

    def __init__(self, db: Session):
        super().__init__(OHLCV, db)

    def get_by_security_and_timeframe(self, security_id: int, timeframe: str = '1DAY', start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, limit: Optional[int] = None) -> List[OHLCV]:
        """Fetch OHLCV data for a specific security and timeframe, with optional date range and limit."""
        query = self.db.query(OHLCV).filter(OHLCV.security_id == security_id, OHLCV.timeframe == timeframe)

        if start_date:
            query = query.filter(OHLCV.timestamp >= start_date)
        if end_date:
            query = query.filter(OHLCV.timestamp <= end_date)

        query = query.order_by(asc(OHLCV.timestamp))

        if limit:
            query = query.limit(limit)

        return query.all()
