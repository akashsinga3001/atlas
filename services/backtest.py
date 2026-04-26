"""Backtesting service with strategy framework and persistent run storage."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import re
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
    initial_stop: Decimal | None = None
    trailing_stop: Decimal | None = None
    best_close: Decimal | None = None


class BacktestService:
    """Service class for strategy execution and historical backtesting."""

    FOUR_DP = Decimal('0.0001')
    SIX_DP = Decimal('0.000001')
    HUNDRED = Decimal('100')
    BASIS_POINTS_DENOMINATOR = Decimal('10000')
    FUT_UNDERLYING_PATTERN = re.compile(r'^(?P<base>[A-Z0-9&\-]+?)(?:\d{1,2}[A-Z]{3}\d{2}|[A-Z]{3}\d{2})FUT$')
    FUT_PREFIX_FALLBACK_PATTERN = re.compile(r'^(?P<base>[A-Z0-9&\-]+?)(?=\d)')

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
        persisted_params = self._json_safe_dict(params)
        strategy = create_strategy(strategy_name=strategy_name, strategy_params=params)

        strategy.supports_short = bool(strategy.supports_short and allow_short)

        logger.info(
            'Starting backtest strategy={} timeframe={} allow_short={} tickers_count={}',
            strategy_name,
            timeframe,
            allow_short,
            0 if not tickers else len(tickers),
        )

        signal_securities = self._get_securities(tickers)
        trades: list[dict[str, Any]] = []
        skipped: list[str] = []

        is_multitimeframe_strategy = strategy_name == 'ma_reversal_multitimeframe'

        futures_lookup: dict[str, list[Security]] = {}
        if is_multitimeframe_strategy:
            signal_securities = self._get_eq_securities(tickers)
            futures_lookup = self._build_futures_lookup_by_underlying(self._get_active_futures())

        for security in signal_securities:
            if is_multitimeframe_strategy:
                futures_for_underlying = futures_lookup.get(security.ticker, [])
                if not futures_for_underlying:
                    skipped.append(security.ticker)
                    continue

                candles_by_timeframe = self._load_multitimeframe_candles(
                    security_id=security.id,
                    ticker=security.ticker,
                    start_date=start_date,
                    end_date=end_date,
                )

                daily_candles = candles_by_timeframe['1DAY']
                weekly_candles = candles_by_timeframe['1WEEK']
                monthly_candles = candles_by_timeframe['1MONTH']

                if (
                    len(daily_candles) <= strategy.warmup_bars
                    or len(weekly_candles) <= strategy.warmup_bars
                    or len(monthly_candles) <= strategy.warmup_bars
                ):
                    skipped.append(security.ticker)
                    continue

                execution_candles_by_security = self._load_execution_candles_for_futures(
                    futures=futures_for_underlying,
                    start_date=start_date,
                    end_date=end_date,
                )
                if not execution_candles_by_security:
                    skipped.append(security.ticker)
                    continue

                security_trades = self._simulate_multitimeframe_security(
                    daily_candles=daily_candles,
                    weekly_candles=weekly_candles,
                    monthly_candles=monthly_candles,
                    signal_ticker=security.ticker,
                    strategy=strategy,
                    transaction_cost_bps=transaction_cost_bps,
                    slippage_bps=slippage_bps,
                    quantity=quantity,
                    futures_contracts=futures_for_underlying,
                    execution_candles_by_security=execution_candles_by_security,
                )
            else:
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
            strategy_params=persisted_params,
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
            'strategy_params': persisted_params,
            'timeframe': timeframe,
            'tickers_count': len(signal_securities),
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

    def _get_eq_securities(self, tickers: list[str] | None) -> list[Security]:
        """Fetch active EQ securities optionally filtered by ticker list."""
        with self._session_factory() as session:
            query = select(Security).where(Security.is_active.is_(True), Security.type == 'EQ').order_by(Security.ticker.asc())
            if tickers:
                normalized = [item.strip().upper() for item in tickers if item.strip()]
                query = query.where(Security.ticker.in_(normalized))
            return list(session.execute(query).scalars().all())

    def _get_active_futures(self) -> list[Security]:
        """Fetch active FUT securities with available expiry dates."""
        with self._session_factory() as session:
            query = (
                select(Security)
                .where(Security.is_active.is_(True), Security.type == 'FUT', Security.expiry_date.is_not(None))
                .order_by(Security.ticker.asc())
            )
            return list(session.execute(query).scalars().all())

    def _build_futures_lookup_by_underlying(self, futures: list[Security]) -> dict[str, list[Security]]:
        """Group futures contracts by derived underlying EQ ticker."""
        lookup: dict[str, list[Security]] = {}
        for future in futures:
            underlying = self._extract_future_underlying(future.ticker)
            if underlying is None:
                continue
            lookup.setdefault(underlying, []).append(future)

        for contracts in lookup.values():
            contracts.sort(key=lambda item: (item.expiry_date or date.max, item.ticker))
        return lookup

    def _extract_future_underlying(self, future_ticker: str) -> str | None:
        """Derive underlying symbol from futures ticker."""
        ticker = future_ticker.strip().upper()
        if not ticker.endswith('FUT'):
            return None

        regex_match = self.FUT_UNDERLYING_PATTERN.match(ticker)
        if regex_match:
            base = regex_match.group('base')
            return base or None

        fallback_match = self.FUT_PREFIX_FALLBACK_PATTERN.match(ticker)
        if fallback_match:
            base = fallback_match.group('base')
            return base or None

        return None

    def _load_execution_candles_for_futures(
        self,
        futures: list[Security],
        start_date: date | None,
        end_date: date | None,
    ) -> dict[int, dict[date, BacktestCandle]]:
        """Load 1DAY execution candles for candidate futures contracts."""
        execution_map: dict[int, dict[date, BacktestCandle]] = {}
        for future in futures:
            candles = self._load_candles(
                security_id=future.id,
                ticker=future.ticker,
                timeframe='1DAY',
                start_date=start_date,
                end_date=end_date,
            )
            if not candles:
                continue
            execution_map[future.id] = {candle.candle_date: candle for candle in candles}

        return execution_map

    def _resolve_futures_contract_for_date(self, contracts: list[Security], as_of_date: date) -> Security | None:
        """Select futures contract by date rule: <=15 same month, >15 next month, else nearest."""
        if not contracts:
            return None

        target_year = as_of_date.year
        target_month = as_of_date.month
        if as_of_date.day > 15:
            if target_month == 12:
                target_month = 1
                target_year += 1
            else:
                target_month += 1

        month_matches = [
            contract
            for contract in contracts
            if contract.expiry_date is not None
            and contract.expiry_date.year == target_year
            and contract.expiry_date.month == target_month
            and contract.expiry_date >= as_of_date
        ]
        if month_matches:
            return min(month_matches, key=lambda item: item.expiry_date or date.max)

        valid_future = [contract for contract in contracts if contract.expiry_date is not None and contract.expiry_date >= as_of_date]
        if valid_future:
            return min(valid_future, key=lambda item: item.expiry_date or date.max)

        return None

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

    def _simulate_multitimeframe_security(
        self,
        daily_candles: list[BacktestCandle],
        weekly_candles: list[BacktestCandle],
        monthly_candles: list[BacktestCandle],
        signal_ticker: str,
        strategy: Any,
        transaction_cost_bps: Decimal,
        slippage_bps: Decimal,
        quantity: Decimal,
        futures_contracts: list[Security],
        execution_candles_by_security: dict[int, dict[date, BacktestCandle]],
    ) -> list[dict[str, Any]]:
        """Run monthly-gated strategy with EQ signals and FUT execution."""
        position: _OpenPosition | None = None
        trades: list[dict[str, Any]] = []
        last_exit_index = -1

        weekly_index = -1
        monthly_index = -1

        for daily_index, daily_candle in enumerate(daily_candles):
            while weekly_index + 1 < len(weekly_candles) and weekly_candles[weekly_index + 1].candle_date <= daily_candle.candle_date:
                weekly_index += 1

            while monthly_index + 1 < len(monthly_candles) and monthly_candles[monthly_index + 1].candle_date <= daily_candle.candle_date:
                monthly_index += 1

            if weekly_index < 0 or monthly_index < 0:
                continue

            selected_contract = self._resolve_futures_contract_for_date(futures_contracts, daily_candle.candle_date)
            selected_execution_candle = None
            if selected_contract is not None:
                selected_execution_candle = execution_candles_by_security.get(selected_contract.id, {}).get(daily_candle.candle_date)

            current_execution_candle = None
            if position is not None:
                current_execution_candle = execution_candles_by_security.get(position.security_id, {}).get(daily_candle.candle_date)
                if current_execution_candle is None:
                    continue

            if position is not None:
                position = self._update_position_stops(position=position, candle=current_execution_candle, strategy=strategy)

                stop_kind = self._get_stop_hit_kind(position=position, candle=current_execution_candle, strategy=strategy)
                if stop_kind is not None:
                    stop_price = position.trailing_stop if position.trailing_stop is not None else position.entry_price
                    trades.append(
                        self._close_position(
                            position=position,
                            exit_signal=strategy.stop_exit_signal(stop_kind),
                            exit_index=daily_index,
                            exit_candle=current_execution_candle,
                            transaction_cost_bps=transaction_cost_bps,
                            slippage_bps=slippage_bps,
                            exit_price_override=stop_price,
                        )
                    )
                    position = None
                    last_exit_index = daily_index
                    continue

                if selected_contract is not None and selected_execution_candle is not None and selected_contract.id != position.security_id:
                    trades.append(
                        self._close_position(
                            position=position,
                            exit_signal='ROLL_OVER_EXIT',
                            exit_index=daily_index,
                            exit_candle=current_execution_candle,
                            transaction_cost_bps=transaction_cost_bps,
                            slippage_bps=slippage_bps,
                        )
                    )
                    stop_levels = strategy.build_stop_levels(entry_price=selected_execution_candle.close, direction=position.direction)
                    position = self._open_position(
                        direction=position.direction,
                        security_id=selected_contract.id,
                        ticker=selected_contract.ticker,
                        entry_signal='ROLL_OVER_ENTRY',
                        entry_index=daily_index,
                        entry_candle=selected_execution_candle,
                        quantity=quantity,
                        slippage_bps=slippage_bps,
                        stop_levels=stop_levels,
                    )
                    position.entry_features = self._merge_signal_context(position.entry_features, signal_ticker, 'ROLL_OVER_ENTRY')

            if daily_index == last_exit_index:
                continue

            signal = strategy.generate_multitimeframe_signal(
                daily_candles=daily_candles,
                weekly_candles=weekly_candles,
                monthly_candles=monthly_candles,
                daily_index=daily_index,
                weekly_index=weekly_index,
                monthly_index=monthly_index,
            )

            if signal == SIGNAL_HOLD:
                continue

            if position is None:
                if selected_contract is None or selected_execution_candle is None:
                    continue

                if signal == SIGNAL_LONG_ENTRY and strategy.supports_long:
                    stop_levels = strategy.build_stop_levels(entry_price=selected_execution_candle.close, direction='LONG')
                    position = self._open_position(
                        direction='LONG',
                        security_id=selected_contract.id,
                        ticker=selected_contract.ticker,
                        entry_signal=signal,
                        entry_index=daily_index,
                        entry_candle=selected_execution_candle,
                        quantity=quantity,
                        slippage_bps=slippage_bps,
                        stop_levels=stop_levels,
                    )
                elif signal == SIGNAL_SHORT_ENTRY and strategy.supports_short:
                    stop_levels = strategy.build_stop_levels(entry_price=selected_execution_candle.close, direction='SHORT')
                    position = self._open_position(
                        direction='SHORT',
                        security_id=selected_contract.id,
                        ticker=selected_contract.ticker,
                        entry_signal=signal,
                        entry_index=daily_index,
                        entry_candle=selected_execution_candle,
                        quantity=quantity,
                        slippage_bps=slippage_bps,
                        stop_levels=stop_levels,
                    )

                if position is not None:
                    position.entry_features = self._merge_signal_context(position.entry_features, signal_ticker, signal)
                continue

            if signal == SIGNAL_LONG_ENTRY and position.direction == 'SHORT':
                if current_execution_candle is None:
                    continue
                trades.append(
                    self._close_position(
                        position=position,
                        exit_signal='OPPOSITE_SIGNAL_EXIT',
                        exit_index=daily_index,
                        exit_candle=current_execution_candle,
                        transaction_cost_bps=transaction_cost_bps,
                        slippage_bps=slippage_bps,
                    )
                )
                position = None
                last_exit_index = daily_index
                continue

            if signal == SIGNAL_SHORT_ENTRY and position.direction == 'LONG':
                if current_execution_candle is None:
                    continue
                trades.append(
                    self._close_position(
                        position=position,
                        exit_signal='OPPOSITE_SIGNAL_EXIT',
                        exit_index=daily_index,
                        exit_candle=current_execution_candle,
                        transaction_cost_bps=transaction_cost_bps,
                        slippage_bps=slippage_bps,
                    )
                )
                position = None
                last_exit_index = daily_index
                continue

        if position is not None:
            last_index = len(daily_candles) - 1
            final_execution_candle = execution_candles_by_security.get(position.security_id, {}).get(daily_candles[last_index].candle_date)
            if final_execution_candle is None:
                return trades

            trades.append(
                self._close_position(
                    position=position,
                    exit_signal='FORCE_CLOSE_END',
                    exit_index=last_index,
                    exit_candle=final_execution_candle,
                    transaction_cost_bps=transaction_cost_bps,
                    slippage_bps=slippage_bps,
                )
            )

        return trades

    def _load_multitimeframe_candles(
        self,
        security_id: int,
        ticker: str,
        start_date: date | None,
        end_date: date | None,
    ) -> dict[str, list[BacktestCandle]]:
        """Load aligned 1DAY/1WEEK/1MONTH candle streams for one security."""
        return {
            '1DAY': self._load_candles(security_id=security_id, ticker=ticker, timeframe='1DAY', start_date=start_date, end_date=end_date),
            '1WEEK': self._load_candles(security_id=security_id, ticker=ticker, timeframe='1WEEK', start_date=start_date, end_date=end_date),
            '1MONTH': self._load_candles(security_id=security_id, ticker=ticker, timeframe='1MONTH', start_date=start_date, end_date=end_date),
        }

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
        stop_levels: dict[str, Decimal] | None = None,
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
            initial_stop=None if stop_levels is None else self._q6(stop_levels['initial_stop']),
            trailing_stop=None if stop_levels is None else self._q6(stop_levels['trailing_stop']),
            best_close=self._q6(entry_candle.close),
        )

    def _close_position(
        self,
        position: _OpenPosition,
        exit_signal: str,
        exit_index: int,
        exit_candle: BacktestCandle,
        transaction_cost_bps: Decimal,
        slippage_bps: Decimal,
        exit_price_override: Decimal | None = None,
    ) -> dict[str, Any]:
        """Close an open position and calculate gross/net trade metrics."""
        if exit_price_override is None:
            side = 'SELL' if position.direction == 'LONG' else 'BUY'
            exit_price = self._apply_slippage(price=exit_candle.close, side=side, slippage_bps=slippage_bps)
        else:
            exit_price = Decimal(exit_price_override)

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

    def _update_position_stops(self, position: _OpenPosition, candle: BacktestCandle, strategy: Any) -> _OpenPosition:
        """Update best close and trailing stop for active position."""
        if position.best_close is None:
            position.best_close = candle.close

        if position.trailing_stop is None:
            return position

        if position.direction == 'LONG':
            position.best_close = max(position.best_close, candle.close)
        else:
            position.best_close = min(position.best_close, candle.close)

        position.trailing_stop = self._q6(
            strategy.update_trailing_stop(
                direction=position.direction,
                current_stop=position.trailing_stop,
                best_close=position.best_close,
            )
        )
        return position

    def _get_stop_hit_kind(self, position: _OpenPosition, candle: BacktestCandle, strategy: Any) -> str | None:
        """Return INITIAL/TRAILING when corresponding stop level is breached by wick."""
        if position.trailing_stop is None:
            return None

        if not strategy.stop_hit(direction=position.direction, candle=candle, stop_price=position.trailing_stop):
            return None

        if position.initial_stop is not None and position.trailing_stop == position.initial_stop:
            return 'INITIAL'

        return 'TRAILING'

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

    def _json_safe_dict(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Convert Decimal values to JSON-safe primitives for persistence."""
        safe: dict[str, Any] = {}
        for key, value in payload.items():
            if isinstance(value, Decimal):
                safe[key] = str(value)
            else:
                safe[key] = value
        return safe

    def _merge_signal_context(self, features: dict[str, Any] | None, signal_ticker: str, signal_event: str) -> dict[str, Any]:
        """Attach signal source metadata for EQ-signal/FUT-execution traceability."""
        payload = dict(features or {})
        payload['signal_ticker'] = signal_ticker
        payload['signal_event'] = signal_event
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
