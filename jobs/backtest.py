"""Celery tasks for strategy backtesting."""

from datetime import date
from decimal import Decimal
from typing import Any

from celery_app import celery_app
from config import settings
from utils.logger import logger


def _to_date(value: str | None) -> date | None:
    """Parse ISO date string to date for task execution."""
    if value is None:
        return None
    return date.fromisoformat(value)


def _to_decimal(value: str | int | float | Decimal) -> Decimal:
    """Normalize numeric input to Decimal for deterministic math."""
    return Decimal(str(value))


def _validate_non_negative(name: str, value: Decimal) -> None:
    """Reject negative values for trading cost inputs."""
    if value < 0:
        raise ValueError(f'{name} must be >= 0')


@celery_app.task(name='jobs.backtest.daily_backtest', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=240, retry_jitter=True, retry_kwargs={'max_retries': 2})
def daily_backtest(
    self,
    strategy_name: str = 'sma_crossover',
    strategy_params: dict | None = None,
    timeframe: str = '1DAY',
    start_date: str | None = None,
    end_date: str | None = None,
    tickers: list[str] | None = None,
    initial_capital: str = '100000',
    transaction_cost_bps: str = '5',
    slippage_bps: str = '2',
    allow_short: bool = True,
) -> dict:
    """Run scheduled strategy backtest with persistent run/trade storage."""
    from services.backtest import BacktestService

    logger.info('Starting daily backtest strategy={} timeframe={} allow_short={}', strategy_name, timeframe, allow_short)
    parsed_start = _to_date(start_date)
    parsed_end = _to_date(end_date)
    parsed_initial_capital = _to_decimal(initial_capital)
    parsed_transaction_cost_bps = _to_decimal(transaction_cost_bps)
    parsed_slippage_bps = _to_decimal(slippage_bps)

    _validate_non_negative('initial_capital', parsed_initial_capital)
    _validate_non_negative('transaction_cost_bps', parsed_transaction_cost_bps)
    _validate_non_negative('slippage_bps', parsed_slippage_bps)

    service = BacktestService()
    result = service.run_backtest(
        strategy_name=strategy_name,
        strategy_params=strategy_params,
        timeframe=timeframe,
        start_date=parsed_start,
        end_date=parsed_end,
        tickers=tickers,
        initial_capital=parsed_initial_capital,
        transaction_cost_bps=parsed_transaction_cost_bps,
        slippage_bps=parsed_slippage_bps,
        allow_short=allow_short,
    )
    result['trigger_source'] = 'scheduled'
    return result


@celery_app.task(name='jobs.backtest.on_demand_backtest', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=240, retry_jitter=True, retry_kwargs={'max_retries': 2})
def on_demand_backtest(
    self,
    reason: str = 'manual_run',
    strategy_name: str = 'sma_crossover',
    strategy_params: dict | None = None,
    timeframe: str = '1DAY',
    start_date: str | None = None,
    end_date: str | None = None,
    tickers: list[str] | None = None,
    initial_capital: str = '100000',
    transaction_cost_bps: str = '5',
    slippage_bps: str = '2',
    allow_short: bool = True,
) -> dict:
    """Run on-demand strategy backtest with persistent run/trade storage."""
    from services.backtest import BacktestService

    logger.info(
        'Starting on-demand backtest reason={} strategy={} timeframe={} allow_short={}',
        reason,
        strategy_name,
        timeframe,
        allow_short,
    )

    parsed_start = _to_date(start_date)
    parsed_end = _to_date(end_date)
    parsed_initial_capital = _to_decimal(initial_capital)
    parsed_transaction_cost_bps = _to_decimal(transaction_cost_bps)
    parsed_slippage_bps = _to_decimal(slippage_bps)

    _validate_non_negative('initial_capital', parsed_initial_capital)
    _validate_non_negative('transaction_cost_bps', parsed_transaction_cost_bps)
    _validate_non_negative('slippage_bps', parsed_slippage_bps)

    service = BacktestService()
    result = service.run_backtest(
        strategy_name=strategy_name,
        strategy_params=strategy_params,
        timeframe=timeframe,
        start_date=parsed_start,
        end_date=parsed_end,
        tickers=tickers,
        initial_capital=parsed_initial_capital,
        transaction_cost_bps=parsed_transaction_cost_bps,
        slippage_bps=parsed_slippage_bps,
        allow_short=allow_short,
    )
    result['trigger_source'] = 'on_demand'
    result['reason'] = reason
    return result


