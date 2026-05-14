"""Relative strength features versus benchmark, sector, and universe."""

from __future__ import annotations

import pandas as pd

from backtesting.config import WindowConfig
from backtesting.feature_engineering.utils import rolling_slope, safe_divide


def generate_relative_strength_features(dataframe: pd.DataFrame, windows: WindowConfig) -> pd.DataFrame:
    """Generate relative strength features from aligned benchmark and sector context."""
    frame = dataframe.copy()
    frame = frame.sort_values(['security_id', 'candle_date']).reset_index(drop=True)

    required_columns = {'benchmark_close', 'sector_close', 'universe_close'}
    missing = sorted([column for column in required_columns if column not in frame.columns])
    if missing:
        raise ValueError(f'Missing columns for relative strength features: {missing}')

    grouped = frame.groupby('security_id', group_keys=False)
    frame['relative_strength_ratio'] = safe_divide(frame['close'], frame['benchmark_close'])

    benchmark_return = frame.groupby('security_id')['benchmark_close'].pct_change()
    stock_return = grouped['close'].pct_change()
    frame['outperformance_score'] = (
        stock_return.groupby(frame['security_id']).transform(
            lambda series: series.rolling(windows.medium, min_periods=windows.medium).sum()
        )
        - benchmark_return.groupby(frame['security_id']).transform(
            lambda series: series.rolling(windows.medium, min_periods=windows.medium).sum()
        )
    )

    frame['rs_slope'] = grouped['relative_strength_ratio'].transform(
        lambda series: rolling_slope(series, windows.short)
    )
    frame['market_alpha_estimate'] = (stock_return - benchmark_return).groupby(frame['security_id']).transform(
        lambda series: series.rolling(windows.medium, min_periods=windows.medium).mean()
    )

    frame['sector_relative_strength_ratio'] = safe_divide(frame['close'], frame['sector_close'])
    frame['universe_relative_strength_ratio'] = safe_divide(frame['close'], frame['universe_close'])

    frame['rolling_rs_percentile'] = frame.groupby('candle_date')['relative_strength_ratio'].rank(pct=True)

    return frame
