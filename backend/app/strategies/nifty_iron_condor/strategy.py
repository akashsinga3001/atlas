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

# Below this many raw daily closes, a trailing realized-vol/momentum read isn't trustworthy —
# mirrors the research repo's no-lookahead, growing-history convention.
MIN_HISTORY_DAYS = 120

TAIL_EVENT_LOOKBACK_DAYS = 10  # ~2 trading weeks — the spec's "fades within roughly two weeks" window
TAIL_EVENT_RETURN_THRESHOLD = -0.03
MOMENTUM_LOOKBACK_DAYS = 20
VOL_EXPANSION_LOOKBACK_DAYS = 20
VOL_EXPANSION_COMPARISON_LAG = 5


def compute_vix_percentile(history_closes: list[float], current_value: float, lookback_days: int) -> Optional[float]:
    """Percentile rank (0-100) of current_value within its own trailing lookback_days of history plus itself.

    No lookahead: history_closes must already exclude current_value (it's the prior trading
    days only), and current_value is the live reading being ranked against them. Returns
    None below lookback_days of history — too little to trust a percentile against.
    """
    if len(history_closes) < lookback_days:
        return None

    window = history_closes[-lookback_days:] + [current_value]
    rank = sum(1 for v in window if v <= current_value)
    return rank / len(window) * 100.0


def compute_risk_flags(nifty_closes: list[float], vix_closes: list[float], vix_percentile: Optional[float]) -> dict:
    """Lightweight, informational-only monitoring flags for known weak regimes (never gates entry —
    surfaced for whoever monitors the strategy, per spec). All None when there isn't enough history yet.

    - worst_regime: negative 20-day underlying momentum combined with VIX percentile >= 67th —
      historically the worst regime for this strategy.
    - vol_expansion: realized vol and VIX both rising over a short trailing window together —
      a known weak state.
    - tail_event_recent: a >=3% single-day NIFTY down move within the last ~10 trading days —
      elevated risk that fades within roughly two weeks.
    """
    flags: dict = {"momentum_20d_negative": None, "worst_regime": None, "vol_expansion": None, "tail_event_recent": None}

    if len(nifty_closes) > MOMENTUM_LOOKBACK_DAYS:
        momentum_20d = (nifty_closes[-1] - nifty_closes[-1 - MOMENTUM_LOOKBACK_DAYS]) / nifty_closes[-1 - MOMENTUM_LOOKBACK_DAYS]
        flags["momentum_20d_negative"] = momentum_20d < 0
        flags["worst_regime"] = bool(momentum_20d < 0 and vix_percentile is not None and vix_percentile >= 67)

    if len(nifty_closes) >= VOL_EXPANSION_LOOKBACK_DAYS + VOL_EXPANSION_COMPARISON_LAG + 1 and len(vix_closes) > VOL_EXPANSION_COMPARISON_LAG:
        log_returns = np.diff(np.log(nifty_closes))
        vol_series = pd.Series(log_returns).rolling(VOL_EXPANSION_LOOKBACK_DAYS).std().dropna()
        if len(vol_series) > VOL_EXPANSION_COMPARISON_LAG:
            realized_vol_rising = vol_series.iloc[-1] > vol_series.iloc[-1 - VOL_EXPANSION_COMPARISON_LAG]
            vix_rising = vix_closes[-1] > vix_closes[-1 - VOL_EXPANSION_COMPARISON_LAG]
            flags["vol_expansion"] = bool(realized_vol_rising and vix_rising)

    if len(nifty_closes) > TAIL_EVENT_LOOKBACK_DAYS:
        recent = nifty_closes[-(TAIL_EVENT_LOOKBACK_DAYS + 1):]
        recent_returns = [recent[i] / recent[i - 1] - 1 for i in range(1, len(recent))]
        flags["tail_event_recent"] = any(r <= TAIL_EVENT_RETURN_THRESHOLD for r in recent_returns)

    return flags


class NiftyIronCondorSignalStrategy(Strategy):
    """Daily signal for the delta-targeted NIFTY iron condor: records that day's spot close,
    India VIX percentile (and whether it passes the entry gate), and monitoring-only risk flags.

    Unconditional — a signal fires every NSE trading day regardless of whether the VIX gate
    passes or a position is already open, so there's a full audit trail of the gate's daily
    state. The execution engine (OptionsTradeService) is what actually decides whether to act
    on a given day's signal: it checks vix_gate_pass and whether a position is already open.
    """
    code = "nifty_iron_condor"
    name = "NIFTY Iron Condor"

    def execute(self, context: StrategyContext) -> list[Observation]:
        as_of_date = context.as_of_date.date()
        config = context.config

        if not is_nse_trading_day(as_of_date):
            logger.debug(f"{as_of_date} is not an NSE trading day — no signal.")
            return []

        underlying_ticker = config.get("underlying_ticker", "NIFTY 50")
        vix_ticker = config.get("vix_ticker", "INDIA VIX")

        security = context.feature_service.get_security_by_ticker(underlying_ticker, "NSE")
        if not security:
            logger.error(f"Underlying security '{underlying_ticker}' not found in securities table — cannot generate signal.")
            return []

        vix_security = context.feature_service.get_security_by_ticker(vix_ticker, "NSE")
        if not vix_security:
            logger.error(f"VIX security '{vix_ticker}' not found in securities table — cannot generate signal.")
            return []

        try:
            quote_service = context.quote_service_factory()
            spot_close = quote_service.get_last_price(underlying_ticker, "NSE")
            vix_value = quote_service.get_last_price(vix_ticker, "NSE")
        except Exception:
            logger.error(f"Failed to fetch live quotes for {underlying_ticker}/{vix_ticker} — no signal.", exc_info=True)
            return []

        if not spot_close or spot_close <= 0:
            logger.error(f"No live price returned for {underlying_ticker} — no signal.")
            return []
        if not vix_value or vix_value <= 0:
            logger.error(f"No live price returned for {vix_ticker} — no signal.")
            return []

        nifty_closes = context.feature_service.get_recent_closes(security.id, as_of_date=as_of_date)
        vix_closes = context.feature_service.get_recent_closes(vix_security.id, as_of_date=as_of_date)

        lookback = config.get("vix_percentile_lookback_days", 252)
        vix_percentile = compute_vix_percentile(vix_closes, vix_value, lookback)

        avoid_low = config.get("vix_avoid_band_low", 33)
        avoid_high = config.get("vix_avoid_band_high", 67)
        # Insufficient history to compute a percentile is treated as a gate failure, not a
        # pass — never trade the VIX gate blind just because there isn't enough data yet.
        vix_gate_pass = vix_percentile is not None and not (avoid_low < vix_percentile < avoid_high)

        risk_flags = compute_risk_flags(nifty_closes, vix_closes, vix_percentile)

        logger.info(f"NIFTY iron condor signal for {as_of_date}: spot_close={spot_close}, vix_value={vix_value}, "
                    f"vix_percentile={vix_percentile}, vix_gate_pass={vix_gate_pass}, risk_flags={risk_flags}")

        payload = {
            "spot_close": spot_close, "vix_value": vix_value, "vix_percentile": vix_percentile,
            "vix_gate_pass": vix_gate_pass, "strategy": self.code, **risk_flags,
        }
        return [Observation(security_id=security.id, observed_at=datetime.combine(as_of_date, datetime.min.time()), payload=payload)]
