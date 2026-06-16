# backend/app/utils/timeframe.py

from datetime import datetime
from app.enums.ohlcv import OHLCVTimeFrame, OHLCVDataSource

KITE_TIMEFRAME_MAP = {OHLCVTimeFrame.ONE_MINUTE: "minute", OHLCVTimeFrame.FIVE_MINUTES: "5minute", OHLCVTimeFrame.FIFTEEN_MINUTES: "15minute", OHLCVTimeFrame.THIRTY_MINUTES: "30minute", OHLCVTimeFrame.ONE_HOUR: "60minute", OHLCVTimeFrame.ONE_DAY: "day"}
YF_TIMEFRAME_MAP = {OHLCVTimeFrame.ONE_MINUTE: "1m", OHLCVTimeFrame.FIVE_MINUTES: "5m", OHLCVTimeFrame.FIFTEEN_MINUTES: "15m", OHLCVTimeFrame.THIRTY_MINUTES: "30m", OHLCVTimeFrame.ONE_HOUR: "60m", OHLCVTimeFrame.ONE_DAY: "1d"}


def get_provider_timeframe(timeframe: OHLCVTimeFrame, source: OHLCVDataSource) -> str:
    """Get the corresponding timeframe string for the specified data source."""
    mappings = {OHLCVDataSource.YAHOO_FINANCE: YF_TIMEFRAME_MAP, OHLCVDataSource.KITE: KITE_TIMEFRAME_MAP}
    return mappings.get(source, {}).get(timeframe)


def is_market_day():
    return datetime.now().weekday < 5  # Monday to Friday are market days


def is_market_hours():
    now = datetime.now().time()
    return (now >= datetime.strptime("09:15", "%H:%M").time() and now <= datetime.strptime("15:30", "%H:%M").time())
