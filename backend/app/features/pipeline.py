# backend/app/features/pipeline.py

import pandas as pd

from app.features.trend import TrendFeatures
from app.features.momentum import MomentumFeatures
from app.features.volatility import VolatilityFeatures
from app.features.volume import VolumeFeatures
from app.features.structure import StructureFeatures
from app.features.breakout import BreakoutFeatures
from app.features.relative_strength import RelativeStrengthFeatures
from app.features.sector import SectorFeatures
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FeaturePipeline:
    """Pipeline for extracting features from financial data."""

    @classmethod
    def transform(cls, stock_df: pd.DataFrame, index_df: pd.DataFrame | None = None) -> pd.DataFrame:
        """Extract features from stock and index data.

        Args:
            stock_df (pd.DataFrame): DataFrame containing stock data.
            index_df (pd.DataFrame | None): DataFrame containing index data.

        Returns:
            pd.DataFrame: DataFrame containing extracted features.
        """
        stock_df = stock_df.copy()

        stock_df = TrendFeatures.transform(stock_df)
        stock_df = MomentumFeatures.transform(stock_df)
        stock_df = VolatilityFeatures.transform(stock_df)
        stock_df = VolumeFeatures.transform(stock_df)
        stock_df = StructureFeatures.transform(stock_df)
        stock_df = BreakoutFeatures.transform(stock_df)

        if index_df is not None:
            stock_df = RelativeStrengthFeatures.transform(stock_df, index_df)

        stock_df = SectorFeatures.transform(stock_df)

        return stock_df
