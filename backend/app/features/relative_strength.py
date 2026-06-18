# backend/app/features/relative_strength.py

import numpy as np
import pandas as pd


class RelativeStrengthFeatures:
    """Calculates relative strength features such as RSI and momentum acceleration."""

    @classmethod
    def transform(cls, stock_df: pd.DataFrame, index_df: pd.DataFrame) -> pd.DataFrame:
        df = stock_df.copy()
        idx = index_df[[ 'candle_timestamp', 'close']].copy().sort_values('candle_timestamp')

        idx['index_ret_5'] = idx['close'].pct_change(5).fillna(0)
        idx['index_ret_10'] = idx['close'].pct_change(10).fillna(0)
        idx['index_ret_20'] = idx['close'].pct_change(20).fillna(0)
        idx['index_ret_60'] = idx['close'].pct_change(60).fillna(0)

        idx['index_sma_252'] = idx['close'].rolling(252).mean()
        idx_merge = idx.rename(columns={ 'close': 'index_close'})

        df = df.merge(idx_merge, on='candle_timestamp', how='left')

        df['rs_5'] = (df['ret_5'] - df['index_ret_5']).fillna(0)
        df['rs_10'] = (df['ret_10'] - df['index_ret_10']).fillna(0)
        df['rs_20'] = (df['ret_20'] - df['index_ret_20']).fillna(0)
        df['rs_60'] = (df['ret_60'] - df['index_ret_60']).fillna(0)

        stock_sma_252 = df.groupby('ticker')['close'].transform(lambda x: x.rolling(252).mean())
        stock_ratio = df['close'] / stock_sma_252.replace(0, np.nan)
        index_ratio = df['index_close'] / df['index_sma_252'].replace(0, np.nan)
        df['rs_ratio'] = (stock_ratio / index_ratio.replace(0, np.nan) - 1).fillna(0)

        df['rs_ratio_ret_20'] = df.groupby('ticker')['rs_ratio'].transform(lambda x: x.pct_change(20).fillna(0))
        df['rs_ratio_ret_60'] = df.groupby('ticker')['rs_ratio'].transform(lambda x: x.pct_change(60).fillna(0))

        df = df.drop(columns=[ 'index_close', 'index_ret_5', 'index_ret_10', 'index_ret_20', 'index_ret_60', 'index_sma_252'])

        return df
