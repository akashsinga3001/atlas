"""Portfolio performance metrics for walk-forward backtest evaluation."""

import math
from typing import Any


class MlMetricsService:
    """Compute portfolio-level performance metrics from a sequence of closed trades."""

    def compute_fold_metrics(
        self,
        closed_trades: list[dict[str, Any]],
        daily_portfolio_values: list[float],
        risk_free_rate_annual: float = 0.065,
    ) -> dict[str, float]:
        """Compute all standard performance metrics for one walk-forward fold.

        Args:
            closed_trades: List of trade dicts, each with keys:
                           realized_pnl_pct (float), direction (str), exit_reason (str).
            daily_portfolio_values: Ordered list of end-of-day portfolio values.
            risk_free_rate_annual: Annual risk-free rate for Sharpe ratio (default 6.5 % NSE T-bill proxy).

        Returns:
            Dict with sharpe_ratio, max_drawdown_pct, win_rate_pct, total_return_pct,
            long_accuracy, short_accuracy, avg_pnl_pct, avg_win_pct, avg_loss_pct,
            profit_factor, total_trades, winning_trades, losing_trades.
        """
        total_return_pct = self._total_return(daily_portfolio_values)
        max_drawdown_pct = self._max_drawdown(daily_portfolio_values)
        sharpe = self._sharpe_ratio(daily_portfolio_values, risk_free_rate_annual)

        longs = [t for t in closed_trades if t['direction'] == 'long']
        shorts = [t for t in closed_trades if t['direction'] == 'short']

        win_rate_pct = self._win_rate(closed_trades)
        long_accuracy = self._win_rate(longs)
        short_accuracy = self._win_rate(shorts)

        pnls = [float(t['realized_pnl_pct']) for t in closed_trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        avg_win_pct = sum(wins) / len(wins) if wins else 0.0
        avg_loss_pct = sum(losses) / len(losses) if losses else 0.0
        avg_pnl_pct = sum(pnls) / len(pnls) if pnls else 0.0

        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

        return {
            'sharpe_ratio': round(sharpe, 4),
            'max_drawdown_pct': round(max_drawdown_pct, 4),
            'total_return_pct': round(total_return_pct, 4),
            'win_rate_pct': round(win_rate_pct, 4),
            'long_accuracy': round(long_accuracy, 4),
            'short_accuracy': round(short_accuracy, 4),
            'avg_pnl_pct': round(avg_pnl_pct, 4),
            'avg_win_pct': round(avg_win_pct, 4),
            'avg_loss_pct': round(avg_loss_pct, 4),
            'profit_factor': round(profit_factor, 4),
            'total_trades': len(closed_trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
        }

    def aggregate_fold_metrics(self, fold_metrics_list: list[dict[str, float]]) -> dict[str, float]:
        """Average per-fold metrics across all walk-forward folds.

        Args:
            fold_metrics_list: List of metric dicts, one per completed fold.

        Returns:
            Dict of averaged metrics plus fold count.
        """
        if not fold_metrics_list:
            return {}

        count_keys = {
            'total_trades',
            'winning_trades',
            'losing_trades',
            'signals_scored',
            'accepted_entries',
            'rejected_no_price',
            'rejected_low_confidence',
            'rejected_capacity',
            'rejected_insufficient_capital',
            'rejected_conflict',
            'days_with_no_candidates',
        }
        keys = fold_metrics_list[0].keys()
        aggregated: dict[str, float] = {}
        for key in keys:
            if key == 'fold_index':
                continue
            values = [float(m[key]) for m in fold_metrics_list if key in m]
            if key in count_keys:
                aggregated[key] = sum(values) if values else 0.0
            else:
                aggregated[key] = sum(values) / len(values) if values else 0.0

        aggregated['fold_count'] = float(len(fold_metrics_list))
        return aggregated

    # ── Private helpers ────────────────────────────────────────────────────────

    def _total_return(self, daily_values: list[float]) -> float:
        """Compute total return percentage from start to end of portfolio value series.

        Args:
            daily_values: Ordered daily portfolio values.

        Returns:
            Total return as a percentage.
        """
        if len(daily_values) < 2 or daily_values[0] <= 0:
            return 0.0
        return ((daily_values[-1] - daily_values[0]) / daily_values[0]) * 100.0

    def _max_drawdown(self, daily_values: list[float]) -> float:
        """Compute maximum peak-to-trough drawdown percentage.

        Args:
            daily_values: Ordered daily portfolio values.

        Returns:
            Maximum drawdown as a positive percentage (e.g. 12.5 means -12.5 %).
        """
        if len(daily_values) < 2:
            return 0.0

        peak = daily_values[0]
        max_dd = 0.0
        for value in daily_values:
            if value > peak:
                peak = value
            if peak > 0:
                dd = (peak - value) / peak * 100.0
                if dd > max_dd:
                    max_dd = dd

        return max_dd

    def _sharpe_ratio(self, daily_values: list[float], risk_free_rate_annual: float) -> float:
        """Compute annualised Sharpe ratio from daily portfolio values.

        Args:
            daily_values: Ordered daily portfolio values.
            risk_free_rate_annual: Annual risk-free rate as a decimal.

        Returns:
            Annualised Sharpe ratio. Returns 0.0 if insufficient data.
        """
        if len(daily_values) < 2:
            return 0.0

        daily_returns = [
            (daily_values[i] - daily_values[i - 1]) / daily_values[i - 1]
            for i in range(1, len(daily_values))
            if daily_values[i - 1] > 0
        ]

        if not daily_returns:
            return 0.0

        daily_rf = risk_free_rate_annual / 252.0
        excess = [r - daily_rf for r in daily_returns]
        mean_excess = sum(excess) / len(excess)

        variance = sum((r - mean_excess) ** 2 for r in excess) / len(excess)
        std_excess = math.sqrt(variance) if variance > 0 else 0.0

        if std_excess < 1e-8:
            return 0.0

        sharpe = (mean_excess / std_excess) * math.sqrt(252.0)
        return max(-999999.9999, min(999999.9999, sharpe))

    def _win_rate(self, trades: list[dict[str, Any]]) -> float:
        """Compute win rate as a percentage across the given trade list.

        Args:
            trades: List of trade dicts with realized_pnl_pct key.

        Returns:
            Win rate as a percentage (0–100). Returns 0.0 for empty lists.
        """
        if not trades:
            return 0.0
        winners = sum(1 for t in trades if float(t['realized_pnl_pct']) > 0)
        return (winners / len(trades)) * 100.0
