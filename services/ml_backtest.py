"""Walk-forward backtesting engine for ML directional prediction strategies."""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from time import perf_counter
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from config import settings
from models.backtest import BacktestDailyMetrics, BacktestPosition, BacktestPrediction, BacktestRun
from models.ohlcv import Ohlcv
from services.ml_dataset import MlDatasetService
from services.ml_metrics import MlMetricsService
from services.ml_model import MlModelService
from services.ml_risk import MlRiskService, RiskParameters
from utils.logger import logger


@dataclass
class WalkForwardConfig:
    """Configuration for one walk-forward backtest run."""

    backtest_name: str
    total_start_date: date         # Earliest date used for initial training window
    total_end_date: date           # Latest date used (end of last test window)
    train_window_days: int         # Rolling training window size (e.g. 365)
    test_window_days: int          # Rolling test/evaluation window size (e.g. 90)
    step_days: int                 # How many days to advance each fold (e.g. 90)
    horizon_days: int              # ML prediction horizon
    threshold_pct: float           # ML label threshold
    model_type: str                # 'rf', 'lgb', 'xgb', or 'ensemble'
    top_n_per_direction: int       # Max signals per direction per day
    risk: RiskParameters
    notes: str | None = None


@dataclass
class FoldResult:
    """Outputs produced by one walk-forward fold."""

    fold_index: int
    train_start: date
    train_end: date
    test_start: date
    test_end: date
    closed_trades: list[dict[str, Any]] = field(default_factory=list)
    open_positions_end: list[dict[str, Any]] = field(default_factory=list)
    predictions: list[dict[str, Any]] = field(default_factory=list)
    daily_portfolio: list[dict[str, Any]] = field(default_factory=list)
    fold_metrics: dict[str, float] = field(default_factory=dict)
    model_long_path: str = ''
    model_short_path: str = ''


