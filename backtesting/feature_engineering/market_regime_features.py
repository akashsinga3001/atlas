"""Rule-based and optional clustering-based market regime features."""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtesting.config import RegimeConfig
from backtesting.feature_engineering.utils import normalize_zscore, rolling_slope


REGIME_NAME_TO_CODE = {
    'trending': 1,
    'choppy': 2,
    'panic': 3,
    'expansion': 4,
}


def generate_market_regime_features(dataframe: pd.DataFrame, config: RegimeConfig) -> pd.DataFrame:
    """Generate regime features and regime labels from trend/volatility/breadth context."""
    frame = dataframe.copy()
    frame = frame.sort_values(['security_id', 'candle_date']).reset_index(drop=True)

    grouped = frame.groupby('security_id', group_keys=False)
    returns = grouped['close'].pct_change()

    frame['regime_realized_volatility'] = returns.groupby(frame['security_id']).transform(
        lambda series: series.rolling(config.volatility_window, min_periods=config.volatility_window).std(ddof=0)
    )
    frame['regime_volatility_zscore'] = grouped['regime_realized_volatility'].transform(
        lambda series: normalize_zscore(series, config.trend_window)
    )

    frame['regime_trend_strength'] = grouped['close'].transform(
        lambda series: rolling_slope(series, config.trend_window)
    )
    frame['regime_momentum'] = grouped['close'].pct_change(config.breadth_window)

    frame['up_day'] = (returns > 0).astype(float)
    breadth = frame.groupby('candle_date')['up_day'].mean()
    frame = frame.merge(
        breadth.rename('regime_breadth').reset_index(),
        on='candle_date',
        how='left',
        validate='many_to_one',
    )

    is_panic = frame['regime_volatility_zscore'] >= config.panic_vol_zscore
    is_expansion = (
        (frame['regime_momentum'] >= config.expansion_momentum_threshold)
        & (frame['regime_trend_strength'] > 0)
        & (~is_panic)
    )
    is_trending = (
        frame['regime_trend_strength'].abs() >= config.choppy_trend_abs_threshold
    ) & (~is_panic) & (~is_expansion)

    frame['market_regime'] = np.select(
        [is_panic, is_expansion, is_trending],
        ['panic', 'expansion', 'trending'],
        default='choppy',
    )
    frame['market_regime_code'] = frame['market_regime'].map(REGIME_NAME_TO_CODE).astype(float)

    if config.clustering_enabled:
        _add_clustering_regime(frame, config.clustering_regimes)

    frame = frame.drop(columns=['up_day'])
    return frame


def _add_clustering_regime(frame: pd.DataFrame, clusters: int) -> None:
    """Optional k-means regime assignment based on regime feature vectors."""
    try:
        from sklearn.cluster import KMeans
    except Exception:
        frame['cluster_regime'] = np.nan
        return

    columns = ['regime_realized_volatility', 'regime_trend_strength', 'regime_momentum', 'regime_breadth']
    fit_data = frame[columns].replace([np.inf, -np.inf], np.nan).dropna()
    if fit_data.empty:
        frame['cluster_regime'] = np.nan
        return

    kmeans = KMeans(n_clusters=clusters, random_state=42, n_init='auto')
    labels = pd.Series(kmeans.fit_predict(fit_data), index=fit_data.index, dtype=float)
    frame['cluster_regime'] = labels.reindex(frame.index)
