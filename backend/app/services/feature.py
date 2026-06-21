# app/services/feature.py

import pandas as pd
import numpy as np
import time

from sqlalchemy.orm import Session

from app.repositories.ohlcv import OHLCVRepository
from app.repositories.features import SecurityFeatureRepository
from app.repositories.security import SecurityRepository
from app.features.pipeline import FeaturePipeline
from app.enums.feature import FeatureCalculationType
from app.schemas.base import APIResponse
from app.models.features import SecurityFeature

from app.utils.logger import get_logger

logger = get_logger(__name__)


class FeatureService:
    """Service for managing feature extraction and storage."""

    def __init__(self, db: Session):
        self.db = db
        self.ohlcv_repo = OHLCVRepository(db)
        self.security_repo = SecurityRepository(db)
        self.security_feature_repo = SecurityFeatureRepository(db)

    def generate_security_features(self, type: str, securities: list = None, start_date: str = None, end_date: str = None, timeframe: str = None) -> APIResponse:
        """Generate and store features for all securities based on the specified timeframe."""
        logger.info(f"Starting feature generation for type: {type}")
        try:

            if type == FeatureCalculationType.COMPLETE.value:
                return self.generate_complete_features(securities, start_date, end_date, timeframe)
            elif type == FeatureCalculationType.INCREMENTAL.value:
                return self.generate_incremental_features(securities, timeframe)

            return APIResponse(success=False, message="INVALID_FEATURE_CALCULATION_TYPE", data={ "error": f"Unsupported feature calculation type: {type}"})
        except Exception as e:
            logger.error(f"Failed to generate features for securities. Error: {str(e)}", exc_info=True)
            return APIResponse(success=False, message="FEATURE_GENERATION_FAILED", data={ "error": str(e) })

    def generate_complete_features(self, securities: list, start_date: str, end_date: str, timeframe: str) -> APIResponse:
        """Generate complete features for the specified securities and timeframe."""
        try:
            logger.info(f"Loading OHLCV data for timeframe {timeframe} to generate features.")
            start = time.perf_counter()

            ohlcv_data = self.ohlcv_repo.get_by_tickers_and_timeframe(securities, timeframe, start_date, end_date)
            logger.info(f"Loaded OHLCV data for {len(securities)} securities in {time.perf_counter() - start:.2f} seconds.")

            index_data = self.ohlcv_repo.get_by_tickers_and_timeframe(["NIFTY 50"], timeframe, start_date, end_date)

            all_df = self._get_dataframe_from_records(ohlcv_data)
            index_df = self._get_dataframe_from_records(index_data)

            feature_columns = [column.name for column in SecurityFeature.__table__.columns if column.name not in [ "id", "created_at", "updated_at"]]

            total_processed = 0

            for ticker, ohlcv_df in all_df.groupby("ticker"):
                logger.info(f"Generating features for security: {ticker}")

                start = time.perf_counter()
                df = FeaturePipeline.transform(ohlcv_df.copy(), index_df)

                logger.info(f"{ticker}: pipeline completed in {time.perf_counter() - start:.2f}s")

                available_columns = [ col for col in feature_columns if col in df.columns ]
                records = (df[available_columns].replace([np.inf, -np.inf], np.nan).where(pd.notnull(df[available_columns]), None).to_dict("records"))

                start = time.perf_counter()
                count = self.security_feature_repo.replace_for_security(records)

                logger.info(f"{ticker}: upserted {count} feature records in {time.perf_counter() - start:.2f}s")
                total_processed += count

            return APIResponse(success=True, message="FEATURE_GENERATION_SUCCESS", data={ "total_processed": total_processed })
        except Exception as e:
            logger.error(f"Error during complete feature generation: {str(e)}", exc_info=True)
            return APIResponse(success=False, message="FEATURE_GENERATION_FAILED", data={ "error": str(e) })

    def generate_incremental_features(self, securities: list, timeframe: str) -> APIResponse:
        """Generate incremental features for the specified securities and timeframe."""
        try:
            logger.info(f"Generating incremental features for securities: {len(securities)} and timeframe: {timeframe}")

            feature_columns = [column.name for column in SecurityFeature.__table__.columns if column.name not in [ "id", "created_at", "updated_at"]]

            total_processed = 0

            index_data = self.ohlcv_repo.get_by_tickers_and_timeframe(tickers=["NIFTY 50"], timeframe=timeframe, )
            index_df = self._get_dataframe_from_records(index_data)
            if len(index_df) > 300:
                index_df = index_df.tail(300)

            for ticker in securities:
                logger.info(f"Generating incremental features for security: {ticker}")
                ohlcv_data = self.ohlcv_repo.get_by_tickers_and_timeframe(tickers=[ticker], timeframe=timeframe)
                ohlcv_df = self._get_dataframe_from_records(ohlcv_data)

                if ohlcv_df.empty:
                    logger.warning(f"No OHLCV data found for security: {ticker}. Skipping feature generation.")
                    continue

                ohlcv_df = ohlcv_df.tail(300)
                df = FeaturePipeline.transform(ohlcv_df.copy(), index_df)

                available_columns = [ col for col in feature_columns if col in df.columns ]
                records = (df[available_columns].replace([np.inf, -np.inf], np.nan).where(pd.notnull(df[available_columns]), None).to_dict("records"))

                count = self.security_feature_repo.bulk_upsert(records)
                logger.info(f"{ticker}: upserted {count} incremental feature records.")
                total_processed += count
            return APIResponse(success=True, message="FEATURE_GENERATION_SUCCESS", data={ "processed_records": total_processed })
        except Exception as e:
            logger.error(f"Error during incremental feature generation: {str(e)}", exc_info=True)
            return APIResponse(success=False, message="INCREMENTAL_FEATURE_GENERATION_FAILED", data={ "error": str(e) })

    def _get_dataframe_from_records(self, records: list) -> pd.DataFrame:
        """Convert a list of records to a pandas DataFrame."""
        if not records:
            logger.warning("No records found to convert to DataFrame.")
            return pd.DataFrame()

        return pd.DataFrame([{ "ohlcv_id": row.id, "security_id": row.security_id, "ticker": row.security.ticker, "sector": row.security.sector or None, "candle_timestamp": row.candle_timestamp, "open": float(row.open), "high": float(row.high), "low": float(row.low), "close": float(row.close), "volume": float(row.volume), } for row in records])
