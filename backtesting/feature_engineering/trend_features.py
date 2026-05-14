"""Trend and momentum-oriented numerical features."""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtesting.config import WindowConfig
from backtesting.feature_engineering.utils import pct_change_from, rolling_slope, safe_divide


def generate_trend_features(dataframe: pd.DataFrame, windows: WindowConfig) -> pd.DataFrame:
    """Generate trend features per security using trailing windows only."""
    frame = dataframe.copy()
    frame = frame.sort_values(['security_id', 'candle_date']).reset_index(drop=True)
    grouped = frame.groupby('security_id', group_keys=False)

    frame['sma20'] = grouped['close'].transform(lambda series: series.rolling(windows.medium, min_periods=windows.medium).mean())
    frame['sma50'] = grouped['close'].transform(lambda series: series.rolling(windows.long, min_periods=windows.long).mean())
    frame['sma200'] = grouped['close'].transform(lambda series: series.rolling(windows.very_long, min_periods=windows.very_long).mean())
    frame['ema20'] = grouped['close'].transform(lambda series: series.ewm(span=windows.medium, adjust=False).mean())
    frame['ema50'] = grouped['close'].transform(lambda series: series.ewm(span=windows.long, adjust=False).mean())
    frame['ema200'] = grouped['close'].transform(lambda series: series.ewm(span=windows.very_long, adjust=False).mean())

    frame['sma20_distance_percent'] = safe_divide(frame['close'] - frame['sma20'], frame['sma20'])
    frame['sma50_distance_percent'] = safe_divide(frame['close'] - frame['sma50'], frame['sma50'])
    frame['sma200_distance_percent'] = safe_divide(frame['close'] - frame['sma200'], frame['sma200'])

    bullish_alignment = (
        (frame['close'] > frame['ema20'])
        & (frame['ema20'] > frame['ema50'])
        & (frame['ema50'] > frame['ema200'])
    )
    bearish_alignment = (
        (frame['close'] < frame['ema20'])
        & (frame['ema20'] < frame['ema50'])
        & (frame['ema50'] < frame['ema200'])
    )
    frame['ema_alignment'] = np.select([bullish_alignment, bearish_alignment], [1.0, -1.0], default=0.0)

    frame['sma_slope'] = grouped['sma50'].transform(lambda series: rolling_slope(series, windows.short))
    frame['rolling_return'] = grouped['close'].transform(lambda series: pct_change_from(series, windows.medium))
    frame['rolling_momentum'] = grouped['close'].transform(lambda series: pct_change_from(series, windows.short))

    higher_high = (grouped['high'].shift(0) > grouped['high'].shift(1)).astype(float)
    higher_low = (grouped['low'].shift(0) > grouped['low'].shift(1)).astype(float)
    frame['higher_high_count'] = higher_high.groupby(frame['security_id']).transform(
        lambda series: series.rolling(windows.short, min_periods=windows.short).sum()
    )
    frame['higher_low_count'] = higher_low.groupby(frame['security_id']).transform(
        lambda series: series.rolling(windows.short, min_periods=windows.short).sum()
    )

    frame['trend_persistence_score'] = safe_divide(
        frame['higher_high_count'] + frame['higher_low_count'],
        pd.Series(float(windows.short * 2), index=frame.index),
    )

    rolling_breakout_high = grouped['high'].transform(
        lambda series: series.shift(1).rolling(windows.long, min_periods=windows.long).max()
    )
    frame['breakout_strength'] = safe_divide(frame['close'] - rolling_breakout_high, rolling_breakout_high)

    ma_max = frame[['sma20', 'sma50', 'sma200']].max(axis=1)
    ma_min = frame[['sma20', 'sma50', 'sma200']].min(axis=1)
    frame['moving_average_compression'] = safe_divide(ma_max - ma_min, frame['close'])

    return frame
