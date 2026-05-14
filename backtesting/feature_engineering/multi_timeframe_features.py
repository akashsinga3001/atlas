"""Cross-timeframe alignment and agreement features."""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtesting.config import WindowConfig
from backtesting.feature_engineering.utils import safe_divide


def generate_multi_timeframe_features(dataframe: pd.DataFrame, windows: WindowConfig) -> pd.DataFrame:
    """Generate daily-weekly-monthly agreement and confirmation features."""
    frame = dataframe.copy()
    frame = frame.sort_values(['security_id', 'candle_date']).reset_index(drop=True)

    required_columns = {'w_close', 'm_close'}
    missing = sorted([column for column in required_columns if column not in frame.columns])
    if missing:
        raise ValueError(f'Missing columns for multi-timeframe features: {missing}')

    grouped = frame.groupby('security_id', group_keys=False)

    d_momentum = grouped['close'].pct_change(windows.short)
    w_momentum = grouped['w_close'].pct_change(windows.short)
    m_momentum = grouped['m_close'].pct_change(windows.short)

    d_trend = np.sign(grouped['close'].pct_change(windows.medium))
    w_trend = np.sign(grouped['w_close'].pct_change(windows.medium))
    m_trend = np.sign(grouped['m_close'].pct_change(windows.medium))

    frame['trend_alignment_score'] = (
        (d_trend == w_trend).astype(float) + (d_trend == m_trend).astype(float) + (w_trend == m_trend).astype(float)
    ) / 3.0

    frame['timeframe_agreement_score'] = (
        np.sign(d_momentum) == np.sign(w_momentum)
    ).astype(float) * 0.5 + (
        np.sign(d_momentum) == np.sign(m_momentum)
    ).astype(float) * 0.5

    frame['higher_timeframe_momentum_confirmation'] = (
        (w_momentum > 0).astype(float) + (m_momentum > 0).astype(float)
    ) / 2.0

    w_prior_high = grouped['w_high'].transform(
        lambda series: series.shift(1).rolling(windows.medium, min_periods=windows.medium).max()
    )
    frame['weekly_breakout_confirmation'] = (frame['w_close'] > w_prior_high).astype(float)

    m_sma_long = grouped['m_close'].transform(
        lambda series: series.rolling(windows.long, min_periods=windows.long).mean()
    )
    frame['monthly_trend_direction'] = np.sign(frame['m_close'] - m_sma_long)

    frame['daily_vs_weekly_distance'] = safe_divide(frame['close'] - frame['w_close'], frame['w_close'])
    frame['daily_vs_monthly_distance'] = safe_divide(frame['close'] - frame['m_close'], frame['m_close'])

    return frame
