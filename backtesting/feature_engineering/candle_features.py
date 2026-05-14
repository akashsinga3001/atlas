"""Numerical candle-structure features."""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtesting.config import FeatureThresholdConfig, WindowConfig
from backtesting.feature_engineering.utils import safe_divide


def generate_candle_features(
    dataframe: pd.DataFrame,
    windows: WindowConfig,
    thresholds: FeatureThresholdConfig,
) -> pd.DataFrame:
    """Generate numerical candle-structure features using past-only information."""
    frame = dataframe.copy()
    frame = frame.sort_values(['security_id', 'candle_date']).reset_index(drop=True)

    grouped = frame.groupby('security_id', group_keys=False)
    candle_body = (frame['close'] - frame['open']).abs()
    candle_range = (frame['high'] - frame['low']).clip(lower=0)

    frame['candle_body'] = candle_body
    frame['candle_range'] = candle_range
    frame['body_to_range_ratio'] = safe_divide(candle_body, candle_range)
    frame['upper_wick_ratio'] = safe_divide(frame['high'] - frame[['open', 'close']].max(axis=1), candle_range)
    frame['lower_wick_ratio'] = safe_divide(frame[['open', 'close']].min(axis=1) - frame['low'], candle_range)
    frame['close_position_in_range'] = safe_divide(frame['close'] - frame['low'], candle_range)

    prev_close = grouped['close'].shift(1)
    gap_pct = safe_divide(frame['open'] - prev_close, prev_close)
    frame['gap_up_percent'] = np.where(gap_pct > 0, gap_pct, 0.0)
    frame['gap_down_percent'] = np.where(gap_pct < 0, gap_pct.abs(), 0.0)

    rolling_avg_range = grouped['candle_range'].transform(
        lambda series: series.rolling(window=windows.medium, min_periods=windows.medium).mean()
    )
    frame['rolling_avg_candle_range'] = rolling_avg_range
    frame['rolling_candle_tightness'] = 1.0 - safe_divide(
        frame['candle_range'],
        grouped['candle_range'].transform(lambda series: series.rolling(window=windows.medium, min_periods=windows.medium).max()),
    )

    frame['expansion_candle_flag'] = (
        frame['candle_range'] > (rolling_avg_range * thresholds.expansion_range_multiplier)
    ).astype(float)
    frame['contraction_candle_flag'] = (
        frame['candle_range'] < (rolling_avg_range * thresholds.contraction_range_multiplier)
    ).astype(float)

    return frame
