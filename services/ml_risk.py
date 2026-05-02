"""Position sizing, stop-loss, and take-profit rules for ML-driven trade simulation."""

from dataclasses import dataclass
from typing import Any


@dataclass
class RiskParameters:
    """Immutable risk configuration for one backtest or live run."""

    portfolio_value: float          # Starting (or current) portfolio value in INR
    max_position_pct: float         # Maximum % of portfolio in a single position (e.g. 0.05 = 5 %)
    max_open_positions: int         # Hard cap on simultaneous open positions
    stop_loss_pct: float            # Fixed stop-loss below entry (e.g. 0.03 = 3 %)
    take_profit_pct: float          # Fixed take-profit above entry (e.g. 0.08 = 8 %)
    min_confidence: float           # Minimum model confidence to enter a trade (e.g. 0.60)
    commission_pct: float           # Round-trip commission as fraction of trade value (e.g. 0.001)


@dataclass
class SizedPosition:
    """Output of the position-sizer for one candidate signal."""

    security_id: int
    ticker: str
    direction: str          # 'long' or 'short'
    confidence: float
    entry_price: float
    stop_loss_price: float
    take_profit_price: float
    position_size_inr: float    # Capital allocated to this trade
    shares: int                 # Whole number of shares (floor division)
    accepted: bool              # False when confidence or capital filters reject the signal
    reject_reason: str | None = None


class MlRiskService:
    """Apply risk management rules to model signals before simulated execution."""

    def size_positions(
        self,
        signals: list[dict[str, Any]],
        prices: dict[int, float],
        params: RiskParameters,
        open_position_count: int,
    ) -> list[SizedPosition]:
        """Convert ranked model signals into sized, risk-checked positions.

        Args:
            signals: Ranked prediction dicts from MlModelService.score_direction().
                     Each dict must contain security_id, ticker, direction, confidence.
            prices: Map of security_id → current close price for entry.
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

            capital = min(params.portfolio_value * params.max_position_pct, params.portfolio_value / max(params.max_open_positions, 1))
            shares = int(capital // entry_price)

            if shares <= 0:
                positions.append(self._rejected(security_id, ticker, direction, confidence, entry_price, params, reason='insufficient_capital'))
                continue

            position_size_inr = shares * entry_price

            if direction == 'long':
                stop_loss_price = entry_price * (1.0 - params.stop_loss_pct)
                take_profit_price = entry_price * (1.0 + params.take_profit_pct)
            else:
                stop_loss_price = entry_price * (1.0 + params.stop_loss_pct)
                take_profit_price = entry_price * (1.0 - params.take_profit_pct)

            remaining_slots -= 1
            positions.append(SizedPosition(
                security_id=security_id,
                ticker=ticker,
                direction=direction,
                confidence=confidence,
                entry_price=entry_price,
                stop_loss_price=round(stop_loss_price, 2),
                take_profit_price=round(take_profit_price, 2),
                position_size_inr=round(position_size_inr, 2),
                shares=shares,
                accepted=True,
                reject_reason=None,
            ))

        return positions

    def apply_exit_rules(
        self,
        entry_price: float,
        current_price: float,
        stop_loss_price: float,
        take_profit_price: float,
        direction: str,
        days_held: int,
        horizon_days: int,
    ) -> str | None:
        """Determine if an open position should be exited on this bar.

        Args:
            entry_price: Price at which the position was opened.
            current_price: Current bar's close price.
            stop_loss_price: Absolute stop-loss level.
            take_profit_price: Absolute take-profit level.
            direction: 'long' or 'short'.
            days_held: Number of trading days the position has been open.
            horizon_days: Maximum hold period from the model's prediction horizon.

        Returns:
            Exit reason string ('stop_loss', 'take_profit', 'horizon_exit') or None if holding.
        """
        if direction == 'long':
            if current_price <= stop_loss_price:
                return 'stop_loss'
            if current_price >= take_profit_price:
                return 'take_profit'
        else:
            if current_price >= stop_loss_price:
                return 'stop_loss'
            if current_price <= take_profit_price:
                return 'take_profit'

        if days_held >= horizon_days:
            return 'horizon_exit'

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
            params: Risk parameters for stop/take-profit calculation.

        Returns:
            SizedPosition with accepted=False and zero share count.
        """
        stop = entry_price * (1.0 - params.stop_loss_pct) if direction == 'long' else entry_price * (1.0 + params.stop_loss_pct)
        tp = entry_price * (1.0 + params.take_profit_pct) if direction == 'long' else entry_price * (1.0 - params.take_profit_pct)
        return SizedPosition(
            security_id=security_id,
            ticker=ticker,
            direction=direction,
            confidence=confidence,
            entry_price=entry_price,
            stop_loss_price=round(stop, 2),
            take_profit_price=round(tp, 2),
            position_size_inr=0.0,
            shares=0,
            accepted=False,
            reject_reason=reason,
        )
