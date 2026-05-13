"""Position sizing, trailing stop, and exit rules for ML-driven trade simulation."""

from dataclasses import dataclass
from typing import Any


@dataclass
class RiskParameters:
    """Immutable risk configuration for one backtest or live run."""

    portfolio_value: float          # Starting (or current) portfolio value in INR
    max_open_positions: int         # Hard cap on simultaneous open positions
    trailing_stop_pct: float        # Trailing stop distance below high-water mark (e.g. 0.03 = 3 %)
    min_confidence: float           # Minimum model confidence to enter a trade (e.g. 0.60)
    commission_pct: float           # Round-trip commission as fraction of trade value (e.g. 0.001)
    min_cash_reserve: float = 30_000.0   # Cash that must remain available after opening positions


@dataclass
class SizedPosition:
    """Output of the position-sizer for one candidate signal."""

    security_id: int
    ticker: str
    direction: str              # 'long' or 'short'
    confidence: float
    entry_price: float
    trailing_stop_price: float  # Initial trailing stop level (trails upward as price rises)
    position_size_inr: float    # Capital allocated to this trade (lots × entry_price)
    lots: int                   # Number of futures lots
    accepted: bool              # False when confidence or capital filters reject the signal
    reject_reason: str | None = None


class MlRiskService:
    """Apply risk management rules to model signals before simulated execution."""

    def size_positions(
        self,
        signals: list[dict[str, Any]],
        prices: dict[int, float],
        lot_sizes: dict[int, int],
        params: RiskParameters,
        open_position_count: int,
    ) -> list[SizedPosition]:
        """Convert ranked model signals into lot-sized, risk-checked positions.

        Args:
            signals: Ranked prediction dicts from MlModelService.score_direction().
                     Each dict must contain security_id, ticker, direction, confidence.
            prices: Map of security_id → current close price for entry.
            lot_sizes: Map of security_id → futures lot size (from securities table).
            params: Risk configuration for this run.
            open_position_count: Number of already-open positions to respect the cap.

        Returns:
            List of SizedPosition objects. Check .accepted to filter tradeable entries.
        """
        positions: list[SizedPosition] = []
        remaining_slots = params.max_open_positions - open_position_count

        for signal in signals:
            security_id = int(signal['security_id'])
            ticker = str(signal['ticker'])
            direction = str(signal['direction'])
            confidence = float(signal['confidence'])
            entry_price = prices.get(security_id, 0.0)

            if entry_price <= 0:
                positions.append(self._rejected(security_id, ticker, direction, confidence, entry_price, params, reason='no_price'))
                continue

            if confidence < params.min_confidence:
                positions.append(self._rejected(security_id, ticker, direction, confidence, entry_price, params, reason='low_confidence'))
                continue

            if remaining_slots <= 0:
                positions.append(self._rejected(security_id, ticker, direction, confidence, entry_price, params, reason='capacity'))
                continue

            lots = lot_sizes.get(security_id, 1)
            position_size_inr = lots * entry_price

            if position_size_inr > params.portfolio_value:
                positions.append(self._rejected(security_id, ticker, direction, confidence, entry_price, params, reason='insufficient_capital'))
                continue

            if params.portfolio_value - position_size_inr < params.min_cash_reserve:
                positions.append(self._rejected(security_id, ticker, direction, confidence, entry_price, params, reason='insufficient_capital'))
                continue

            trailing_stop_price = entry_price * (1.0 - params.trailing_stop_pct)

            remaining_slots -= 1
            positions.append(SizedPosition(
                security_id=security_id,
                ticker=ticker,
                direction=direction,
                confidence=confidence,
                entry_price=entry_price,
                trailing_stop_price=round(trailing_stop_price, 2),
                position_size_inr=round(position_size_inr, 2),
                lots=lots,
                accepted=True,
                reject_reason=None,
            ))

        return positions

    def update_trailing_stop(
        self,
        current_stop: float,
        day_high: float,
        trailing_stop_pct: float,
    ) -> float:
        """Ratchet the trailing stop upward based on the day's high-water mark.

        The stop only moves up, never down. Call this before checking exit rules.

        Args:
            current_stop: Current absolute trailing stop price.
            day_high: The high price of the current bar.
            trailing_stop_pct: Trailing distance as a fraction (e.g. 0.03 = 3 %).

        Returns:
            Updated trailing stop price (always >= current_stop).
        """
        candidate = day_high * (1.0 - trailing_stop_pct)
        return max(current_stop, round(candidate, 2))

    def apply_exit_rules(
        self,
        direction: str,
        day_open: float,
        day_low: float,
        day_close: float,
        trailing_stop_price: float,
        days_held: int,
        horizon_days: int,
    ) -> tuple[str, float] | None:
        """Determine if an open position should be exited on this bar.

        Checks are applied in priority order:
        1. Gap-down open below trailing stop (emergency exit at open price).
        2. Intraday low touches trailing stop (exit at stop price).
        3. Maximum holding period reached (exit at close).

        Args:
            direction: 'long' or 'short'.
            day_open: Opening price of the current bar.
            day_low: Low price of the current bar.
            day_close: Closing price of the current bar.
            trailing_stop_price: Current absolute trailing stop level.
            days_held: Number of trading days the position has been open.
            horizon_days: Maximum hold period.

        Returns:
            Tuple of (exit_reason, exit_price) or None if the position should be held.
        """
        if direction == 'long':
            if day_open <= trailing_stop_price:
                return ('stop_loss_gap', day_open)
            if day_low <= trailing_stop_price:
                return ('trailing_stop', trailing_stop_price)
        # short side uses inverted logic (stop above entry) — placeholder for future use
        else:
            if day_open >= trailing_stop_price:
                return ('stop_loss_gap', day_open)
            if day_low >= trailing_stop_price:
                return ('trailing_stop', trailing_stop_price)

        if days_held >= horizon_days:
            return ('horizon_exit', day_close)

        return None

    def compute_realized_pnl_pct(
        self,
        entry_price: float,
        exit_price: float,
        direction: str,
        commission_pct: float,
    ) -> float:
        """Compute net realized P&L percentage after round-trip commission.

        Args:
            entry_price: Trade entry price.
            exit_price: Trade exit price.
            direction: 'long' or 'short'.
            commission_pct: Fractional round-trip commission (e.g. 0.001 = 0.1 %).

        Returns:
            Net P&L as a percentage of entry price.
        """
        if entry_price <= 0:
            return 0.0

        if direction == 'long':
            gross_pnl_pct = (exit_price - entry_price) / entry_price
        else:
            gross_pnl_pct = (entry_price - exit_price) / entry_price

        return (gross_pnl_pct - commission_pct) * 100.0

    def _rejected(
        self,
        security_id: int,
        ticker: str,
        direction: str,
        confidence: float,
        entry_price: float,
        params: RiskParameters,
        reason: str,
    ) -> SizedPosition:
        """Build a rejected SizedPosition placeholder.

        Args:
            security_id: Security identifier.
            ticker: Ticker symbol.
            direction: 'long' or 'short'.
            confidence: Model confidence score.
            entry_price: Entry price (may be 0 if unknown).
            params: Risk parameters for trailing stop calculation.

        Returns:
            SizedPosition with accepted=False and zero lots.
        """
        stop = entry_price * (1.0 - params.trailing_stop_pct) if direction == 'long' else entry_price * (1.0 + params.trailing_stop_pct)
        return SizedPosition(
            security_id=security_id,
            ticker=ticker,
            direction=direction,
            confidence=confidence,
            entry_price=entry_price,
            trailing_stop_price=round(stop, 2),
            position_size_inr=0.0,
            lots=0,
            accepted=False,
            reject_reason=reason,
        )
