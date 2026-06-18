# backend/app/features/volatility.py

import numpy as np
import pandas as pd


class VolatilityFeatures:
    """Class for calculating volatility-related features for financial time series data."""

    @classmethod
    def transform(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate volatility-related features for the given DataFrame.

        Parameters:
            df (pd.DataFrame): Input DataFrame containing OHLCV data.

        Returns:
            pd.DataFrame: DataFrame with volatility-related features added.
        """
        df = df.copy()
        df = df.sort_values(by=[ "ticker", "candle_timestamp"])

        df['atr_14'] = cls.calculate_atr(df, period=14)
        df['atr_pct'] = df['atr_14'] / df['close']

        df['volatility_20'] = df.groupby("ticker")["close"].transform(lambda x: x.pct_change().rolling(window=20).std())

        df['bb_width'] = cls.calculate_bb_width(df, period=20)
        df['volatility_contraction'] = (df['bb_width'] < df['bb_width'].rolling(50).quantile(0.2))
        df['atr_expansion'] = df.groupby('ticker')['atr_14'].transform(lambda x: x / x.rolling(20).mean()).fillna(1.0)

        # Gap Features
        prev_close = df.groupby("ticker")["close"].transform(lambda x: x.shift(1))
        df['gap'] = ((df['open'] - prev_close) / prev_close.replace(0, np.nan)).abs().fillna(0)
        df['gap_frequency_20'] = df.groupby('ticker')['gap'].transform(lambda x: (x > 0.01).rolling(20).sum()).fillna(0)
        df['avg_gap_size_20'] = df.groupby('ticker')['gap'].transform(lambda x: x.rolling(20).mean()).fillna(0)

        df = df.drop(columns=['gap'])

        return df

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate the Average True Range (ATR) for the given DataFrame.

        Parameters:
            df (pd.DataFrame): Input DataFrame containing OHLCV data.
            period (int): The number of periods to use for ATR calculation.
        Returns:
            pd.Series: A pandas Series containing the ATR values.
        """
        df = df.copy()

        tr1 = df['high'] - df['low']
        prev_close = df.groupby("ticker")["close"].shift(1)
        tr2 = abs(df['high'] - prev_close)
        tr3 = abs(df['low'] - prev_close)
        tr = pd.concat([ tr1, tr2, tr3 ], axis=1).max(axis=1)

        return tr.rolling(window=period).mean().fillna(0)

    @staticmethod
    def calculate_bb_width(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """
        Calculate the Bollinger Bands Width for the given DataFrame.

        Parameters:
            df (pd.DataFrame): Input DataFrame containing OHLCV data.
            period (int): The number of periods to use for Bollinger Bands calculation.
        Returns:
            pd.Series: A pandas Series containing the Bollinger Bands Width values.
        """
        df = df.copy()
        grouped = df.groupby("ticker")

        ma20 = grouped["close"].transform(lambda x: x.rolling(window=period).mean())
        std20 = grouped["close"].transform(lambda x: x.rolling(window=period).std())

        upper = ma20 + (2 * std20)
        lower = ma20 - (2 * std20)
        bb_width = (upper - lower) / ma20

        return bb_width.fillna(0)
