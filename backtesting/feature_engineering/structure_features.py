"""Price-structure and base-formation features."""

from __future__ import annotations

import pandas as pd

from backtesting.config import WindowConfig
from backtesting.feature_engineering.utils import run_length_true, safe_divide


def generate_structure_features(dataframe: pd.DataFrame, windows: WindowConfig) -> pd.DataFrame:
    """Generate structure features describing compression, base, and breakout proximity."""
    frame = dataframe.copy()
    frame = frame.sort_values(['security_id', 'candle_date']).reset_index(drop=True)
    if 'candle_range' not in frame.columns:
        frame['candle_range'] = (frame['high'] - frame['low']).clip(lower=0)
    if 'atr' not in frame.columns:
        frame['atr'] = frame.groupby('security_id', group_keys=False)['candle_range'].transform(
            lambda series: series.rolling(windows.medium, min_periods=windows.medium).mean()
        )
    grouped = frame.groupby('security_id', group_keys=False)

    rolling_52w_high = grouped['high'].transform(
        lambda series: series.rolling(windows.yearly, min_periods=windows.yearly).max()
    )
    rolling_52w_low = grouped['low'].transform(
        lambda series: series.rolling(windows.yearly, min_periods=windows.yearly).min()
    )

    frame['distance_from_52w_high'] = safe_divide(rolling_52w_high - frame['close'], rolling_52w_high)
    frame['distance_from_52w_low'] = safe_divide(frame['close'] - rolling_52w_low, rolling_52w_low)

    rolling_range_median = grouped['candle_range'].transform(
        lambda series: series.rolling(windows.medium, min_periods=windows.medium).median()
    )
    is_consolidating = frame['candle_range'] <= rolling_range_median
    frame['consolidation_length'] = is_consolidating.groupby(frame['security_id']).transform(run_length_true)

    prior_range_high = grouped['high'].transform(
        lambda series: series.shift(1).rolling(windows.long, min_periods=windows.long).max()
    )
    prior_range_low = grouped['low'].transform(
        lambda series: series.shift(1).rolling(windows.long, min_periods=windows.long).min()
    )

    frame['breakout_proximity'] = safe_divide(prior_range_high - frame['close'], prior_range_high)
    frame['support_proximity'] = safe_divide(frame['close'] - prior_range_low, frame['close'])
    frame['resistance_proximity'] = safe_divide(prior_range_high - frame['close'], frame['close'])

    frame['base_tightness'] = safe_divide(
        grouped['close'].transform(lambda series: series.rolling(windows.medium, min_periods=windows.medium).std(ddof=0)),
        grouped['close'].transform(lambda series: series.rolling(windows.medium, min_periods=windows.medium).mean()),
    )
    frame['range_contraction_score'] = 1.0 - safe_divide(
        frame['candle_range'],
        grouped['candle_range'].transform(lambda series: series.rolling(windows.medium, min_periods=windows.medium).max()),
    )

    frame['price_compression_score'] = safe_divide(
        grouped['close'].transform(lambda series: series.rolling(windows.medium, min_periods=windows.medium).std(ddof=0)),
        frame['atr'],
    )

    return frame
