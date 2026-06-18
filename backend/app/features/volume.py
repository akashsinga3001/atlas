# backend/app/features/volume.py

import numpy as np
import pandas as pd


class VolumeFeatures:
    """Class to calculate volume-related features for a given DataFrame of OHLCV data."""

    @classmethod
    def transform(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate volume-related features for the given OHLCV DataFrame.

        Parameters:
            df (pd.DataFrame): Input DataFrame containing OHLCV data.

        Returns:
            pd.DataFrame: DataFrame with volume-related features added.
        """
        df = df.copy()
        df = df.sort_values(by=[ "ticker", "candle_timestamp"])

        df['vol_ma_20'] = df.groupby("ticker")["volume"].transform(lambda x: x.rolling(window=20).mean().fillna(0))
        df['volume_ratio'] = df['volume'] / df['vol_ma_20']
        df['turnover'] = df['volume'] * df['close']
        df['avg_turnover_20'] = df.groupby("ticker")["turnover"].transform(lambda x: x.rolling(window=20).mean().fillna(0))
        df['turnover_acceleration'] = (df['turnover'] / df['avg_turnover_20'].replace(0, np.nan)).fillna(0)

        direction = df.groupby('ticker')['close'].transform(lambda x: x.diff()).fillna(0) > 0
        df['obv'] = (direction.astype(int) * df['volume']).groupby(df['ticker']).cumsum()
        df['volume_acceleration'] = df.groupby('ticker')['volume_ratio'].transform(lambda x: x / x.shift(1).replace(0, np.nan)).fillna(1.0)
        df['volume_trend'] = df.groupby('ticker')['volume'].transform(lambda x: x.pct_change(10)).fillna(0)

        df['__up_vol'] = direction.astype(int) * df['volume']
        df['up_volume_ratio'] = (df.groupby('ticker')['__up_vol'].transform(lambda x: x.rolling(20).sum()) / df.groupby('ticker')['volume'].transform(lambda x: x.rolling(20).sum()).replace(0, np.nan)).fillna(0.5)
        df = df.drop(columns=['__up_vol'])

        return df
