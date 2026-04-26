"""Celery tasks for strategy backtesting."""

from datetime import date
from decimal import Decimal
from typing import Any

from celery_app import celery_app
from services.backtest import BacktestService
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
