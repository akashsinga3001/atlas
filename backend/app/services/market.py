# backend/app/services/market.py

from sqlalchemy.orm import Session

from app.models.features import MarketFeature
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MarketService:
    """Service for reading market sentiment and breadth data."""

    def __init__(self, db: Session):
        self.db = db

    def get_sentiment(self, timeframe: str = "1d") -> dict:
        """Return the latest market sentiment snapshot."""
        latest = (self.db.query(MarketFeature).filter(MarketFeature.timeframe == timeframe).order_by(MarketFeature.candle_timestamp.desc()).first())
        if not latest:
            return {}

        return self._build_sentiment(latest)

    def get_sentiment_history(self, timeframe: str = "1d", limit: int = 60) -> list[dict]:
        """Return recent market sentiment snapshots, oldest to newest, for trend sparklines."""
        rows = (self.db.query(MarketFeature).filter(MarketFeature.timeframe == timeframe).order_by(MarketFeature.candle_timestamp.desc()).limit(limit).all())
        return [self._build_sentiment(row) for row in reversed(rows)]

    def _build_sentiment(self, row: MarketFeature) -> dict:
        """Convert a MarketFeature row into a plain dict with a Fear & Greed style label."""
        score = float(row.regime_score) if row.regime_score is not None else None

        return {
            "candle_timestamp": row.candle_timestamp,
            "regime_score": round(score, 2) if score is not None else None,
            "label": self._label_for_score(score),
            "advance_decline_ratio": round(float(row.advance_decline_ratio), 2) if row.advance_decline_ratio is not None else None,
            "market_breadth_ema20": round(float(row.market_breadth_ema20), 2) if row.market_breadth_ema20 is not None else None,
            "market_breadth_ema50": round(float(row.market_breadth_ema50), 2) if row.market_breadth_ema50 is not None else None,
            "pct_above_ema20": round(float(row.pct_above_ema20), 2) if row.pct_above_ema20 is not None else None,
            "pct_above_ema50": round(float(row.pct_above_ema50), 2) if row.pct_above_ema50 is not None else None,
            "pct_above_ema200": round(float(row.pct_above_ema200), 2) if row.pct_above_ema200 is not None else None,
            "new_highs_count": row.new_highs_count,
            "new_lows_count": row.new_lows_count,
        }

    @staticmethod
    def _label_for_score(score: float | None) -> str | None:
        """Map a 0-100 regime score to a Fear & Greed style label."""
        if score is None:
            return None
        if score < 20:
            return "Extreme Fear"
        if score < 40:
            return "Fear"
        if score < 60:
            return "Neutral"
        if score < 80:
            return "Greed"
        return "Extreme Greed"