class MlBacktestService:
    """Run walk-forward backtests and persist results to the database."""

    def __init__(self) -> None:
        self._engine = create_engine(settings.DATABASE_URL, echo=settings.DB_ECHO, future=True)
        self._session_factory = sessionmaker(bind=self._engine, autoflush=False, autocommit=False, future=True)
        self._dataset_service = MlDatasetService()
        self._model_service = MlModelService()
        self._risk_service = MlRiskService()
        self._metrics_service = MlMetricsService()

    def run(self, config: WalkForwardConfig) -> dict[str, Any]:
        """Execute a full walk-forward backtest and persist all results.

        Args:
            config: Walk-forward configuration including date ranges and risk parameters.

        Returns:
            Summary dict with backtest_run_id, aggregate metrics, and fold breakdown.
        """
        folds = self._build_fold_windows(config)
        if not folds:
            raise ValueError('No walk-forward folds could be constructed from the given date range and window sizes')

        logger.info(
            'Backtest starting name={} folds={} model_type={} date_range={}/{} train_window={} test_window={} step={} top_n={}',
            config.backtest_name,
            len(folds),
            config.model_type,
            config.total_start_date,
            config.total_end_date,
            config.train_window_days,
            config.test_window_days,
            config.step_days,
            config.top_n_per_direction,
        )

        run_id = self._create_backtest_run(config, len(folds))
        all_fold_metrics: list[dict[str, float]] = []

        try:
            for fold_def in folds:
                fold_index, train_start, train_end, test_start, test_end = fold_def
                logger.info('Fold {} train={}/{} test={}/{}', fold_index, train_start, train_end, test_start, test_end)
                fold_start = perf_counter()

                fold_result = self._run_fold(
                    config=config,
                    fold_index=fold_index,
                    train_start=train_start,
                    train_end=train_end,
                    test_start=test_start,
                    test_end=test_end,
                )
                if fold_result.fold_metrics:
                    all_fold_metrics.append(fold_result.fold_metrics)
                self._persist_fold(run_id, fold_result)
                logger.info(
                    'Fold {} complete runtime_s={} predictions={} closed_trades={} daily_points={} sharpe={} return_pct={}',
                    fold_index,
                    round(perf_counter() - fold_start, 2),
                    len(fold_result.predictions),
                    len(fold_result.closed_trades),
                    len(fold_result.daily_portfolio),
                    round(fold_result.fold_metrics.get('sharpe_ratio', 0), 4),
                    round(fold_result.fold_metrics.get('total_return_pct', 0), 4),
                )
        except Exception:
            self._mark_run_failed(run_id)
            raise

        aggregated = self._metrics_service.aggregate_fold_metrics(all_fold_metrics)
        self._update_backtest_run(run_id, aggregated, all_fold_metrics, config)

        logger.info('Backtest complete run_id={} sharpe={} total_return={}%',
                    run_id,
                    round(aggregated.get('sharpe_ratio', 0), 3),
                    round(aggregated.get('total_return_pct', 0), 2))

        return {
            'success': True,
            'backtest_run_id': run_id,
            'backtest_name': config.backtest_name,
            'total_folds': len(folds),
            'aggregate_metrics': aggregated,
            'fold_metrics': all_fold_metrics,
        }

    # ── Fold Construction ──────────────────────────────────────────────────────

    def _build_fold_windows(
        self, config: WalkForwardConfig
    ) -> list[tuple[int, date, date, date, date]]:
        """Generate rolling fold windows from the config date range.

        Args:
            config: Walk-forward configuration.

        Returns:
            List of (fold_index, train_start, train_end, test_start, test_end) tuples.
        """
        folds: list[tuple[int, date, date, date, date]] = []
        fold_index = 0
        test_start = config.total_start_date + timedelta(days=config.train_window_days)

        while test_start + timedelta(days=config.test_window_days - 1) <= config.total_end_date:
            train_start = test_start - timedelta(days=config.train_window_days)
            train_end = test_start - timedelta(days=1)
            test_end = test_start + timedelta(days=config.test_window_days - 1)
            folds.append((fold_index, train_start, train_end, test_start, test_end))
            fold_index += 1
            test_start += timedelta(days=config.step_days)

        return folds

    # ── Single Fold Execution ──────────────────────────────────────────────────

    def _run_fold(
        self,
        config: WalkForwardConfig,
        fold_index: int,
        train_start: date,
        train_end: date,
        test_start: date,
        test_end: date,
    ) -> FoldResult:
        """Train a model on the training window and simulate trades in the test window.

        Args:
            config: Walk-forward configuration.
            fold_index: Zero-based fold number for logging.
            train_start: Start of training window (inclusive).
            train_end: End of training window (inclusive).
            test_start: Start of test window (inclusive).
            test_end: End of test window (inclusive).

        Returns:
            FoldResult with trades, predictions, daily portfolio values, and metrics.
        """
        result = FoldResult(
            fold_index=fold_index,
            train_start=train_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
        )

        dataset = self._dataset_service.build_training_dataset(
            horizon_days=config.horizon_days,
            threshold_pct=config.threshold_pct,
            train_start_date=train_start,
            train_end_date=train_end,
        )
        logger.info('Fold {} dataset built records={} features={}', fold_index, len(dataset.records), len(dataset.feature_keys))
        if len(dataset.records) < 300:
            logger.warning('Fold {} skipped — insufficient training records: {}', fold_index, len(dataset.records))
            return result

        train_start_ts = perf_counter()
        trained = self._model_service.train(
            run_date=train_end,
            records=dataset.records,
            feature_keys=dataset.feature_keys,
            model_type=config.model_type,
        )
        logger.info(
            'Fold {} model trained runtime_s={} model_type={} long_path={} short_path={}',
            fold_index,
            round(perf_counter() - train_start_ts, 2),
            config.model_type,
            trained.long_model_path,
            trained.short_model_path,
        )
        result.model_long_path = trained.long_model_path
        result.model_short_path = trained.short_model_path

        # Simulate day-by-day through the test window
        test_dates = self._trading_dates_in_range(test_start, test_end)
        preloaded_daily_rows = self._dataset_service.preload_daily_rows_for_inference()
        open_positions: list[dict[str, Any]] = []
        closed_trades: list[dict[str, Any]] = []
        cash_balance = config.risk.portfolio_value
        committed_capital = 0.0  # Capital currently tied up in open positions
        daily_portfolio: list[dict[str, Any]] = []
        prev_portfolio_value = config.risk.portfolio_value
        latest_prices: dict[int, float] = {}
        latest_price_dates: dict[int, date] = {}
        simulation_stats: dict[str, int] = {
            'signals_scored': 0,
            'accepted_entries': 0,
            'rejected_no_price': 0,
            'rejected_low_confidence': 0,
            'rejected_capacity': 0,
            'rejected_insufficient_capital': 0,
            'rejected_conflict': 0,
            'days_with_no_candidates': 0,
        }
        logger.info('Fold {} simulation starting trading_days={}', fold_index, len(test_dates))

        for day_index, current_date in enumerate(test_dates, start=1):
            prices = self._prices_on_date(current_date)
            for security_id, price in prices.items():
                if price > 0:
                    latest_prices[security_id] = price
                    latest_price_dates[security_id] = current_date

            # Exit check on existing open positions
            still_open: list[dict[str, Any]] = []
            for pos in open_positions:
                sid = pos['security_id']
                current_price = prices.get(sid, 0.0)
                if current_price <= 0:
                    still_open.append(pos)
                    continue

                days_held = (current_date - pos['entry_date']).days
                exit_reason = self._risk_service.apply_exit_rules(
                    entry_price=pos['entry_price'],
                    current_price=current_price,
                    stop_loss_price=pos['stop_loss_price'],
                    take_profit_price=pos['take_profit_price'],
                    direction=pos['direction'],
                    days_held=days_held,
                    horizon_days=config.horizon_days,
                )

                if exit_reason:
                    pnl_pct = self._risk_service.compute_realized_pnl_pct(
                        entry_price=pos['entry_price'],
                        exit_price=current_price,
                        direction=pos['direction'],
                        commission_pct=config.risk.commission_pct,
                    )
                    pnl_inr = pos['position_size_inr'] * (pnl_pct / 100.0)
                    cash_balance += pos['position_size_inr'] + pnl_inr
                    committed_capital = max(0.0, committed_capital - pos['position_size_inr'])

                    closed_trades.append({**pos, 'exit_date': current_date, 'exit_price': current_price,
                                          'exit_reason': exit_reason, 'realized_pnl_pct': pnl_pct, 'realized_pnl_inr': pnl_inr})
                else:
                    still_open.append(pos)

            open_positions = still_open

            # Generate new signals for this date
            inference_dataset = self._dataset_service.build_inference_dataset_from_preloaded_daily(
                daily_rows_by_security=preloaded_daily_rows,
                as_of_date=current_date,
            )
            fresh_records = [record for record in inference_dataset.records if record['prediction_date'] == current_date]
            available_capital = max(0.0, cash_balance)
            if fresh_records:
                security_direction_map = {
                    int(position['security_id']): str(position['direction'])
                    for position in open_positions
                }
                entered_today: set[int] = set()

                for direction in ('long', 'short'):
                    model_path = result.model_long_path if direction == 'long' else result.model_short_path
                    signals = self._model_service.score_direction(
                        records=fresh_records,
                        feature_keys=inference_dataset.feature_keys,
                        model_path=model_path,
                        direction=direction,
                        top_n=config.top_n_per_direction,
                    )
                    simulation_stats['signals_scored'] += len(signals)
                    top_signals = [s for s in signals if s['rank'] is not None]
                    # Pass available_capital as portfolio_value so sizer respects remaining cash
                    available_params = RiskParameters(
                        portfolio_value=available_capital,
                        max_position_pct=config.risk.max_position_pct,
                        max_open_positions=config.risk.max_open_positions,
                        stop_loss_pct=config.risk.stop_loss_pct,
                        take_profit_pct=config.risk.take_profit_pct,
                        min_confidence=config.risk.min_confidence,
                        commission_pct=config.risk.commission_pct,
                    )
                    sized = self._risk_service.size_positions(
                        signals=top_signals,
                        prices=prices,
                        params=available_params,
                        open_position_count=len(open_positions),
                    )
                    for pos in sized:
                        if pos.accepted:
                            existing_direction = security_direction_map.get(pos.security_id)
                            if existing_direction is not None:
                                simulation_stats['rejected_conflict'] += 1
                                continue
                            if pos.security_id in entered_today:
                                simulation_stats['rejected_conflict'] += 1
                                continue

                            open_positions.append({
                                'security_id': pos.security_id,
                                'ticker': pos.ticker,
                                'direction': pos.direction,
                                'confidence': pos.confidence,
                                'entry_date': current_date,
                                'entry_price': pos.entry_price,
                                'stop_loss_price': pos.stop_loss_price,
                                'take_profit_price': pos.take_profit_price,
                                'position_size_inr': pos.position_size_inr,
                                'shares': pos.shares,
                            })
                            security_direction_map[pos.security_id] = pos.direction
                            entered_today.add(pos.security_id)
                            cash_balance -= pos.position_size_inr
                            committed_capital += pos.position_size_inr
                            available_capital -= pos.position_size_inr
                            simulation_stats['accepted_entries'] += 1
                        else:
                            reason = pos.reject_reason
                            if reason == 'no_price':
                                simulation_stats['rejected_no_price'] += 1
                            elif reason == 'low_confidence':
                                simulation_stats['rejected_low_confidence'] += 1
                            elif reason == 'capacity':
                                simulation_stats['rejected_capacity'] += 1
                            elif reason == 'insufficient_capital':
                                simulation_stats['rejected_insufficient_capital'] += 1

                    result.predictions.extend([
                        {**s, 'prediction_date': current_date}
                        for s in signals
                    ])
            else:
                simulation_stats['days_with_no_candidates'] += 1

            equity_value = self._mark_to_market_equity(cash_balance, open_positions, prices)
            start_value = config.risk.portfolio_value if not daily_portfolio else daily_portfolio[0]['portfolio_value']
            daily_return_pct = round(((equity_value - prev_portfolio_value) / prev_portfolio_value) * 100.0, 4) if prev_portfolio_value > 0 else 0.0
            peak = max((d['portfolio_value'] for d in daily_portfolio), default=equity_value)
            max_dd_to_date = round(((peak - equity_value) / peak) * 100.0, 4) if peak > 0 else 0.0
            prev_portfolio_value = equity_value

            daily_portfolio.append({
                'date': current_date,
                'portfolio_value': round(equity_value, 2),
                'cumulative_return_pct': round(((equity_value - start_value) / start_value) * 100.0, 4) if start_value > 0 else 0.0,
                'daily_return_pct': daily_return_pct,
                'max_drawdown_to_date_pct': max_dd_to_date,
                'open_positions': len(open_positions),
                'closed_positions': len(closed_trades),
            })

            if day_index % 10 == 0 or day_index == len(test_dates):
                logger.info(
                    'Fold {} progress day={}/{} date={} open_positions={} closed_trades={} portfolio_value={} committed_capital={}',
                    fold_index,
                    day_index,
                    len(test_dates),
                    current_date,
                    len(open_positions),
                    len(closed_trades),
                    round(equity_value, 2),
                    round(committed_capital, 2),
                )

        # Ensure fold metrics include liquidation of all remaining open positions.
        unmatched_positions: list[dict[str, Any]] = []
        for pos in open_positions:
            security_id = int(pos['security_id'])
            final_price = latest_prices.get(security_id)
            final_date = latest_price_dates.get(security_id)
            if final_price is None or final_date is None:
                unmatched_positions.append(pos)
                continue

            pnl_pct = self._risk_service.compute_realized_pnl_pct(
                entry_price=pos['entry_price'],
                exit_price=final_price,
                direction=pos['direction'],
                commission_pct=config.risk.commission_pct,
            )
            pnl_inr = pos['position_size_inr'] * (pnl_pct / 100.0)
            cash_balance += pos['position_size_inr'] + pnl_inr
            committed_capital = max(0.0, committed_capital - pos['position_size_inr'])
            closed_trades.append(
                {
                    **pos,
                    'exit_date': final_date,
                    'exit_price': final_price,
                    'exit_reason': 'fold_end',
                    'realized_pnl_pct': pnl_pct,
                    'realized_pnl_inr': pnl_inr,
                }
            )

        open_positions = unmatched_positions

        if daily_portfolio:
            final_prices = {int(pos['security_id']): float(latest_prices.get(int(pos['security_id']), 0.0)) for pos in open_positions}
            final_equity = round(self._mark_to_market_equity(cash_balance, open_positions, final_prices), 2)
            if len(daily_portfolio) > 1:
                prev_equity = float(daily_portfolio[-2]['portfolio_value'])
            else:
                prev_equity = float(config.risk.portfolio_value)

            start_equity = float(daily_portfolio[0]['portfolio_value']) if daily_portfolio else float(config.risk.portfolio_value)
            daily_return_pct = round(((final_equity - prev_equity) / prev_equity) * 100.0, 4) if prev_equity > 0 else 0.0
            peak = max((float(d['portfolio_value']) for d in daily_portfolio[:-1]), default=final_equity)
            max_dd_to_date = round(((peak - final_equity) / peak) * 100.0, 4) if peak > 0 else 0.0

            daily_portfolio[-1] = {
                'date': daily_portfolio[-1]['date'],
                'portfolio_value': final_equity,
                'cumulative_return_pct': round(((final_equity - start_equity) / start_equity) * 100.0, 4) if start_equity > 0 else 0.0,
                'daily_return_pct': daily_return_pct,
                'max_drawdown_to_date_pct': max_dd_to_date,
                'open_positions': len(open_positions),
                'closed_positions': len(closed_trades),
            }

            if open_positions:
                logger.warning('Fold {} ended with {} unmatched open positions due to missing terminal prices', fold_index, len(open_positions))

        result.closed_trades = closed_trades
        result.open_positions_end = open_positions
        result.daily_portfolio = daily_portfolio

        daily_values = [d['portfolio_value'] for d in daily_portfolio]
        result.fold_metrics = self._metrics_service.compute_fold_metrics(
            closed_trades=closed_trades,
            daily_portfolio_values=daily_values,
        )
        result.fold_metrics['fold_index'] = float(fold_index)
        result.fold_metrics.update({key: float(value) for key, value in simulation_stats.items()})
        if simulation_stats['accepted_entries'] == 0 and len(test_dates) > 0:
            logger.warning(
                'Fold {} generated zero entries. diagnostics={} test_dates={} closed_trades={}',
                fold_index,
                simulation_stats,
                len(test_dates),
                len(closed_trades),
            )
        return result

    def _mark_to_market_equity(
        self,
        cash_balance: float,
        open_positions: list[dict[str, Any]],
        prices: dict[int, float],
    ) -> float:
        """Compute total equity as cash plus reserved capital and unrealized P&L."""
        equity_value = cash_balance
        for position in open_positions:
            security_id = int(position['security_id'])
            current_price = float(prices.get(security_id, 0.0))
            position_size = float(position['position_size_inr'])
            if current_price <= 0:
                equity_value += position_size
                continue

            entry_price = float(position['entry_price'])
            if entry_price <= 0:
                equity_value += position_size
                continue

            if str(position['direction']) == 'long':
                unrealized_pnl_inr = position_size * ((current_price - entry_price) / entry_price)
            else:
                unrealized_pnl_inr = position_size * ((entry_price - current_price) / entry_price)

            equity_value += position_size + unrealized_pnl_inr

        return equity_value

    # ── Database helpers ───────────────────────────────────────────────────────

    def _create_backtest_run(self, config: WalkForwardConfig, total_folds: int) -> int:
        """Insert a BacktestRun row and return its id.

        Args:
            config: Walk-forward configuration.
            total_folds: Number of folds planned for this run.

        Returns:
            Primary key of the newly inserted BacktestRun row.

        Raises:
            ValueError: If a backtest with the same name already exists.
        """
        with self._session_factory() as session:
            existing = session.execute(
                select(BacktestRun.id).where(BacktestRun.backtest_name == config.backtest_name)
            ).scalar_one_or_none()
            if existing is not None:
                raise ValueError(f'Backtest with name "{config.backtest_name}" already exists (id={existing}). Use a unique name.')

            run = BacktestRun(
                backtest_name=config.backtest_name,
                status='running',
                train_start_date=config.total_start_date,
                train_end_date=config.total_end_date - timedelta(days=config.test_window_days),
                test_start_date=config.total_start_date + timedelta(days=config.train_window_days),
                test_end_date=config.total_end_date,
                strategy_version=config.model_type,
                use_enhanced_features=True,
                use_ensemble=(config.model_type == 'ensemble'),
                total_folds=total_folds,
                train_window_days=config.train_window_days,
                test_window_days=config.test_window_days,
                notes=config.notes,
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            return int(run.id)

    def _persist_fold(self, run_id: int, fold: FoldResult) -> None:
        """Persist predictions, positions, and daily metrics for one completed fold.

        Args:
            run_id: BacktestRun primary key.
            fold: Completed fold result.
        """
        with self._session_factory() as session:
            for pred in fold.predictions:
                session.add(BacktestPrediction(
                    backtest_run_id=run_id,
                    security_id=int(pred['security_id']),
                    ticker=str(pred['ticker']),
                    prediction_date=pred['prediction_date'],
                    direction=str(pred['direction']),
                    predicted_confidence=Decimal(str(round(float(pred['confidence']), 6))),
                    predicted_rank=pred.get('rank'),
                    top_features=pred.get('top_features', []),
                ))

            for trade in fold.closed_trades:
                session.add(BacktestPosition(
                    backtest_run_id=run_id,
                    security_id=int(trade['security_id']),
                    ticker=str(trade['ticker']),
                    direction=str(trade['direction']),
                    confidence=Decimal(str(round(float(trade['confidence']), 6))),
                    entry_date=trade['entry_date'],
                    entry_price=Decimal(str(round(float(trade['entry_price']), 4))),
                    position_size=Decimal(str(round(float(trade['position_size_inr']), 2))),
                    stop_loss_price=Decimal(str(round(float(trade['stop_loss_price']), 4))),
                    take_profit_price=Decimal(str(round(float(trade['take_profit_price']), 4))),
                    exit_date=trade.get('exit_date'),
                    exit_price=Decimal(str(round(float(trade['exit_price']), 4))) if trade.get('exit_price') else None,
                    exit_reason=trade.get('exit_reason'),
                    realized_pnl=Decimal(str(round(float(trade.get('realized_pnl_inr', 0)), 4))),
                    realized_pnl_pct=Decimal(str(round(float(trade.get('realized_pnl_pct', 0)), 4))),
                    hit=float(trade.get('realized_pnl_pct', 0)) > 0,
                ))

            for open_position in fold.open_positions_end:
                session.add(BacktestPosition(
                    backtest_run_id=run_id,
                    security_id=int(open_position['security_id']),
                    ticker=str(open_position['ticker']),
                    direction=str(open_position['direction']),
                    confidence=Decimal(str(round(float(open_position['confidence']), 6))),
                    entry_date=open_position['entry_date'],
                    entry_price=Decimal(str(round(float(open_position['entry_price']), 4))),
                    position_size=Decimal(str(round(float(open_position['position_size_inr']), 2))),
                    stop_loss_price=Decimal(str(round(float(open_position['stop_loss_price']), 4))),
                    take_profit_price=Decimal(str(round(float(open_position['take_profit_price']), 4))),
                    exit_date=None,
                    exit_price=None,
                    exit_reason='fold_end_unpriced',
                    realized_pnl=Decimal('0'),
                    realized_pnl_pct=Decimal('0'),
                    hit=None,
                ))

            for day in fold.daily_portfolio:
                session.add(BacktestDailyMetrics(
                    backtest_run_id=run_id,
                    metric_date=day['date'],
                    portfolio_value=Decimal(str(day['portfolio_value'])),
                    cumulative_return_pct=Decimal(str(day['cumulative_return_pct'])),
                    daily_return_pct=Decimal(str(day['daily_return_pct'])),
                    max_drawdown_to_date_pct=Decimal(str(day['max_drawdown_to_date_pct'])),
                    open_positions_count=int(day['open_positions']),
                    closed_positions_count=int(day['closed_positions']),
                ))

            session.commit()
            logger.info(
                'Persisted fold {} for run_id={} predictions={} closed_positions={} open_positions={} daily_metrics={}',
                fold.fold_index,
                run_id,
                len(fold.predictions),
                len(fold.closed_trades),
                len(fold.open_positions_end),
                len(fold.daily_portfolio),
            )

    def _update_backtest_run(
        self,
        run_id: int,
        aggregated: dict[str, float],
        fold_metrics_list: list[dict[str, float]],
        config: WalkForwardConfig,
    ) -> None:
        """Update BacktestRun aggregate metrics after all folds complete.

        Args:
            run_id: BacktestRun primary key.
            aggregated: Averaged metrics across all folds.
            fold_metrics_list: Per-fold metric dicts for the fold_metrics JSON column.
            config: Walk-forward config (for cross-referencing strategy details).
        """
        with self._session_factory() as session:
            run = session.get(BacktestRun, run_id)
            if run is None:
                return

            run.status = 'completed'
            run.sharpe_ratio = Decimal(str(round(aggregated.get('sharpe_ratio', 0), 4)))
            run.max_drawdown_pct = Decimal(str(round(aggregated.get('max_drawdown_pct', 0), 4)))
            run.total_return_pct = Decimal(str(round(aggregated.get('total_return_pct', 0), 4)))
            run.win_rate_pct = Decimal(str(round(aggregated.get('win_rate_pct', 0), 4)))
            run.long_accuracy_pct = Decimal(str(round(aggregated.get('long_accuracy', 0), 4)))
            run.short_accuracy_pct = Decimal(str(round(aggregated.get('short_accuracy', 0), 4)))
            run.avg_trade_return_pct = Decimal(str(round(aggregated.get('avg_pnl_pct', 0), 4)))
            run.total_trades_simulated = int(aggregated.get('total_trades', 0))
            run.winning_trades = int(aggregated.get('winning_trades', 0))
            run.losing_trades = int(aggregated.get('losing_trades', 0))
            run.total_predictions = sum(int(f.get('total_trades', 0)) for f in fold_metrics_list)
            run.fold_metrics = fold_metrics_list

            session.commit()

    def _mark_run_failed(self, run_id: int) -> None:
        """Set a BacktestRun status to 'failed' on unexpected error.

        Args:
            run_id: BacktestRun primary key.
        """
        try:
            with self._session_factory() as session:
                run = session.get(BacktestRun, run_id)
                if run is not None:
                    run.status = 'failed'
                    session.commit()
                    logger.error('Backtest run marked failed run_id={}', run_id)
        except Exception:
            pass  # Best-effort — do not mask the original exception

    # ── Market Data Helpers ────────────────────────────────────────────────────

    def _prices_on_date(self, target_date: date) -> dict[int, float]:
        """Fetch close prices for all active EQ securities on a given date.

        Args:
            target_date: The trading date to fetch prices for.

        Returns:
            Dict mapping security_id → close price.
        """
        with self._session_factory() as session:
            rows = session.execute(
                select(Ohlcv.security_id, Ohlcv.close)
                .where(Ohlcv.candle_date == target_date)
                .where(Ohlcv.timeframe == '1DAY')
            ).all()
            return {int(r.security_id): float(r.close) for r in rows}

    def _trading_dates_in_range(self, start: date, end: date) -> list[date]:
        """Return all calendar dates in [start, end] that have 1DAY OHLCV data.

        Args:
            start: Start date (inclusive).
            end: End date (inclusive).

        Returns:
            Sorted list of dates where at least one security has a 1DAY candle.
        """
        with self._session_factory() as session:
            rows = session.execute(
                select(Ohlcv.candle_date)
                .where(Ohlcv.candle_date >= start)
                .where(Ohlcv.candle_date <= end)
                .where(Ohlcv.timeframe == '1DAY')
                .distinct()
                .order_by(Ohlcv.candle_date)
            ).scalars().all()
            return list(rows)
