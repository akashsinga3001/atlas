# backend/app/features/breakout.py

import numpy as np
import pandas as pd


class BreakoutFeatures:
    """Class to calculate breakout features for a given OHLCV DataFrame."""

    @classmethod
    def transform(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate breakout features for the given OHLCV DataFrame.

        Parameters:
        df (pd.DataFrame): DataFrame containing OHLCV data with columns ['open', 'high', 'low', 'close', 'volume'].

        Returns:
        pd.DataFrame: DataFrame with additional breakout feature columns.
        """
        df = df.copy()
        df = df.sort_values(by=[ "ticker", "candle_timestamp"])

        rolling_highs = {}
        for n in [ 20, 50 ]:
            rolling_high = df.groupby('ticker')['high'].transform(lambda x, n=n: x.shift(1).rolling(window=n).max())
            rolling_highs[n] = rolling_high

            df[f'dist_{n}d_high'] = ((df['close'] - rolling_high) / rolling_high.replace(0, np.nan)).fillna(0)
            df[f'new_{n}d_high'] = (df['close'] > rolling_high).astype(int)

        df['breakout_strength_20'] = (df['close'] / rolling_highs[20].replace(0, np.nan) * df['volume_ratio']).fillna(0)
        df['breakout_strength_50'] = (df['close'] / rolling_highs[50].replace(0, np.nan) * df['volume_ratio']).fillna(0)
        df['breakout_volume_ratio'] = np.where(df['new_20d_high'] == 1, df['volume_ratio'], 1.0)

        return df
