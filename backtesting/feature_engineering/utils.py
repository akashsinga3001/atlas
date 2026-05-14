"""Shared helpers for leakage-safe feature engineering."""

from __future__ import annotations

import numpy as np
import pandas as pd


EPSILON = 1e-12


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Safely divide two vectors while preserving NaN semantics."""
    return numerator / denominator.replace(0, np.nan)


def pct_change_from(series: pd.Series, periods: int) -> pd.Series:
    """Percent change helper with explicit period control."""
    return safe_divide(series - series.shift(periods), series.shift(periods))


def rolling_slope(series: pd.Series, window: int) -> pd.Series:
    """Approximate linear-regression slope on rolling windows."""
    if window < 2:
        return pd.Series(np.nan, index=series.index)

    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    x_demean = x - x_mean
    denom = float((x_demean ** 2).sum())

    def _slope(values: np.ndarray) -> float:
        y = values.astype(float)
        if np.isnan(y).any():
            return np.nan
        y_mean = float(y.mean())
        num = float((x_demean * (y - y_mean)).sum())
        return num / denom if denom > 0 else np.nan

    return series.rolling(window=window, min_periods=window).apply(_slope, raw=True)


def run_length_true(mask: pd.Series) -> pd.Series:
    """Compute consecutive run length for True values."""
    groups = (~mask).cumsum()
    lengths = mask.groupby(groups).cumcount() + 1
    return lengths.where(mask, 0)


def normalize_zscore(series: pd.Series, window: int) -> pd.Series:
    """Rolling z-score with stable denominator handling."""
    mean = series.rolling(window=window, min_periods=window).mean()
    std = series.rolling(window=window, min_periods=window).std(ddof=0)
    return safe_divide(series - mean, std + EPSILON)
