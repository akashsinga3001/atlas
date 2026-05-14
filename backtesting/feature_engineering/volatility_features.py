"""Volatility, squeeze, and range-contraction features."""

from __future__ import annotations

import pandas as pd

from backtesting.config import FeatureThresholdConfig, WindowConfig
from backtesting.feature_engineering.utils import normalize_zscore, safe_divide


def generate_volatility_features(
    dataframe: pd.DataFrame,
    windows: WindowConfig,
    thresholds: FeatureThresholdConfig,
) -> pd.DataFrame:
    """Generate volatility and squeeze features from trailing price history."""
    frame = dataframe.copy()
    frame = frame.sort_values(['security_id', 'candle_date']).reset_index(drop=True)
    if 'candle_range' not in frame.columns:
        frame['candle_range'] = (frame['high'] - frame['low']).clip(lower=0)
    grouped = frame.groupby('security_id', group_keys=False)

    prev_close = grouped['close'].shift(1)
    tr_components = pd.concat(
        [
            (frame['high'] - frame['low']).abs(),
            (frame['high'] - prev_close).abs(),
            (frame['low'] - prev_close).abs(),
        ],
        axis=1,
    )
    frame['atr'] = tr_components.max(axis=1).groupby(frame['security_id']).transform(
        lambda series: series.rolling(windows.medium, min_periods=windows.medium).mean()
    )

    frame['atr_percent'] = safe_divide(frame['atr'], frame['close'])
    atr_long = grouped['atr'].transform(lambda series: series.rolling(windows.long, min_periods=windows.long).mean())
    frame['atr_compression_ratio'] = safe_divide(frame['atr'], atr_long)

    sma = grouped['close'].transform(lambda series: series.rolling(windows.medium, min_periods=windows.medium).mean())
    std = grouped['close'].transform(lambda series: series.rolling(windows.medium, min_periods=windows.medium).std(ddof=0))
    upper = sma + (2.0 * std)
    lower = sma - (2.0 * std)
    frame['bollinger_band_width'] = safe_divide(upper - lower, sma)

    returns = grouped['close'].pct_change()
    frame['rolling_volatility'] = returns.groupby(frame['security_id']).transform(
        lambda series: series.rolling(windows.medium, min_periods=windows.medium).std(ddof=0)
    )
    frame['rolling_standard_deviation'] = grouped['close'].transform(
        lambda series: series.rolling(windows.medium, min_periods=windows.medium).std(ddof=0)
    )

    vol_long = grouped['rolling_volatility'].transform(
        lambda series: series.rolling(windows.long, min_periods=windows.long).mean()
    )
    frame['volatility_contraction_score'] = safe_divide(vol_long - frame['rolling_volatility'], vol_long)
    frame['volatility_expansion_score'] = safe_divide(frame['rolling_volatility'] - vol_long, vol_long)

    min4 = grouped['candle_range'].transform(lambda series: series.rolling(4, min_periods=4).min())
    min7 = grouped['candle_range'].transform(lambda series: series.rolling(7, min_periods=7).min())
    frame['narrow_range_4'] = (frame['candle_range'] <= min4).astype(float)
    frame['narrow_range_7'] = (frame['candle_range'] <= min7).astype(float)

    bb_z = grouped['bollinger_band_width'].transform(lambda series: normalize_zscore(series, windows.long))
    atr_z = grouped['atr_compression_ratio'].transform(lambda series: normalize_zscore(series, windows.long))
    frame['squeeze_detection'] = (
        (frame['atr_compression_ratio'] <= thresholds.atr_compression_threshold)
        & (frame['bollinger_band_width'] <= grouped['bollinger_band_width'].transform(
            lambda series: series.rolling(windows.long, min_periods=windows.long).quantile(0.2)
        ))
    ).astype(float)
    frame['squeeze_score'] = -(bb_z + atr_z)

    return frame
