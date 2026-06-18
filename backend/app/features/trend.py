# backend/app/features/trend.py

import numpy as np
import pandas as pd


class TrendFeatures:
    """Class for calculating trend-related features for financial time series data."""

    @classmethod
    def transform(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate trend-related features for the given DataFrame.

        Parameters:
            df (pd.DataFrame): Input DataFrame containing OHLCV data.

        Returns:
            pd.DataFrame: DataFrame with trend-related features added.
        """

        df = df.copy()
        df = df.sort_values(by=[ "ticker", "candle_timestamp"])

        # EMAs
        df["ema_5"] = cls.calculate_ema(df, period=5)
        df["ema_10"] = cls.calculate_ema(df, period=10)
        df["ema_20"] = cls.calculate_ema(df, period=20)
        df["ema_50"] = cls.calculate_ema(df, period=50)
        df["ema_100"] = cls.calculate_ema(df, period=100)

        # Distances to EMAs
        df["dist_ema_5"] = (df["close"] - df["ema_5"]) / df["ema_5"]
        df["dist_ema_10"] = (df["close"] - df["ema_10"]) / df["ema_10"]
        df["dist_ema_20"] = (df["close"] - df["ema_20"]) / df["ema_20"]
        df["dist_ema_50"] = (df["close"] - df["ema_50"]) / df["ema_50"]

        # Slopes of EMAs
        df['ema20_slope_5'] = df.groupby("ticker")['ema_20'].transform(lambda x: x.pct_change(5))
        df['ema50_slope_5'] = df.groupby("ticker")['ema_50'].transform(lambda x: x.pct_change(5))

        # Other trend features
        df['ema_compression'] = abs(df['ema_20'] - df['ema_50']) / (df['ema_50'])
        df['golden_cross'] = (df['ema_20'] > df['ema_50'])
        df['ema_alignment_score'] = ((df['close'] > df['ema_20']).astype(int) + (df['ema_20'] > df['ema_50']).astype(int) + (df['ema_50'] > df['ema_100']).astype(int))

        rolling_252_low = df.groupby('ticker')['low'].transform(lambda x: x.rolling(252).min())
        rolling_252_high = df.groupby('ticker')['high'].transform(lambda x: x.rolling(252).max())
        above_ema20 = (df['close'] > df['ema_20']).astype(int)
        df['dist_252d_low'] = ((df['close'] - rolling_252_low) / rolling_252_low.replace(0, np.nan)).fillna(0)
        df['dist_252d_high'] = ((df['close'] - rolling_252_high) / rolling_252_high.replace(0, np.nan)).fillna(0)
        df['days_above_ema20'] = above_ema20.groupby(df['ticker']).transform(lambda x: x.rolling(20).sum()).fillna(0)

        # Trend Efficiency: |net 20d return| / sum of 20d absolute returns
        net_ret_20 = df.groupby('ticker')['close'].transform(lambda x: x.pct_change(20).abs())
        path_20 = df.groupby('ticker')['close'].transform(lambda x: x.pct_change().abs().rolling(20).sum())
        df['trend_efficiency'] = (net_ret_20 / path_20.replace(0, np.nan)).fillna(0)

        return df

    @staticmethod
    def calculate_ema(df: pd.DataFrame, period: int = 20, price_col: str = "close") -> pd.Series:
        """
        Calculate the Exponential Moving Average (EMA) for a given period.

        Parameters:
            df (pd.DataFrame): Input DataFrame containing OHLCV data.
            period (int): The period for calculating the EMA. Default is 20.
            price_col (str): The column name for the price data. Default is "close".

        Returns:
            pd.Series: A pandas Series containing the EMA values.
        """
        return df.groupby("ticker")[price_col].transform(lambda x: x.ewm(span=period, adjust=False).mean().fillna(0))
