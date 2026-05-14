"""Configurable leakage-safe target generation for expansion research."""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtesting.config import TargetConfig
from backtesting.feature_engineering.utils import safe_divide


class TargetGenerator:
    """Generate future expansion targets without contaminating feature columns."""

    def __init__(self, config: TargetConfig) -> None:
        self._config = config

    def generate(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Generate all configured targets and forward-return helper columns."""
        frame = dataframe.copy()
        frame = frame.sort_values(['security_id', 'candle_date']).reset_index(drop=True)
        if 'candle_range' not in frame.columns:
            frame['candle_range'] = (frame['high'] - frame['low']).clip(lower=0)

        for future_target in self._config.future_return_targets:
            frame = self._add_future_return_target(frame, future_target.threshold_pct, future_target.lookahead_days)

        frame = self._add_breakout_target(frame)
        frame = self._add_volatility_expansion_target(frame)
        frame = self._add_momentum_continuation_target(frame)

        return frame

    def _add_future_return_target(self, frame: pd.DataFrame, threshold_pct: float, lookahead_days: int) -> pd.DataFrame:
        threshold = threshold_pct / 100.0
        label_name = f'target_up_{int(threshold_pct)}pct_within_{lookahead_days}d'
        return_name = f'future_return_{lookahead_days}d'

        max_future_high = frame.groupby('security_id', group_keys=False)['high'].transform(
            lambda series: _future_rolling(series, lookahead_days, mode='max')
        )
        frame[return_name] = safe_divide(max_future_high - frame['close'], frame['close'])
        frame[label_name] = (frame[return_name] >= threshold).astype(float)
        return frame

    def _add_breakout_target(self, frame: pd.DataFrame) -> pd.DataFrame:
        cfg = self._config.breakout_target
        rolling_52w_high = frame.groupby('security_id', group_keys=False)['high'].transform(
            lambda series: series.rolling(cfg.yearly_high_window, min_periods=cfg.yearly_high_window).max()
        )

        future_high = frame.groupby('security_id', group_keys=False)['high'].transform(
            lambda series: _future_rolling(series, cfg.lookahead_days, mode='max')
        )
        future_range = frame.groupby('security_id', group_keys=False)['candle_range'].transform(
            lambda series: _future_rolling(series, cfg.lookahead_days, mode='max')
        )

        frame[f'target_future_52w_high_within_{cfg.lookahead_days}d'] = (future_high > rolling_52w_high).astype(float)
        frame[f'target_future_range_expansion_{cfg.lookahead_days}d'] = (
            safe_divide(future_range, frame['candle_range']) >= cfg.expansion_threshold
        ).astype(float)
        return frame

    def _add_volatility_expansion_target(self, frame: pd.DataFrame) -> pd.DataFrame:
        cfg = self._config.volatility_target
        vol_col = f'realized_vol_{cfg.realized_vol_window}d'
        frame[vol_col] = frame.groupby('security_id', group_keys=False)['close'].pct_change().groupby(frame['security_id']).transform(
            lambda series: series.rolling(cfg.realized_vol_window, min_periods=cfg.realized_vol_window).std(ddof=0)
        )

        future_vol = frame.groupby('security_id', group_keys=False)[vol_col].transform(
            lambda series: _future_rolling(series, cfg.lookahead_days, mode='max')
        )
        frame[f'target_volatility_expansion_{cfg.lookahead_days}d'] = (
            safe_divide(future_vol, frame[vol_col]) >= cfg.expansion_threshold
        ).astype(float)
        return frame

    def _add_momentum_continuation_target(self, frame: pd.DataFrame) -> pd.DataFrame:
        cfg = self._config.momentum_target
        min_return = cfg.min_return_pct / 100.0
        max_drawdown = cfg.max_drawdown_pct / 100.0

        future_max_high = frame.groupby('security_id', group_keys=False)['high'].transform(
            lambda series: _future_rolling(series, cfg.lookahead_days, mode='max')
        )
        future_min_low = frame.groupby('security_id', group_keys=False)['low'].transform(
            lambda series: _future_rolling(series, cfg.lookahead_days, mode='min')
        )

        future_upside = safe_divide(future_max_high - frame['close'], frame['close'])
        future_drawdown = safe_divide(future_min_low - frame['close'], frame['close'])

        frame[f'target_momentum_continuation_{cfg.lookahead_days}d'] = (
            (future_upside >= min_return) & (future_drawdown >= max_drawdown)
        ).astype(float)
        return frame


def _future_rolling(series: pd.Series, window: int, mode: str) -> pd.Series:
    """Compute forward rolling aggregates over t+1..t+window."""
    shifted = series.shift(-1)
    reversed_series = shifted.iloc[::-1]

    if mode == 'max':
        rolled = reversed_series.rolling(window=window, min_periods=window).max()
    elif mode == 'min':
        rolled = reversed_series.rolling(window=window, min_periods=window).min()
    else:
        raise ValueError(f'Unsupported mode: {mode}')

    return rolled.iloc[::-1]