# ── ML Walk-Forward Backtest Tasks ────────────────────────────────────────────

@celery_app.task(name='jobs.backtest.run_ml_walk_forward', bind=True)
def run_ml_walk_forward(
    self,
    backtest_name: str,
    total_start_date: str,
    total_end_date: str,
    train_window_days: int = 365,
    test_window_days: int = 90,
    step_days: int = 90,
    model_type: str = 'ensemble',
    top_n_per_direction: int = 4,
    portfolio_value: float = 1_000_000.0,
    max_open_positions: int = 4,
    trailing_stop_pct: float = 0.03,
    min_confidence: float = 0.60,
    commission_pct: float = 0.001,
    notes: str | None = None,
) -> dict:
    """Run a full ML walk-forward backtest and persist all results to the database.

    Args:
        backtest_name: Unique name for this backtest run.
        total_start_date: ISO date string for the overall start (e.g. '2023-01-01').
        total_end_date: ISO date string for the overall end (e.g. '2025-12-31').
        train_window_days: Days in each rolling training window.
        test_window_days: Days in each rolling test window.
        step_days: Days to advance between folds.
        model_type: One of 'rf', 'lgb', 'xgb', or 'ensemble'.
        top_n_per_direction: Max signals per direction per day.
        portfolio_value: Starting portfolio value in INR.
        max_open_positions: Hard cap on simultaneous open positions.
        trailing_stop_pct: Trailing stop distance as fraction of high-water mark (e.g. 0.03).
        min_confidence: Minimum model confidence to enter a trade.
        commission_pct: Round-trip commission fraction.
        notes: Optional notes to store with the backtest run.

    Returns:
        Summary dict with backtest_run_id and aggregate metrics.
    """
    from datetime import date as _date

    from services.ml_backtest import MlBacktestService, WalkForwardConfig
    from services.ml_risk import RiskParameters

    task_id = getattr(getattr(self, 'request', None), 'id', None)
    logger.info(
        'ML walk-forward task starting task_id={} name={} model_type={} date_range={}/{} train_window={} test_window={} step={} top_n={}',
        task_id,
        backtest_name,
        model_type,
        total_start_date,
        total_end_date,
        train_window_days,
        test_window_days,
        step_days,
        top_n_per_direction,
    )

    risk = RiskParameters(
        portfolio_value=portfolio_value,
        max_open_positions=max_open_positions,
        trailing_stop_pct=trailing_stop_pct,
        min_confidence=min_confidence,
        commission_pct=commission_pct,
    )

    config = WalkForwardConfig(
        backtest_name=backtest_name,
        total_start_date=_date.fromisoformat(total_start_date),
        total_end_date=_date.fromisoformat(total_end_date),
        train_window_days=train_window_days,
        test_window_days=test_window_days,
        step_days=step_days,
        horizon_days=int(settings.ML_HORIZON_DAYS),
        threshold_pct=float(settings.ML_MOVE_THRESHOLD_PCT),
        model_type=model_type,
        top_n_per_direction=top_n_per_direction,
        risk=risk,
        notes=notes,
    )

    service = MlBacktestService()
    try:
        result = service.run(config)
    except Exception as exc:
        logger.exception('ML walk-forward task failed task_id={} name={} error={}', task_id, backtest_name, str(exc))
        raise

    result['trigger_source'] = 'celery'
    logger.info(
        'ML walk-forward task completed task_id={} name={} run_id={} folds={} sharpe={} return_pct={}',
        task_id,
        backtest_name,
        result.get('backtest_run_id'),
        result.get('total_folds'),
        round(float(result.get('aggregate_metrics', {}).get('sharpe_ratio', 0.0)), 4),
        round(float(result.get('aggregate_metrics', {}).get('total_return_pct', 0.0)), 4),
    )
    return result

