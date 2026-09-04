# app/services/feature.py

import pandas as pd
import numpy as np
import time

from datetime import date, datetime
from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.repositories.ohlcv import OHLCVRepository
from app.repositories.features import SecurityFeatureRepository, MarketFeatureRepository
from app.repositories.security import SecurityRepository
from app.features.pipeline import FeaturePipeline
from app.features.market import MarketFeatures
from app.enums.feature import FeatureCalculationType
from app.schemas.base import APIResponse
from app.models.features import SecurityFeature, MarketFeature
from app.models.ohlcv import OHLCV
from app.models.security import Security
from app.enums.security import SecurityType
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
                response = self.generate_complete_features(securities, start_date, end_date, timeframe)
            elif type == FeatureCalculationType.INCREMENTAL.value or type == FeatureCalculationType.LIVE_REFRESH.value:
                response = self.generate_incremental_features(securities, timeframe, live_refresh=type == FeatureCalculationType.LIVE_REFRESH.value)
            else:
                return APIResponse(success=False, message="INVALID_FEATURE_CALCULATION_TYPE", data={ "error": f"Unsupported feature calculation type: {type}"})

            if response.success and type != FeatureCalculationType.LIVE_REFRESH.value:
                market_response = self.generate_market_features(timeframe, start_date, end_date)
                if not market_response.success:
                    logger.error(f"Market feature generation failed after security feature generation: {market_response.message}")

            return response
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

    def generate_incremental_features(self, securities: list, timeframe: str, live_refresh: bool = False) -> APIResponse:
        """Generate incremental features for the specified securities and timeframe."""
        try:
            logger.info(f"Generating incremental features for {len(securities)} securities and timeframe: {timeframe}")

            feature_columns = [column.name for column in SecurityFeature.__table__.columns if column.name not in [ "id", "created_at", "updated_at"]]

            index_data = self.ohlcv_repo.get_recent_by_tickers_and_timeframe(tickers=["NIFTY 50"], timeframe=timeframe, limit_per_ticker=1000)
            index_df = self._get_dataframe_from_records(index_data)

            # Bounded at the SQL level to the last 1000 rows PER TICKER — never loads
            # each security's full history just to trim it down in Python afterward.
            # The prior unbounded get_by_tickers_and_timeframe() call here loaded the
            # entire OHLCV table for every ticker on every 10-minute live-refresh run,
            # which was the actual cause of this job's recurring out-of-memory kills.
            ohlcv_data = self.ohlcv_repo.get_recent_by_tickers_and_timeframe(tickers=securities, timeframe=timeframe, limit_per_ticker=1000)
            all_df = self._get_dataframe_from_records(ohlcv_data)

            if all_df.empty:
                return APIResponse(success=False, message="NO_OHLCV_DATA", data={ "error": "No OHLCV data found for the specified securities and timeframe."})

            grouped_data = [(ticker, group.copy()) for ticker, group in all_df.groupby("ticker")]

            logger.info(f"Starting parallel incremental feature generation for {len(grouped_data)} securities.")

            total_processed = 0
            failed_securities = []

            max_workers = 8
            tail_rows = 1 if live_refresh else None

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(self._process_security_incremental, ticker, ohlcv_df, index_df, feature_columns, tail_rows): ticker for ticker, ohlcv_df in grouped_data}

                for future in as_completed(futures):
                    ticker = futures[future]

                    try:
                        count = future.result()
                        total_processed += count
                        logger.info(f"{ticker}: upserted {count} incremental feature records.")
                    except Exception as e:
                        logger.error(f"Error processing security {ticker}: {str(e)}", exc_info=True)
                        failed_securities.append(ticker)

            logger.info(f"Incremental feature generation completed. Processed = {total_processed}, Failed = {len(failed_securities)}")
            return APIResponse(success=len(failed_securities) == 0, message="FEATURE_GENERATION_SUCCESS" if not failed_securities else "FEATURE_GENERATION_PARTIAL_SUCCESS", data={ "processed_records": total_processed, "processed_securities": len(grouped_data) - len(failed_securities), "failed_securities": failed_securities })
        except Exception as e:
            logger.error(f"Error during incremental feature generation: {str(e)}", exc_info=True)
            return APIResponse(success=False, message="INCREMENTAL_FEATURE_GENERATION_FAILED", data={ "error": str(e) })

    def generate_market_features(self, timeframe: str, start_date: str = None, end_date: str = None) -> APIResponse:
        """Generate and store cross-sectional market breadth features across all active equity securities."""
        try:
            equity_tickers = [row.ticker for row in self.db.query(Security.ticker).filter(Security.type == SecurityType.EQUITY.value, Security.is_active == True).all()]

            if not equity_tickers:
                return APIResponse(success=False, message="NO_ACTIVE_EQUITIES", data={ "error": "No active equity securities found."})

            ohlcv_data = self.ohlcv_repo.get_by_tickers_and_timeframe(tickers=equity_tickers, timeframe=timeframe, start_date=start_date, end_date=end_date)
            all_df = self._get_dataframe_from_records(ohlcv_data)

            if all_df.empty:
                return APIResponse(success=False, message="NO_OHLCV_DATA", data={ "error": "No OHLCV data found for market feature generation."})

            all_df = all_df.groupby("ticker").tail(1000)

            market_df = MarketFeatures.transform(all_df)
            market_df["timeframe"] = timeframe

            feature_columns = [column.name for column in MarketFeature.__table__.columns if column.name not in [ "id", "created_at", "updated_at"]]
            available_columns = [ col for col in feature_columns if col in market_df.columns ]

            records = (market_df[available_columns].replace([np.inf, -np.inf], np.nan).where(pd.notnull(market_df[available_columns]), None).to_dict("records"))

            count = MarketFeatureRepository(self.db).bulk_upsert(records)
            self.db.commit()

            logger.info(f"Market feature generation completed. Upserted {count} rows.")
            return APIResponse(success=True, message="MARKET_FEATURE_GENERATION_SUCCESS", data={ "processed_records": count })
        except Exception as e:
            logger.error(f"Error during market feature generation: {str(e)}", exc_info=True)
            return APIResponse(success=False, message="MARKET_FEATURE_GENERATION_FAILED", data={ "error": str(e) })

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

    @staticmethod
    def _process_security_incremental(ticker: str, ohlcv_df: pd.DataFrame, index_df: pd.DataFrame, feature_columns: list, tail_rows: int = None) -> int:
        """Process a single security to generate and upsert incremental features."""
        db = SessionLocal()
        try:
            repo = SecurityFeatureRepository(db)
            df = FeaturePipeline.transform(ohlcv_df.copy(), index_df)

            if tail_rows is not None:
                df = df.tail(tail_rows)

            available_columns = [ col for col in feature_columns if col in df.columns ]

            records = (df[available_columns].replace([np.inf, -np.inf], np.nan).where(pd.notnull(df[available_columns]), None).to_dict("records"))

            count = repo.bulk_upsert(records)
            db.commit()
            return count
        finally:
            db.close()

    def get_latest_snapshot(self, timeframe: str = "1d") -> pd.DataFrame:
        """Get the latest snapshot of features for all securities. One row per security with the most recent features."""
        latest_timestamp_subquery = self.db.query(OHLCV.security_id, func.max(OHLCV.candle_timestamp).label("latest_timestamp")).filter(OHLCV.timeframe == timeframe).group_by(OHLCV.security_id).subquery()
        records = self.db.query(SecurityFeature).join(OHLCV, SecurityFeature.ohlcv_id == OHLCV.id).join(Security, OHLCV.security_id == Security.id).filter(Security.type == SecurityType.EQUITY.value).join(latest_timestamp_subquery, (OHLCV.security_id == latest_timestamp_subquery.c.security_id) & (OHLCV.candle_timestamp == latest_timestamp_subquery.c.latest_timestamp)).all()
        return self._feature_records_to_dataframe(records)

    def get_snapshot(self, as_of_date, timeframe: str = "1d") -> pd.DataFrame:
        """Get a snapshot of features for all securities as of a specific date. One row per security with the most recent features up to that date."""
        latest_timestamp_subquery = self.db.query(OHLCV.security_id, func.max(OHLCV.candle_timestamp).label("latest_timestamp")).filter(OHLCV.timeframe == timeframe, OHLCV.candle_timestamp <= as_of_date).group_by(OHLCV.security_id).subquery()
        records = self.db.query(SecurityFeature).join(OHLCV, SecurityFeature.ohlcv_id == OHLCV.id).join(Security, OHLCV.security_id == Security.id).filter(Security.type == SecurityType.EQUITY.value).join(latest_timestamp_subquery, (OHLCV.security_id == latest_timestamp_subquery.c.security_id) & (OHLCV.candle_timestamp == latest_timestamp_subquery.c.latest_timestamp)).all()
        return self._feature_records_to_dataframe(records)

    def _feature_records_to_dataframe(self, records: list[SecurityFeature]) -> pd.DataFrame:
        """Convert SecurityFeature ORM objects into a DataFrame."""
        if not records:
            logger.warning("No feature records found to convert to DataFrame.")
            return pd.DataFrame()

        return pd.DataFrame([{ "security_id": row.ohlcv.security_id, "ticker": row.ohlcv.security.ticker, "sector": row.ohlcv.security.sector, "candle_timestamp": row.ohlcv.candle_timestamp, **{col.name: float(v) if (v := getattr(row, col.name)) is not None else None for col in SecurityFeature.__table__.columns if col.name not in [ "id", "created_at", "updated_at", "ohlcv_id"]} } for row in records])

    def get_global_quantiles(self, quantiles: dict[str, float]) -> dict[str, float]:
        """Get global quantiles for specified feature columns."""
        feature_columns = list(quantiles.keys())
        records = self.db.query(*[getattr(SecurityFeature, col) for col in feature_columns]).join(OHLCV, SecurityFeature.ohlcv_id == OHLCV.id).join(Security, OHLCV.security_id == Security.id).filter(Security.type == SecurityType.EQUITY.value).all()

        if not records:
            return { column: 0.0 for column in feature_columns }

        df = pd.DataFrame(records, columns=feature_columns).astype(float)
        thresholds = {}

        for column, percentile in quantiles.items():
            thresholds[column] = float(df[column].dropna().quantile(percentile))
        return thresholds

    def get_security_by_ticker(self, ticker: str, exchange: str) -> Optional[Security]:
        """Look up a single security by ticker and exchange."""
        return self.security_repo.get_by_ticker_exchange(ticker, exchange)

    def get_recent_closes(self, security_id: int, timeframe: str = "1d", as_of_date: date = None) -> list[float]:
        """Return every daily close on record for a security up to and including as_of_date, oldest first."""
        end = datetime.combine(as_of_date, datetime.min.time()) if as_of_date else None
        rows = self.ohlcv_repo.get_by_security_and_timeframe(security_id, timeframe=timeframe, end_date=end)
        return [float(r.close) for r in rows]

    def get_latest_features_for_security(self, security_id: int, timeframe: str = "1d") -> dict:
        """Get the most recent feature row for a single security as a plain dict."""
        latest_ohlcv = (self.db.query(OHLCV).filter(OHLCV.security_id == security_id, OHLCV.timeframe == timeframe).order_by(OHLCV.candle_timestamp.desc()).first())
        if not latest_ohlcv:
            return {}

        record = (self.db.query(SecurityFeature).filter(SecurityFeature.ohlcv_id == latest_ohlcv.id).first())
        if not record:
            return {}

        return {col.name: getattr(record, col.name) for col in SecurityFeature.__table__.columns if col.name not in [ "id", "created_at", "updated_at", "ohlcv_id"]}
