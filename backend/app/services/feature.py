# app/services/feature.py

import pandas as pd
import numpy as np
import time

from sqlalchemy import func
from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.repositories.ohlcv import OHLCVRepository
from app.repositories.features import SecurityFeatureRepository
from app.repositories.security import SecurityRepository
from app.features.pipeline import FeaturePipeline
from app.enums.feature import FeatureCalculationType
from app.schemas.base import APIResponse
from app.models.features import SecurityFeature
from app.models.ohlcv import OHLCV
from app.core.database import SessionLocal

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

            if not securities:
                securities = self.security_repo.get_all(limit=None, order_by="ticker")
                securities = [security.ticker for security in securities]

            if type == FeatureCalculationType.COMPLETE.value:
                return self.generate_complete_features(securities, start_date, end_date, timeframe)
            elif type == FeatureCalculationType.INCREMENTAL.value or type == FeatureCalculationType.LIVE_REFRESH.value:
                return self.generate_incremental_features(securities, timeframe)

            return APIResponse(success=False, message="INVALID_FEATURE_CALCULATION_TYPE", data={ "error": f"Unsupported feature calculation type: {type}"})
        except Exception as e:
            logger.error(f"Failed to generate features for securities. Error: {str(e)}", exc_info=True)
            return APIResponse(success=False, message="FEATURE_GENERATION_FAILED", data={ "error": str(e) })

    def generate_complete_features(self, securities: list, start_date: str, end_date: str, timeframe: str) -> APIResponse:
        """Generate complete features for the specified securities and timeframe."""
        try:
            logger.info(f"Loading OHLCV data for timeframe {timeframe} to generate complete features for securities: {len(securities)}")

            start = time.perf_counter()

            ohlcv_data = self.ohlcv_repo.get_by_tickers_and_timeframe(tickers=securities, timeframe=timeframe, start_date=start_date, end_date=end_date)
            logger.info(f"Loaded OHLCV data for {len(securities)} securities in {time.perf_counter() - start:.2f} seconds.")

            index_data = self.ohlcv_repo.get_by_tickers_and_timeframe(tickers=["NIFTY 50"], timeframe=timeframe, start_date=start_date, end_date=end_date)

            all_df = self._get_dataframe_from_records(ohlcv_data)
            index_df = self._get_dataframe_from_records(index_data)

            if all_df.empty:
                return APIResponse(success=False, message="NO_OHLCV_DATA", data={ "error": "No OHLCV data found for the specified securities and timeframe."})

            feature_columns = [column.name for column in SecurityFeature.__table__.columns if column.name not in [ "id", "created_at", "updated_at"]]

            grouped_data = [(ticker, group.copy()) for ticker, group in all_df.groupby("ticker")]

            logger.info(f"Starting Parallel Feature Generation for {len(grouped_data)} securities.")

            total_processed = 0
            failed_securities = []

            max_workers = 8

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(self._process_security, ticker, ohlcv_df, index_df, feature_columns): ticker for ticker, ohlcv_df in grouped_data}

                for future in as_completed(futures):
                    ticker = futures[future]

                    try:
                        count = future.result()
                        total_processed += count
                        logger.info(f"{ticker}: upserted {count} feature records.")
                    except Exception as e:
                        logger.error(f"Error processing security {ticker}: {str(e)}", exc_info=True)
                        failed_securities.append(ticker)

            logger.info(f"Feature Generation Completed. Processed = {total_processed}, Failed = {len(failed_securities)}")
            return APIResponse(success=len(failed_securities) == 0, message="FEATURE_GENERATION_SUCCESS" if not failed_securities else "FEATURE_GENERATION_PARTIAL_SUCCESS", data={ "processed_records": total_processed, "processed_securities": len(grouped_data) - len(failed_securities), "failed_securities": failed_securities })
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
            if len(index_df) > 1000:
                index_df = index_df.tail(1000)

            for ticker in securities:
                ohlcv_data = self.ohlcv_repo.get_by_tickers_and_timeframe(tickers=[ticker], timeframe=timeframe)
                ohlcv_df = self._get_dataframe_from_records(ohlcv_data)

                if ohlcv_df.empty:
                    logger.warning(f"No OHLCV data found for security: {ticker}. Skipping feature generation.")
                    continue

                ohlcv_df = ohlcv_df.tail(1000)
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

    @staticmethod
    def _process_security(ticker: str, ohlcv_df: pd.DataFrame, index_df: pd.DataFrame, feature_columns: list) -> int:
        """Process a single security to generate and store features."""
        db = SessionLocal()
        try:
            repo = SecurityFeatureRepository(db)
            df = FeaturePipeline.transform(ohlcv_df.copy(), index_df)

            available_columns = [ col for col in feature_columns if col in df.columns ]

            records = (df[available_columns].replace([np.inf, -np.inf], np.nan).where(pd.notnull(df[available_columns]), None).to_dict("records"))

            count = repo.replace_for_security(records)
            return count
        finally:
            db.close()

    def get_latest_snapshot(self, timeframe: str = "1d") -> pd.DataFrame:
        """Get the latest snapshot of features for all securities. One row per security with the most recent features."""
        latest_timestamp_subquery = self.db.query(OHLCV.security_id, func.max(OHLCV.candle_timestamp).label("latest_timestamp")).filter(OHLCV.timeframe == timeframe).group_by(OHLCV.security_id).subquery()
        records = self.db.query(SecurityFeature).join(OHLCV, SecurityFeature.ohlcv_id == OHLCV.id).join(latest_timestamp_subquery, (OHLCV.security_id == latest_timestamp_subquery.c.security_id) & (OHLCV.candle_timestamp == latest_timestamp_subquery.c.latest_timestamp)).all()
        return self._feature_records_to_dataframe(records)

    def get_snapshot(self, as_of_date, timeframe: str = "1d") -> pd.DataFrame:
        """Get a snapshot of features for all securities as of a specific date. One row per security with the most recent features up to that date."""
        latest_timestamp_subquery = self.db.query(OHLCV.security_id, func.max(OHLCV.candle_timestamp).label("latest_timestamp")).filter(OHLCV.timeframe == timeframe, OHLCV.candle_timestamp <= as_of_date).group_by(OHLCV.security_id).subquery()
        records = self.db.query(SecurityFeature).join(OHLCV, SecurityFeature.ohlcv_id == OHLCV.id).join(latest_timestamp_subquery, (OHLCV.security_id == latest_timestamp_subquery.c.security_id) & (OHLCV.candle_timestamp == latest_timestamp_subquery.c.latest_timestamp)).all()
        return self._feature_records_to_dataframe(records)

    def _feature_records_to_dataframe(self, records: list[SecurityFeature]) -> pd.DataFrame:
        """Convert SecurityFeature ORM objects into a DataFrame."""
        if not records:
            logger.warning("No feature records found to convert to DataFrame.")
            return pd.DataFrame()

        return pd.DataFrame([{
            "security_id": row.ohlcv.security_id,
            "ticker": row.ohlcv.security.ticker,
            "sector": row.ohlcv.security.sector,
            "candle_timestamp": row.ohlcv.candle_timestamp,
            "atr_pct": float(row.atr_pct) if row.atr_pct is not None else None,
            "base_tightness": float(row.base_tightness) if row.base_tightness is not None else None,
            "ema_compression": float(row.ema_compression) if row.ema_compression is not None else None,
            "close_near_high": float(row.close_near_high) if row.close_near_high is not None else None,
            "volume_ratio": float(row.volume_ratio) if row.volume_ratio is not None else None,
            "dist_ema_10": float(row.dist_ema_10) if row.dist_ema_10 is not None else None
        } for row in records])

    def get_global_quantiles(self, quantiles: dict[str, float]) -> dict[str, float]:
        """Get global quantiles for specified feature columns."""
        feature_columns = list(quantiles.keys())
        records = self.db.query(*[getattr(SecurityFeature, col) for col in feature_columns]).all()

        if not records:
            return { column: 0.0 for column in feature_columns }

        df = pd.DataFrame(records, columns=feature_columns)
        thresholds = {}

        for column, percentile in quantiles.items():
            thresholds[column] = float(df[column].dropna().quantile(percentile))
        return thresholds
