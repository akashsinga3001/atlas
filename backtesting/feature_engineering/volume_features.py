"""Volume participation and accumulation-related features."""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtesting.config import WindowConfig
from backtesting.feature_engineering.utils import rolling_slope, safe_divide


def generate_volume_features(dataframe: pd.DataFrame, windows: WindowConfig) -> pd.DataFrame:
    """Generate volume and price-volume interaction features."""
    frame = dataframe.copy()
    frame = frame.sort_values(['security_id', 'candle_date']).reset_index(drop=True)
    if 'candle_range' not in frame.columns:
        frame['candle_range'] = (frame['high'] - frame['low']).clip(lower=0)
    grouped = frame.groupby('security_id', group_keys=False)

    frame['rolling_average_volume'] = grouped['volume'].transform(
        lambda series: series.rolling(windows.medium, min_periods=windows.medium).mean()
    )
    rolling_volume_long = grouped['volume'].transform(
        lambda series: series.rolling(windows.long, min_periods=windows.long).mean()
    )

    frame['relative_volume'] = safe_divide(frame['volume'], frame['rolling_average_volume'])
    frame['volume_spike_ratio'] = safe_divide(frame['volume'], rolling_volume_long)

    daily_return = grouped['close'].pct_change()
    frame['price_volume_expansion'] = daily_return.abs() * frame['relative_volume']

    range_ratio = safe_divide(frame['candle_range'], grouped['candle_range'].transform(
        lambda series: series.rolling(windows.medium, min_periods=windows.medium).mean()
    ))
    quiet_up_day = ((daily_return > 0) & (range_ratio < 0.9)).astype(float)
    frame['quiet_accumulation_detection'] = quiet_up_day * frame['relative_volume'].clip(lower=0, upper=2)

    breakout_proxy = (frame['close'] > grouped['high'].transform(
        lambda series: series.shift(1).rolling(windows.medium, min_periods=windows.medium).max()
    )).astype(float)
    volume_contraction = 1.0 - frame['relative_volume'].clip(upper=1.0)
    frame['volume_contraction_before_breakout'] = volume_contraction * breakout_proxy

    up_volume = np.where(daily_return > 0, frame['volume'], 0.0)
    down_volume = np.where(daily_return < 0, frame['volume'], 0.0)
    up_rolling = pd.Series(up_volume, index=frame.index).groupby(frame['security_id']).transform(
        lambda series: series.rolling(windows.medium, min_periods=windows.medium).sum()
    )
    down_rolling = pd.Series(down_volume, index=frame.index).groupby(frame['security_id']).transform(
        lambda series: series.rolling(windows.medium, min_periods=windows.medium).sum()
    )
    frame['delivery_style_accumulation_approx'] = safe_divide(up_rolling - down_rolling, up_rolling + down_rolling)

    frame['volume_trend_slope'] = grouped['volume'].transform(
        lambda series: rolling_slope(np.log1p(series), windows.short)
    )

    return frame
