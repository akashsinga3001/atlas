# backend/app/api/v1/quotes.py

import asyncio
import json
from typing import AsyncGenerator
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.security import Security
from app.services.brokers.kite import KiteService
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

_STREAM_INTERVAL = 5  # seconds between Kite polls


def _resolve_kite_instruments(tickers: list[str], db: Session) -> dict[str, str]:
    """Returns {kite_instrument: ticker} for each ticker found in DB."""
    securities = db.query(Security.ticker, Security.exchange).filter(Security.ticker.in_(tickers)).all()
    return { f"{row.exchange}:{row.ticker}": row.ticker for row in securities }


async def _quote_generator(tickers: list[str]) -> AsyncGenerator[str, None]:
    db = SessionLocal()
    try:
        instrument_map = _resolve_kite_instruments(tickers, db)
        if not instrument_map:
            yield f"data: {json.dumps({'error': 'No matching tickers'})}\n\n"
            return

        kite = KiteService()
        instruments = list(instrument_map.keys())

        while True:
            try:
                raw = kite.get_quotes(instruments)
                payload: dict[str, dict] = {}
                for instrument, data in raw.items():
                    ticker = instrument_map.get(instrument)
                    if not ticker:
                        continue
                    last_price = data.get("last_price")
                    ohlc = data.get("ohlc", {})
                    prev_close = ohlc.get("close")
                    change_pct = (round((last_price - prev_close) / prev_close * 100, 2) if last_price and prev_close and prev_close != 0 else None)
                    payload[ticker] = { "last_price": last_price, "change_pct": change_pct, "volume": data.get("volume"), "high": ohlc.get("high"), "low": ohlc.get("low"), }
                yield f"data: {json.dumps(payload)}\n\n"
            except Exception as exc:
                logger.warning("SSE quote fetch error: {}", exc)
                yield f"data: {json.dumps({'error': str(exc)})}\n\n"

            await asyncio.sleep(_STREAM_INTERVAL)
    finally:
        db.close()


@router.get("/stream")
async def quotes_stream(tickers: str = Query(..., description="Comma-separated ticker list")):
    ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
    if not ticker_list:
        return { "error": "No tickers provided"}

    return StreamingResponse(_quote_generator(ticker_list), media_type="text/event-stream", headers={ "Cache-Control": "no-cache", "X-Accel-Buffering": "no", }, )
