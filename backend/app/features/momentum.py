# backend/app/features/momentum.py

import numpy as np
import pandas as pd


class MomentumFeatures:
    """Class for calculating momentum-related features for financial time series data."""

    @classmethod
    def transform(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate momentum-related features for the given DataFrame.

        Parameters:
            df (pd.DataFrame): Input DataFrame containing OHLCV data.

        Returns:
            pd.DataFrame: DataFrame with momentum-related features added.
        """
        df = df.copy()
        df = df.sort_values(by=[ "ticker", "candle_timestamp"])

        # Returns
        df["ret_5"] = df.groupby("ticker")["close"].pct_change(periods=5).fillna(0)
        df["ret_10"] = df.groupby("ticker")["close"].pct_change(periods=10).fillna(0)
        df["ret_20"] = df.groupby("ticker")["close"].pct_change(periods=20).fillna(0)
        df["ret_60"] = df.groupby("ticker")["close"].pct_change(periods=60).fillna(0)
        df['rsi_14'] = cls.calculate_rsi(df, period=14)
        df['momentum_acceleration'] = df['ret_5'] - df['ret_20']

        # 6-minus-1 month cross-sectional momentum (relative_leadership_v1's frozen signal).
        # Deliberately NOT .fillna(0) like ret_N above — a security with fewer than 127
        # observations must have no valid momentum value at all, not a fake zero return,
        # so it gets excluded from that day's ranking rather than falsely qualifying.
        recent = df.groupby("ticker")["close"].shift(21)
        lookback = df.groupby("ticker")["close"].shift(126)
        df["mom_6_1"] = recent / lookback - 1

        return df

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate the Relative Strength Index (RSI) for the given DataFrame.

        Parameters:
            df (pd.DataFrame): Input DataFrame containing OHLCV data.
            period (int): The number of periods to use for RSI calculation.

        Returns:
            pd.Series: A pandas Series containing the RSI values.
        """
        delta = df.groupby("ticker")["close"].transform(lambda x: x.diff())
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(0)
