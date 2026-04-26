"""Backtesting service with strategy framework and persistent run storage."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from statistics import mean
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from config import settings
from models.backtest import BacktestRun, BacktestTrade
from models.feature import Feature
from models.ohlcv import Ohlcv
from models.security import Security
from strategies import create_strategy
from strategies.base import (
    SIGNAL_HOLD,
    SIGNAL_LONG_ENTRY,
    SIGNAL_LONG_EXIT,
    SIGNAL_SHORT_ENTRY,
    SIGNAL_SHORT_EXIT,
    BacktestCandle,
)
from utils.logger import logger


@dataclass
class _OpenPosition:
    """Internal representation of an open position during simulation."""

    direction: str
    security_id: int
    ticker: str
    entry_index: int
    entry_date: date
    entry_price: Decimal
    quantity: Decimal
    entry_signal: str
    entry_features: dict[str, Any] | None


class BacktestService:
    """Service class for strategy execution and historical backtesting."""

    FOUR_DP = Decimal('0.0001')
    SIX_DP = Decimal('0.000001')
    HUNDRED = Decimal('100')
    BASIS_POINTS_DENOMINATOR = Decimal('10000')

    def __init__(self) -> None:
        self._engine = create_engine(settings.DATABASE_URL, echo=settings.DB_ECHO, future=True)
        self._session_factory = sessionmaker(bind=self._engine, autoflush=False, autocommit=False, future=True)

    def run_backtest(
        self,
        strategy_name: str,
        strategy_params: dict[str, Any] | None = None,
        timeframe: str = '1DAY',
        start_date: date | None = None,
        end_date: date | None = None,
        tickers: list[str] | None = None,
        initial_capital: Decimal = Decimal('100000'),
        transaction_cost_bps: Decimal = Decimal('5'),
        slippage_bps: Decimal = Decimal('2'),
        allow_short: bool = True,
        quantity: Decimal = Decimal('1'),
    ) -> dict[str, Any]:
        """Execute a strategy backtest and persist run + trades."""
        params = dict(strategy_params or {})
        strategy = create_strategy(strategy_name=strategy_name, strategy_params=params)

        strategy.supports_short = bool(strategy.supports_short and allow_short)

        logger.info(
            'Starting backtest strategy={} timeframe={} allow_short={} tickers_count={}',
            strategy_name,
            timeframe,
            allow_short,
            0 if not tickers else len(tickers),
        )

        securities = self._get_securities(tickers)
        trades: list[dict[str, Any]] = []
        skipped: list[str] = []

        for security in securities:
            candles = self._load_candles(security.id, security.ticker, timeframe, start_date, end_date)
            if len(candles) <= strategy.warmup_bars:
                skipped.append(security.ticker)
                continue

            security_trades = self._simulate_security(
                candles=candles,
                security_id=security.id,
                ticker=security.ticker,
                strategy=strategy,
                transaction_cost_bps=transaction_cost_bps,
                slippage_bps=slippage_bps,
                quantity=quantity,
            )
            trades.extend(security_trades)

        summary = self._build_summary(initial_capital=initial_capital, trades=trades)

        run_id = self._persist_run(
            strategy_name=strategy_name,
            strategy_params=params,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            allow_short=allow_short,
            transaction_cost_bps=transaction_cost_bps,
            slippage_bps=slippage_bps,
            initial_capital=summary['initial_capital'],
            final_capital=summary['final_capital'],
            total_return_pct=summary['total_return_pct'],
            max_drawdown_pct=summary['max_drawdown_pct'],
            total_trades=summary['total_trades'],
            winning_trades=summary['winning_trades'],
            win_rate_pct=summary['win_rate_pct'],
            avg_trade_return_pct=summary['avg_trade_return_pct'],
            trades=trades,
            notes=self._build_run_notes(skipped),
        )

        return {
            'success': True,
            'run_id': run_id,
            'strategy_name': strategy_name,
            'strategy_params': params,
            'timeframe': timeframe,
            'tickers_count': len(securities),
            'skipped_tickers_count': len(skipped),
            'skipped_tickers': skipped,
            'allow_short': allow_short,
            'transaction_cost_bps': str(self._q4(transaction_cost_bps)),
            'slippage_bps': str(self._q4(slippage_bps)),
            'summary': {
                'initial_capital': str(summary['initial_capital']),
                'final_capital': str(summary['final_capital']),
                'total_return_pct': str(summary['total_return_pct']),
                'max_drawdown_pct': str(summary['max_drawdown_pct']),
                'total_trades': summary['total_trades'],
                'winning_trades': summary['winning_trades'],
                'win_rate_pct': str(summary['win_rate_pct']),
                'avg_trade_return_pct': str(summary['avg_trade_return_pct']),
            },
            'trades_preview': [self._serialize_trade_preview(trade) for trade in trades[:20]],
        }

    def _get_securities(self, tickers: list[str] | None) -> list[Security]:
        """Fetch active securities, optionally filtered by ticker list."""
        with self._session_factory() as session:
            query = select(Security).where(Security.is_active.is_(True)).order_by(Security.ticker.asc())
            if tickers:
                normalized = [item.strip().upper() for item in tickers if item.strip()]
                query = query.where(Security.ticker.in_(normalized))
            return list(session.execute(query).scalars().all())

    def _load_candles(
        self,
        security_id: int,
        ticker: str,
        timeframe: str,
        start_date: date | None,
        end_date: date | None,
    ) -> list[BacktestCandle]:
        """Load OHLCV candles joined with optional engineered features."""
        with self._session_factory() as session:
            query = (
                select(Ohlcv, Feature)
                .outerjoin(Feature, Feature.ohlcv_id == Ohlcv.id)
                .where(Ohlcv.security_id == security_id, Ohlcv.timeframe == timeframe)
                .order_by(Ohlcv.candle_date.asc(), Ohlcv.id.asc())
            )

            if start_date is not None:
                query = query.where(Ohlcv.candle_date >= start_date)
            if end_date is not None:
                query = query.where(Ohlcv.candle_date <= end_date)

            rows = list(session.execute(query).all())

        candles: list[BacktestCandle] = []
        for ohlcv, feature in rows:
            features = None if feature is None else self._feature_payload(feature)
            candles.append(
                BacktestCandle(
                    security_id=security_id,
                    ticker=ticker,
                    candle_date=ohlcv.candle_date,
                    timeframe=ohlcv.timeframe,
                    open=Decimal(ohlcv.open),
                    high=Decimal(ohlcv.high),
                    low=Decimal(ohlcv.low),
                    close=Decimal(ohlcv.close),
                    volume=int(ohlcv.volume),
                    features=features,
                )
            )

        return candles

    def _simulate_security(
        self,
        candles: list[BacktestCandle],
        security_id: int,
        ticker: str,
        strategy: Any,
        transaction_cost_bps: Decimal,
        slippage_bps: Decimal,
        quantity: Decimal,
    ) -> list[dict[str, Any]]:
        """Run one strategy simulation for one security's candle series."""
        position: _OpenPosition | None = None
        trades: list[dict[str, Any]] = []

        for index, candle in enumerate(candles):
            current_state = 'FLAT' if position is None else position.direction
            signal = strategy.validate_signal(strategy.generate_signal(index=index, candles=candles, position=current_state))

            if signal == SIGNAL_HOLD:
                continue

            if signal == SIGNAL_LONG_ENTRY and strategy.supports_long:
                if position is not None and position.direction == 'SHORT':
                    trades.append(
                        self._close_position(
                            position=position,
                            exit_signal='REVERSE_TO_LONG',
                            exit_index=index,
                            exit_candle=candle,
                            transaction_cost_bps=transaction_cost_bps,
                            slippage_bps=slippage_bps,
                        )
                    )
                    position = None

                if position is None:
                    position = self._open_position(
                        direction='LONG',
                        security_id=security_id,
                        ticker=ticker,
                        entry_signal=signal,
                        entry_index=index,
                        entry_candle=candle,
                        quantity=quantity,
                        slippage_bps=slippage_bps,
                    )

            elif signal == SIGNAL_SHORT_ENTRY and strategy.supports_short:
                if position is not None and position.direction == 'LONG':
                    trades.append(
                        self._close_position(
                            position=position,
                            exit_signal='REVERSE_TO_SHORT',
                            exit_index=index,
                            exit_candle=candle,
                            transaction_cost_bps=transaction_cost_bps,
                            slippage_bps=slippage_bps,
                        )
                    )
                    position = None

                if position is None:
                    position = self._open_position(
                        direction='SHORT',
                        security_id=security_id,
                        ticker=ticker,
                        entry_signal=signal,
                        entry_index=index,
                        entry_candle=candle,
                        quantity=quantity,
                        slippage_bps=slippage_bps,
                    )

            elif signal == SIGNAL_LONG_EXIT and position is not None and position.direction == 'LONG':
                trades.append(
                    self._close_position(
                        position=position,
                        exit_signal=signal,
                        exit_index=index,
                        exit_candle=candle,
                        transaction_cost_bps=transaction_cost_bps,
                        slippage_bps=slippage_bps,
                    )
                )
                position = None

            elif signal == SIGNAL_SHORT_EXIT and position is not None and position.direction == 'SHORT':
                trades.append(
                    self._close_position(
                        position=position,
                        exit_signal=signal,
                        exit_index=index,
                        exit_candle=candle,
                        transaction_cost_bps=transaction_cost_bps,
                        slippage_bps=slippage_bps,
                    )
                )
                position = None

        if position is not None:
            last_index = len(candles) - 1
            trades.append(
                self._close_position(
                    position=position,
                    exit_signal='FORCE_CLOSE_END',
                    exit_index=last_index,
                    exit_candle=candles[last_index],
                    transaction_cost_bps=transaction_cost_bps,
                    slippage_bps=slippage_bps,
                )
            )

        return trades

    def _open_position(
        self,
        direction: str,
        security_id: int,
        ticker: str,
        entry_signal: str,
        entry_index: int,
        entry_candle: BacktestCandle,
        quantity: Decimal,
        slippage_bps: Decimal,
    ) -> _OpenPosition:
        """Open a long or short position with slippage-aware fill price."""
        side = 'BUY' if direction == 'LONG' else 'SELL'
        entry_price = self._apply_slippage(price=entry_candle.close, side=side, slippage_bps=slippage_bps)

        return _OpenPosition(
            direction=direction,
            security_id=security_id,
            ticker=ticker,
            entry_index=entry_index,
            entry_date=entry_candle.candle_date,
            entry_price=self._q6(entry_price),
            quantity=self._q6(quantity),
            entry_signal=entry_signal,
            entry_features=entry_candle.features,
        )

    def _close_position(
        self,
        position: _OpenPosition,
        exit_signal: str,
        exit_index: int,
        exit_candle: BacktestCandle,
        transaction_cost_bps: Decimal,
        slippage_bps: Decimal,
    ) -> dict[str, Any]:
        """Close an open position and calculate gross/net trade metrics."""
        side = 'SELL' if position.direction == 'LONG' else 'BUY'
        exit_price = self._apply_slippage(price=exit_candle.close, side=side, slippage_bps=slippage_bps)

        entry_notional = position.entry_price * position.quantity
        exit_notional = exit_price * position.quantity
        fee_rate = transaction_cost_bps / self.BASIS_POINTS_DENOMINATOR
        total_fees = (entry_notional + exit_notional) * fee_rate

        if position.direction == 'LONG':
            gross_pnl = (exit_price - position.entry_price) * position.quantity
        else:
            gross_pnl = (position.entry_price - exit_price) * position.quantity

        net_pnl = gross_pnl - total_fees
        return_pct = Decimal('0') if entry_notional == 0 else (net_pnl / entry_notional) * self.HUNDRED

        return {
            'security_id': position.security_id,
            'ticker': position.ticker,
            'direction': position.direction,
            'entry_date': position.entry_date,
            'exit_date': exit_candle.candle_date,
            'entry_price': self._q6(position.entry_price),
            'exit_price': self._q6(exit_price),
            'quantity': self._q6(position.quantity),
            'entry_signal': position.entry_signal,
            'exit_signal': exit_signal,
            'gross_pnl': self._q6(gross_pnl),
            'net_pnl': self._q6(net_pnl),
            'return_pct': self._q4(return_pct),
            'bars_held': max(0, exit_index - position.entry_index),
            'entry_features': position.entry_features,
            'exit_features': exit_candle.features,
        }

    def _build_summary(self, initial_capital: Decimal, trades: list[dict[str, Any]]) -> dict[str, Any]:
        """Aggregate equity and risk metrics from executed trades."""
        equity = Decimal(initial_capital)
        peak = Decimal(initial_capital)
        max_drawdown_pct = Decimal('0')

        winning_trades = 0
        trade_returns: list[float] = []

        for trade in trades:
            net_pnl = Decimal(trade['net_pnl'])
            equity += net_pnl

            if equity > peak:
                peak = equity

            if peak > 0:
                drawdown_pct = ((peak - equity) / peak) * self.HUNDRED
                if drawdown_pct > max_drawdown_pct:
                    max_drawdown_pct = drawdown_pct

            if net_pnl > 0:
                winning_trades += 1

            trade_returns.append(float(Decimal(trade['return_pct'])))

        total_trades = len(trades)
        final_capital = self._q6(equity)
        total_return_pct = Decimal('0') if initial_capital == 0 else ((final_capital - initial_capital) / initial_capital) * self.HUNDRED
        win_rate_pct = Decimal('0') if total_trades == 0 else (Decimal(winning_trades) / Decimal(total_trades)) * self.HUNDRED
        avg_trade_return_pct = Decimal('0') if not trade_returns else Decimal(str(mean(trade_returns)))

        return {
            'initial_capital': self._q6(initial_capital),
            'final_capital': final_capital,
            'total_return_pct': self._q4(total_return_pct),
            'max_drawdown_pct': self._q4(max_drawdown_pct),
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate_pct': self._q4(win_rate_pct),
            'avg_trade_return_pct': self._q4(avg_trade_return_pct),
        }

    def _persist_run(
        self,
        strategy_name: str,
        strategy_params: dict[str, Any],
        timeframe: str,
        start_date: date | None,
        end_date: date | None,
        allow_short: bool,
        transaction_cost_bps: Decimal,
        slippage_bps: Decimal,
        initial_capital: Decimal,
        final_capital: Decimal,
        total_return_pct: Decimal,
        max_drawdown_pct: Decimal,
        total_trades: int,
        winning_trades: int,
        win_rate_pct: Decimal,
        avg_trade_return_pct: Decimal,
        trades: list[dict[str, Any]],
        notes: str | None,
    ) -> int:
        """Persist one backtest run and all associated trades."""
        with self._session_factory() as session:
            run = BacktestRun(
                strategy_name=strategy_name,
                strategy_params=strategy_params,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                allow_short=allow_short,
                transaction_cost_bps=self._q4(transaction_cost_bps),
                slippage_bps=self._q4(slippage_bps),
                initial_capital=self._q6(initial_capital),
                final_capital=self._q6(final_capital),
                total_return_pct=self._q4(total_return_pct),
                max_drawdown_pct=self._q4(max_drawdown_pct),
                total_trades=total_trades,
                winning_trades=winning_trades,
                win_rate_pct=self._q4(win_rate_pct),
                avg_trade_return_pct=self._q4(avg_trade_return_pct),
                status='completed',
                notes=notes,
            )

            session.add(run)
            session.flush()

            for trade in trades:
                session.add(
                    BacktestTrade(
                        backtest_run_id=run.id,
                        security_id=int(trade['security_id']),
                        ticker=str(trade['ticker']),
                        direction=str(trade['direction']),
                        entry_date=trade['entry_date'],
                        exit_date=trade['exit_date'],
                        entry_price=self._q6(Decimal(trade['entry_price'])),
                        exit_price=self._q6(Decimal(trade['exit_price'])),
                        quantity=self._q6(Decimal(trade['quantity'])),
                        entry_signal=str(trade['entry_signal']),
                        exit_signal=str(trade['exit_signal']),
                        gross_pnl=self._q6(Decimal(trade['gross_pnl'])),
                        net_pnl=self._q6(Decimal(trade['net_pnl'])),
                        return_pct=self._q4(Decimal(trade['return_pct'])),
                        bars_held=int(trade['bars_held']),
                        entry_features=self._json_safe_features(trade.get('entry_features')),
                        exit_features=self._json_safe_features(trade.get('exit_features')),
                    )
                )

            session.commit()
            return int(run.id)

    def _feature_payload(self, feature: Feature) -> dict[str, Any]:
        """Normalize feature model row into a strategy-friendly payload."""
        return {
            'body_size_pct': float(feature.body_size_pct),
            'upper_wick_pct': float(feature.upper_wick_pct),
            'lower_wick_pct': float(feature.lower_wick_pct),
            'range_pct': float(feature.range_pct),
            'close_position_pct': float(feature.close_position_pct),
            'bias': str(feature.bias),
            'candle_type': str(feature.candle_type),
        }

    def _json_safe_features(self, features: dict[str, Any] | None) -> dict[str, Any] | None:
        """Ensure feature payload is JSON-safe for DB persistence."""
        if features is None:
            return None

        payload: dict[str, Any] = {}
        for key, value in features.items():
            if isinstance(value, Decimal):
                payload[key] = float(value)
            else:
                payload[key] = value
        return payload

    def _apply_slippage(self, price: Decimal, side: str, slippage_bps: Decimal) -> Decimal:
        """Apply adverse slippage to execution price based on order side."""
        ratio = slippage_bps / self.BASIS_POINTS_DENOMINATOR
        if side == 'BUY':
            return price * (Decimal('1') + ratio)
        return price * (Decimal('1') - ratio)

    def _q4(self, value: Decimal) -> Decimal:
        """Quantize to 4 decimal places."""
        return Decimal(value).quantize(self.FOUR_DP, rounding=ROUND_HALF_UP)

    def _q6(self, value: Decimal) -> Decimal:
        """Quantize to 6 decimal places."""
        return Decimal(value).quantize(self.SIX_DP, rounding=ROUND_HALF_UP)

    def _serialize_trade_preview(self, trade: dict[str, Any]) -> dict[str, Any]:
        """Return a compact, JSON-friendly trade preview for terminal output."""
        return {
            'ticker': str(trade['ticker']),
            'direction': str(trade['direction']),
            'entry_date': str(trade['entry_date']),
            'exit_date': str(trade['exit_date']),
            'entry_price': str(trade['entry_price']),
            'exit_price': str(trade['exit_price']),
            'net_pnl': str(trade['net_pnl']),
            'return_pct': str(trade['return_pct']),
            'entry_signal': str(trade['entry_signal']),
            'exit_signal': str(trade['exit_signal']),
        }

    def _build_run_notes(self, skipped: list[str]) -> str | None:
        """Build compact run notes to capture skipped ticker information."""
        if not skipped:
            return None

        preview = ','.join(skipped[:10])
        remaining = max(0, len(skipped) - 10)
        suffix = '' if remaining == 0 else f' (+{remaining} more)'
        return f'Skipped tickers due to insufficient candles: {preview}{suffix}'
