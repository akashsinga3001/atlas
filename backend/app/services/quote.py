# backend/app/services/quote.py

from typing import Optional

from sqlalchemy.orm import Session

from app.models.security import Security
from app.services.brokers.kite import KiteService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class QuoteService:

    def __init__(self, db: Session, kite_service: KiteService = None):
        """Initialise with a DB session and a Kite client (creates a new one if not provided)."""
        self.db = db
        self.kite_service = kite_service or KiteService()

    def resolve_instruments(self, tickers: list[str]) -> dict[str, str]:
        """Look up exchange for each ticker in DB and return a {kite_instrument: ticker} map."""
        securities = (self.db.query(Security.ticker, Security.exchange).filter(Security.ticker.in_(tickers)).all())
        return { f"{row.exchange}:{row.ticker}": row.ticker for row in securities }

    def get_last_price(self, ticker: str, exchange: str) -> Optional[float]:
        """Fetch the current last traded price for a single ticker on a given exchange."""
        instrument = f"{exchange}:{ticker}"
        quote = self.kite_service.get_quotes([instrument])
        data = quote.get(instrument)
        return data.get("last_price") if data else None

    def fetch_quotes(self, instrument_map: dict[str, str]) -> dict[str, dict]:
        """Fetch live quotes from Kite and return formatted price data keyed by ticker."""
        raw = self.kite_service.get_quotes(list(instrument_map.keys()))
        result: dict[str, dict] = {}

        for instrument, data in raw.items():
            ticker = instrument_map.get(instrument)
            if not ticker:
                continue
            last_price = data.get("last_price")
            ohlc = data.get("ohlc", {})
            prev_close = ohlc.get("close")
            change_pct = (round((last_price - prev_close) / prev_close * 100, 2) if last_price and prev_close and prev_close != 0 else None)
            result[ticker] = { "last_price": last_price, "change_pct": change_pct, "volume": data.get("volume"), "high": ohlc.get("high"), "low": ohlc.get("low"), }

        return result
