# backend/app/features/sector.py

import numpy as np
import pandas as pd


class SectorFeatures:
    """Class to compute sector features for a given dataset."""

    @classmethod
    def transform(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform the input DataFrame to compute sector features.

        Args:
            df (pd.DataFrame): Input DataFrame containing sector data.

        Returns:
            pd.DataFrame: DataFrame with computed sector features.
        """
        if 'sector' not in df.columns:
            return df

        df = df.copy()

        for n in [ 5, 10, 20, 60 ]:
            ret_col = f'ret_{n}'
            sector_col = f'sector_ret_{n}'

            sector_median = df.groupby([ 'candle_timestamp', 'sector'])[ret_col].transform('median')
            df[sector_col] = sector_median.fillna(0)

            if n in [ 20, 60 ]:
                rs_col = f'sector_rs_{n}'
                df[rs_col] = (df[ret_col] - df[sector_col]).fillna(0)

        return df
