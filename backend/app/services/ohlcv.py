# backend/app/services/ohlcv.py

from datetime import date, timedelta
from sqlalchemy.orm import Session
import yfinance as yf
import pandas as pd

from app.utils.logger import get_logger
from app.schemas.base import APIResponse
from app.enums.ohlcv import OHLCVDataSource, OHLCVTimeFrame, OHLCVImportType
from app.utils.timeframe import get_provider_timeframe
from app.repositories.security import SecurityRepository
from app.repositories.ohlcv import OHLCVRepository
from app.services.brokers.kite import KiteService

logger = get_logger(__name__)


class OHLCVService:
    """Service class for handling OHLCV (Open, High, Low, Close, Volume) data operations."""

    def __init__(self, db: Session):
        self.db = db
        self.timeframe = "1d"
        self.start_date = "2000-01-01"
        self.end_date = date.today().isoformat()
        self.security_repo = SecurityRepository(db)
        self.ohlcv_repo = OHLCVRepository(db)
        self.kite = KiteService()
        self.data_columns = [ "candle_timestamp", "ticker", "open", "high", "low", "close", "volume"]
        pass

    def import_ohlcv_data(self, type: str, securities: list = None, start_date: str = None, end_date: str = None, timeframe: str = None) -> APIResponse:
        """Import OHLCV data based on the provided request parameters."""
        logger.info(f"Starting OHLCV data import for type: {type}")
        try:
            # If no securities are provided, fetch all securities from the database
            if not securities:
                securities = self.security_repo.get_all(limit=None, order_by="ticker")
                securities = [s.ticker for s in securities]

            if type == OHLCVImportType.HISTORICAL.value:
                return self.import_historical_ohlcv_data(securities, start_date=start_date, end_date=end_date, timeframe=timeframe)
            elif type == OHLCVImportType.INCREMENTAL.value:
                return self.import_latest_ohlcv_data(securities, timeframe=timeframe)

            logger.info(f"Fetched {len(securities)} securities for OHLCV import.")
        except Exception as exc:
            logger.error(f"Failed to import OHLCV data. Error: {exc}", exc_info=True)
            return APIResponse(success=False, message="OHLCV_IMPORT_FAILED", data={ "error": str(exc) })

    def import_historical_ohlcv_data(self, securities: list, start_date: str = None, end_date: str = None, timeframe: str = None) -> APIResponse:
        """Import historical OHLCV data for the specified securities and date range."""
        logger.info(f"Importing historical OHLCV data for securities: {len(securities)} securities from {start_date} to {end_date}")
        try:
            start_date = start_date or self.start_date
            end_date = end_date or self.end_date
            normalized_timeframe = get_provider_timeframe(OHLCVTimeFrame(timeframe or self.timeframe), OHLCVDataSource.YAHOO_FINANCE)

            per_ticker_frames = []
            loaded_tickers = 0
            failed_tickers = []

            for index, ticker in enumerate(securities, start=1):
                logger.info(f"Fetching OHLCV data for {ticker} from {start_date} to {end_date} with timeframe {timeframe}")

                try:
                    yahoo_ticker = f"{ticker}.NS" if ticker != "NIFTY 50" else "^NSEI"
                    downloaded = yf.download(yahoo_ticker, interval=normalized_timeframe, start=start_date, end=end_date, auto_adjust=True, progress=False, threads=False)
                    parsed = self._parse_yahoo_data(downloaded, ticker)

                    if parsed.empty:
                        logger.warning(f"No OHLCV data found for {ticker}.")
                        continue

                    per_ticker_frames.append(parsed)
                    loaded_tickers += 1
                    logger.info(f"Fetched {ticker}: {len(parsed):,} records.")

                    if index % 10 == 0:
                        logger.info(f"Progress: {index}/{len(securities)}")
                except Exception as error:
                    failed_tickers.append(ticker)
                    logger.error(f"Failed to fetch OHLCV data for {ticker}. Error: {error}", exc_info=True)

            if not per_ticker_frames:
                logger.warning("No OHLCV data was fetched for any ticker.")
                return APIResponse(success=False, message="NO_OHLCV_DATA_FETCHED", data={ "loaded_tickers": loaded_tickers, "failed_tickers": failed_tickers })

            data = pd.concat(per_ticker_frames, ignore_index=True)
            data = data[self.data_columns].copy()
            data['candle_timestamp'] = pd.to_datetime(data['candle_timestamp'], utc=True, errors='coerce').dt.tz_convert(None)
            data = data.dropna(subset=["candle_timestamp"])
            data = data.drop_duplicates(subset=[ "ticker", "candle_timestamp"], keep="last")
            data = data.sort_values(by=[ "ticker", "candle_timestamp"]).reset_index(drop=True)

            if data.empty:
                logger.warning("No valid OHLCV data after processing.")
                return APIResponse(success=False, message="NO_VALID_OHLCV_DATA", data={ "loaded_tickers": loaded_tickers, "failed_tickers": failed_tickers })

            self._validate_ohlcv_data(data)
            records = self._prepare_for_persistence(data, timeframe=timeframe, source=OHLCVDataSource.YAHOO_FINANCE.value)
            persisted_count = self._persist_ohlcv_data(records)

            logger.info(f"Loaded {loaded_tickers} tickers with {len(data):,} total candles (failed downloads: {len(failed_tickers)})")

            if failed_tickers:
                logger.warning(f"Failed to fetch OHLCV data for the following tickers: {', '.join(failed_tickers)}")

            return APIResponse(success=True, message="HISTORICAL_OHLCV_IMPORT_SUCCESS", data={ "loaded_tickers": loaded_tickers, "failed_tickers": failed_tickers, "total_candles": len(data), "persisted_candles": persisted_count })
        except Exception as exc:
            logger.error(f"Failed to import historical OHLCV data. Error: {exc}", exc_info=True)
            return APIResponse(success=False, message="HISTORICAL_OHLCV_IMPORT_FAILED", data={ "error": str(exc) })

    def import_latest_ohlcv_data(self, securities: list, timeframe: str) -> APIResponse:
        """Import the latest OHLCV data for the specified securities."""
        logger.info(f"Importing latest OHLCV data for securities: {securities}")
        try:
            normalized_timeframe = get_provider_timeframe(OHLCVTimeFrame(timeframe or self.timeframe), OHLCVDataSource.KITE)
            security_map = self._get_security_map()

            per_ticker_frames = []
            loaded_tickers = 0
            failed_tickers = []

            for index, ticker in enumerate(securities, start=1):
                security = security_map.get(ticker)
                latest_timestamp = self.ohlcv_repo.get_latest_candle_timestamp(security["id"], timeframe)

                if latest_timestamp is None:
                    logger.warning(f"No existing OHLCV data found for {ticker} in timeframe {timeframe}. Skipping incremental import.")
                    continue

                start_date = latest_timestamp.date() - timedelta(days=5)
                end_date = date.today()

                logger.info(f"Fetching OHLCV data for {ticker} from {start_date} to {end_date} with timeframe {timeframe}")

                try:
                    broker_token = security.get("broker_token")
                    if broker_token is None:
                        logger.warning(f"No broker token found for {ticker}. Skipping.")
                        continue

                    fetched = self.kite.get_historical_data(broker_token, start_date, end_date, normalized_timeframe)
                    parsed = self._parse_kite_data(fetched, ticker)

                    if parsed.empty:
                        logger.warning(f"No new OHLCV data found for {ticker}.")
                        continue

                    per_ticker_frames.append(parsed)
                    loaded_tickers += 1
                    logger.info(f"Fetched {ticker}: {len(parsed):,} records.")

                    if index % 10 == 0:
                        logger.info(f"Progress: {index}/{len(securities)}")
                except Exception as error:
                    failed_tickers.append(ticker)
                    logger.error(f"Failed to fetch latest OHLCV data for {ticker}. Error: {error}", exc_info=True)

            if not per_ticker_frames:
                logger.warning("No OHLCV data was fetched for any ticker.")
                return APIResponse(success=False, message="NO_OHLCV_DATA_FETCHED", data={ "loaded_tickers": loaded_tickers, "failed_tickers": failed_tickers })

            data = pd.concat(per_ticker_frames, ignore_index=True)
            data = data[self.data_columns].copy()
            data['candle_timestamp'] = pd.to_datetime(data['candle_timestamp'], utc=True, errors='coerce').dt.tz_convert(None)
            data = data.dropna(subset=["candle_timestamp"])
            data = data.drop_duplicates(subset=[ "ticker", "candle_timestamp"], keep="last")
            data = data.sort_values(by=[ "ticker", "candle_timestamp"]).reset_index(drop=True)

            if data.empty:
                logger.warning("No valid OHLCV data after processing.")
                return APIResponse(success=False, message="NO_VALID_OHLCV_DATA", data={ "loaded_tickers": loaded_tickers, "failed_tickers": failed_tickers })

            self._validate_ohlcv_data(data)
            records = self._prepare_for_persistence(data, timeframe=timeframe, source=OHLCVDataSource.KITE.value)
            persisted_count = self._persist_ohlcv_data(records)

            logger.info(f"Loaded {loaded_tickers} tickers with {len(data):,} total candles (failed downloads: {len(failed_tickers)})")

            if failed_tickers:
                logger.warning(f"Failed to fetch OHLCV data for the following tickers: {', '.join(failed_tickers)}")

            return APIResponse(success=True, message="INCREMENTAL_OHLCV_IMPORT_SUCCESS", data={ "loaded_tickers": loaded_tickers, "failed_tickers": failed_tickers, "total_candles": len(data), "persisted_candles": persisted_count })
        except Exception as exc:
            logger.error(f"Failed to import latest OHLCV data. Error: {exc}", exc_info=True)
            return APIResponse(success=False, message="LATEST_OHLCV_IMPORT_FAILED", data={ "error": str(exc) })

    def _parse_yahoo_data(self, data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        if data.empty:
            return pd.DataFrame(columns=self.data_columns)

        frame = data.copy()

        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = frame.columns.get_level_values(0)

        frame = frame.reset_index()
        date_col = frame.columns[0]

        frame = frame.rename(columns={ date_col: "candle_timestamp", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        frame.columns.name = None
        frame.columns = [str(col).lower() for col in frame.columns]
        frame['ticker'] = ticker

        frame = frame[self.data_columns]
        frame = frame.dropna(subset=[ "open", "high", "low", "close", "volume"])
        frame['candle_timestamp'] = pd.to_datetime(frame['candle_timestamp'], utc=True, errors='coerce').dt.tz_convert(None)
        frame = frame.dropna(subset=["candle_timestamp"])

        return frame

    def _parse_kite_data(self, data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        if data.empty:
            return pd.DataFrame(columns=self.data_columns)

        frame = data.copy()
        frame = frame.rename(columns={ "date": "candle_timestamp", "open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"})
        frame['ticker'] = ticker

        frame = frame[self.data_columns]
        frame = frame.dropna(subset=[ "open", "high", "low", "close", "volume"])
        frame['candle_timestamp'] = pd.to_datetime(frame['candle_timestamp'], utc=True, errors='coerce').dt.tz_convert(None)
        frame = frame.dropna(subset=["candle_timestamp"])

        return frame

    def _validate_ohlcv_data(self, data: pd.DataFrame) -> None:
        """Validate the OHLCV data for consistency and correctness."""
        if data.empty:
            raise ValueError("No OHLCV data to validate.")

        required_columns = set(self.data_columns)
        missing_columns = required_columns - set(data.columns)

        if missing_columns:
            raise ValueError(f"Missing required OHLCV columns: {', '.join(missing_columns)}")

        if data['candle_timestamp'].isna().any():
            raise ValueError("OHLCV data contains invalid or missing 'candle_timestamp' values.")

        duplicates = data.duplicated(subset=[ "ticker", "candle_timestamp"])

        if duplicates.any():
            raise ValueError("Duplicate entries found in OHLCV data for the same ticker and timestamp.")

    def _get_security_map(self) -> dict[str, int]:
        """Fetch a mapping of security tickers to their corresponding IDs from the database."""
        securities = self.security_repo.get_all(limit=None, order_by="ticker")
        return {s.ticker: { "id": s.id, "broker_token": s.broker_token, "exchange": s.exchange } for s in securities}

    def _prepare_for_persistence(self, data: pd.DataFrame, timeframe: str, source: str, is_continuous: bool = False) -> list[dict]:
        """Prepare the OHLCV data for persistence by mapping tickers to security IDs and adding metadata."""
        security_map = self._get_security_map()

        frame = data.copy()
        frame['security_id'] = frame['ticker'].map(lambda x: security_map.get(x, {}).get('id'))

        missing = frame[frame['security_id'].isna()]

        if not missing.empty:
            logger.warning(f"Skipping {len(missing)} OHLCV records due to missing security mappings: {missing['ticker'].unique()}")

        frame = frame.dropna(subset=['security_id'])
        frame['security_id'] = frame['security_id'].astype(int)
        frame['timeframe'] = timeframe
        frame['source'] = source
        frame['is_continuous'] = is_continuous

        return frame[[ 'security_id', 'candle_timestamp', 'open', 'high', 'low', 'close', 'volume', 'timeframe', 'source', 'is_continuous']].to_dict(orient='records')

    def _persist_ohlcv_data(self, records: list[dict]) -> int:
        """Persist the OHLCV data to the database and return the number of records inserted."""
        if not records:
            return 0

        batch_size = 10000

        try:
            for start in range(0, len(records), batch_size):
                logger.info(f"Progress: Batch {start // batch_size + 1} / {((len(records) - 1) // batch_size) + 1}")
                batch = records[start:start + batch_size]
                self.ohlcv_repo.bulk_upsert(batch)
            self.db.commit()
            return len(records)
        except Exception:
            self.db.rollback()
            raise
