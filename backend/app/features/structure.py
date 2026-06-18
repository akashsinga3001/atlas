# backend/app/features/structure.py

import numpy as np
import pandas as pd


class StructureFeatures:
    """Class to compute structure features for a given OHLCV DataFrame."""

    @classmethod
    def transform(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute structure features for the given OHLCV DataFrame.

        Parameters:
        df (pd.DataFrame): Input DataFrame containing OHLCV data.

        Returns:
        pd.DataFrame: DataFrame with computed structure features.
        """
        df = df.copy()
        df = df.sort_values(by=[ "ticker", "candle_timestamp"])

        rolling_high = df.groupby("ticker")["high"].transform(lambda x: x.rolling(window=50).max().fillna(0))
        rolling_low = df.groupby("ticker")["low"].transform(lambda x: x.rolling(window=50).min().fillna(0))
        range_ = df['high'] - df['low']

        df['position_in_range'] = np.where(range_ == 0, np.nan, (df['close'] - df['low']) / range_)
        df['near_breakout'] = df['position_in_range'] >= 0.8
        df['base_tightness'] = np.where(rolling_high == rolling_low, np.nan, (rolling_high - rolling_low) / rolling_low)

        rolling_high_20 = df.groupby("ticker")["high"].transform(lambda x: x.rolling(window=20).max().fillna(0))
        rolling_low_20 = df.groupby("ticker")["low"].transform(lambda x: x.rolling(window=20).min().fillna(0))
        df['base_width'] = ((rolling_high_20 - rolling_low_20) / rolling_low_20.replace(0, np.nan)).fillna(0)

        atr_pct_ma50 = df.groupby("ticker")["atr_pct"].transform(lambda x: x.rolling(window=50).mean().fillna(0))
        df['__is_base'] = (df['atr_pct'] < atr_pct_ma50).astype(int)
        df['base_duration'] = df.groupby('ticker')['__is_base'].transform(lambda x: x.rolling(20).sum()).fillna(0)
        df = df.drop(columns=['__is_base'])

        bb_width_median50 = df.groupby('ticker')['bb_width'].transform(lambda x: x.rolling(50).median())
        df['__is_compressed'] = (df['bb_width'] < bb_width_median50).astype(int)
        df['compression_duration'] = df.groupby('ticker')['__is_compressed'].transform(lambda x: x.rolling(20).sum()).fillna(0)
        df = df.drop(columns=['__is_compressed'])

        bb_width_change = df.groupby('ticker')['bb_width'].transform(lambda x: x.diff())
        df['__bb_contracting'] = (bb_width_change < 0).astype(int)
        df['volatility_contraction_count'] = df.groupby('ticker')['__bb_contracting'].transform(lambda x: x.rolling(20).sum()).fillna(0)
        df = df.drop(columns=['__bb_contracting'])

        df['__is_up'] = (df['close'] > df['open']).astype(int)
        df['up_days_10'] = df.groupby('ticker')['__is_up'].transform(lambda x: x.rolling(10).sum()).fillna(0)
        df['up_days_20'] = df.groupby('ticker')['__is_up'].transform(lambda x: x.rolling(20).sum()).fillna(0)
        df = df.drop(columns=['__is_up'])

        df['strong_close_ratio'] = df.groupby('ticker')['position_in_range'].transform(lambda x: x.rolling(20).mean()).fillna(0)

        body_pct = (df['close'] - df['open']) / df['open'].replace(0, np.nan)
        df['__body_pct_up'] = np.where(df['close'] > df['open'], body_pct, 0.0)
        df['bullish_range_expansion'] = df.groupby('ticker')['__body_pct_up'].transform(lambda x: x.rolling(5).mean()).fillna(0)
        df = df.drop(columns=['__body_pct_up'])

        df['close_near_high'] = df['position_in_range'].fillna(0.5)

        return df
