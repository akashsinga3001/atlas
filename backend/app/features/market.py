# backend/app/features/market.py

import numpy as np
import pandas as pd


class MarketFeatures:
    """Class to compute cross-sectional market breadth and sentiment features across all securities."""

    @classmethod
    def transform(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute per-date market breadth features from a multi-ticker OHLCV DataFrame.

        Parameters:
            df (pd.DataFrame): DataFrame with columns ['ticker', 'candle_timestamp', 'close', 'high', 'low'] across many securities.

        Returns:
            pd.DataFrame: One row per candle_timestamp with breadth/regime columns.
        """
        df = df.copy()
        df = df.sort_values(by=[ "ticker", "candle_timestamp"])

        df["ema_20"] = df.groupby("ticker")["close"].transform(lambda x: x.ewm(span=20, adjust=False).mean())
        df["ema_50"] = df.groupby("ticker")["close"].transform(lambda x: x.ewm(span=50, adjust=False).mean())
        df["ema_200"] = df.groupby("ticker")["close"].transform(lambda x: x.ewm(span=200, adjust=False).mean())

        df["rsi_14"] = cls._calculate_rsi(df, period=14)

        rolling_high_252 = df.groupby("ticker")["high"].transform(lambda x: x.shift(1).rolling(window=252).max())
        rolling_low_252 = df.groupby("ticker")["low"].transform(lambda x: x.shift(1).rolling(window=252).min())
        df["new_252d_high"] = df["close"] > rolling_high_252
        df["new_252d_low"] = df["close"] < rolling_low_252

        prev_close = df.groupby("ticker")["close"].shift(1)
        df["advancing"] = df["close"] > prev_close
        df["declining"] = df["close"] < prev_close

        df["above_ema20"] = df["close"] > df["ema_20"]
        df["above_ema50"] = df["close"] > df["ema_50"]
        df["above_ema200"] = df["close"] > df["ema_200"]

        market = df.groupby("candle_timestamp").agg(total=("ticker", "count"), advances=("advancing", "sum"), declines=("declining", "sum"), above_ema20=("above_ema20", "sum"), above_ema50=("above_ema50", "sum"), above_ema200=("above_ema200", "sum"), new_highs_count=("new_252d_high", "sum"), new_lows_count=("new_252d_low", "sum"), avg_rsi=("rsi_14", "mean"), ).reset_index()

        market = market.sort_values("candle_timestamp")

        market["advance_decline_ratio"] = np.where(market["declines"] > 0, market["advances"] / market["declines"], market["advances"].astype(float))
        market["pct_above_ema20"] = (market["above_ema20"] / market["total"] * 100).fillna(0)
        market["pct_above_ema50"] = (market["above_ema50"] / market["total"] * 100).fillna(0)
        market["pct_above_ema200"] = (market["above_ema200"] / market["total"] * 100).fillna(0)

        net_advance_pct = ((market["advances"] - market["declines"]) / market["total"].replace(0, np.nan) * 100).fillna(0)
        market["market_breadth_ema20"] = net_advance_pct.ewm(span=20, adjust=False).mean()
        market["market_breadth_ema50"] = net_advance_pct.ewm(span=50, adjust=False).mean()

        ad_score = (market["advances"] / market["total"] * 100).fillna(0)
        hl_total = market["new_highs_count"] + market["new_lows_count"]
        hl_score = np.where(hl_total > 0, market["new_highs_count"] / hl_total * 100, 50.0)

        market["regime_score"] = (market["pct_above_ema20"] * 0.25 + market["pct_above_ema50"] * 0.25 + ad_score * 0.25 + market["avg_rsi"].fillna(50) * 0.15 + hl_score * 0.10)

        return market[[ "candle_timestamp", "advance_decline_ratio", "market_breadth_ema20", "market_breadth_ema50", "pct_above_ema20", "pct_above_ema50", "pct_above_ema200", "new_highs_count", "new_lows_count", "regime_score"]]

    @staticmethod
    def _calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate per-ticker RSI on a multi-ticker DataFrame."""
        delta = df.groupby("ticker")["close"].transform(lambda x: x.diff())
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.groupby(df["ticker"]).transform(lambda x: x.rolling(window=period).mean())
        avg_loss = loss.groupby(df["ticker"]).transform(lambda x: x.rolling(window=period).mean())

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
