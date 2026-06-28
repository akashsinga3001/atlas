# backend/app/api/v1/quotes.py

import asyncio
import json
from typing import AsyncGenerator
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.core.database import SessionLocal
from app.services.quote import QuoteService
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

_STREAM_INTERVAL = 5  # seconds between Kite polls


async def _quote_generator(tickers: list[str]) -> AsyncGenerator[str, None]:
    """Resolve instruments once, then stream live quote payloads every _STREAM_INTERVAL seconds."""
    db = SessionLocal()
    try:
        service = QuoteService(db)
        instrument_map = service.resolve_instruments(tickers)

        if not instrument_map:
            yield f"data: {json.dumps({'error': 'No matching tickers'})}\n\n"
            return

        while True:
            try:
                payload = service.fetch_quotes(instrument_map)
                yield f"data: {json.dumps(payload)}\n\n"
            except Exception as exc:
                logger.warning("SSE quote fetch error: {}", exc)
                yield f"data: {json.dumps({'error': str(exc)})}\n\n"

            await asyncio.sleep(_STREAM_INTERVAL)
    finally:
        db.close()


@router.get("/stream")
async def quotes_stream(tickers: str = Query(..., description="Comma-separated ticker list")):
    """Open an SSE stream delivering live quotes for the requested tickers."""
    ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
    if not ticker_list:
        return { "error": "No tickers provided"}

    return StreamingResponse(_quote_generator(ticker_list), media_type="text/event-stream", headers={ "Cache-Control": "no-cache", "X-Accel-Buffering": "no"}, )
