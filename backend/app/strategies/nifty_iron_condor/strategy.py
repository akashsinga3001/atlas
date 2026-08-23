# backend/app/strategies/nifty_iron_condor/strategy.py

from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from app.strategies.base import Strategy
from app.strategies.context import StrategyContext
from app.strategies.observation import Observation
from app.utils.trading_calendar import is_nse_trading_day
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Below this many raw daily closes, neither the realized-vol estimate nor its expanding
# median is trustworthy — mirrors the research repo's no-lookahead, growing-history convention.
MIN_HISTORY_DAYS = 120


def compute_vol_regime(closes: list[float], lookback_days: int) -> tuple[Optional[float], Optional[float], Optional[str]]:
    """Classify the current realized-vol regime from an ascending list of daily closes.

    realized_vol is the stdev of trailing `lookback_days` daily log returns; the regime is
    "elevated" if that exceeds the expanding-window median of the same vol series computed
    over all available history (no lookahead), "calm" otherwise. Returns all-None below
    MIN_HISTORY_DAYS of closes — too little history to trust either figure.
    """
    if len(closes) < MIN_HISTORY_DAYS:
        return None, None, None

    log_returns = np.diff(np.log(closes))
    vol_series = pd.Series(log_returns).rolling(lookback_days).std().dropna()
    if vol_series.empty:
        return None, None, None

    realized_vol = float(vol_series.iloc[-1])
    median = float(vol_series.expanding().median().iloc[-1])
    regime = "elevated" if realized_vol > median else "calm"
    return realized_vol, median, regime


class NiftyIronCondorSignalStrategy(Strategy):
    """Monday signal for the NIFTY iron condor: records that day's NIFTY 50 close as spot_close.

    No conditional logic — the strategy is unconditional by design (every NSE-trading Monday
    is a signal). Actual order entry happens the next NSE trading day; see OptionsTradeService.
    """
    code = "nifty_iron_condor"
    name = "NIFTY Iron Condor"

    def execute(self, context: StrategyContext) -> list[Observation]:
        as_of_date = context.as_of_date.date()
        config = context.config

        signal_weekday = config.get("signal_day_of_week", 0)
        if as_of_date.weekday() != signal_weekday or not is_nse_trading_day(as_of_date):
            logger.debug(f"{as_of_date} is not a signal day for {self.code} (weekday={as_of_date.weekday()}) — no signal.")
            return []

        underlying_ticker = config.get("underlying_ticker", "NIFTY 50")
        security = context.feature_service.get_security_by_ticker(underlying_ticker, "NSE")

        if not security:
            logger.error(f"Underlying security '{underlying_ticker}' not found in securities table — cannot generate signal.")
            return []

        try:
            spot_close = context.quote_service_factory().get_last_price(underlying_ticker, "NSE")
        except Exception:
            logger.error(f"Failed to fetch spot quote for {underlying_ticker} — no signal.", exc_info=True)
            return []

        if not spot_close or spot_close <= 0:
            logger.error(f"No live price returned for {underlying_ticker} — no signal.")
            return []

        closes = context.feature_service.get_recent_closes(security.id, as_of_date=as_of_date)
        realized_vol, vol_median, vol_regime = compute_vol_regime(closes, config.get("vol_regime_lookback_days", 60))

        logger.info(f"NIFTY iron condor signal for {as_of_date}: spot_close={spot_close}, "
                    f"realized_vol={realized_vol}, vol_median={vol_median}, vol_regime={vol_regime}")

        return [Observation(security_id=security.id, observed_at=datetime.combine(as_of_date, datetime.min.time()), payload={ "spot_close": spot_close, "vol_regime": vol_regime, "strategy": self.code })]
