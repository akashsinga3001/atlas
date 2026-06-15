# backend/app/services/ohlcv.py

from datetime import date
from sqlalchemy.orm import Session
import yfinance as yf
import pandas as pd

from app.utils.logger import get_logger
from app.schemas.base import APIResponse
from app.enums.ohlcv import OHLCVDataSource, OHLCVTimeFrame
from app.utils.timeframe import get_provider_timeframe
from app.repositories.security import SecurityRepository

logger = get_logger(__name__)


class OHLCVService:
    """Service class for handling OHLCV (Open, High, Low, Close, Volume) data operations."""

    def __init__(self, db: Session):
        self.db = db
        self.timeframe = "1d"
        self.start_date = "2000-01-01"
        self.end_date = date.today().isoformat()
        self.security_repo = SecurityRepository(db)
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

            if type == "historical":
                return self.import_historical_ohlcv_data(securities, start_date=start_date, end_date=end_date, timeframe=timeframe)
            elif type == "incremental":
                return self.import_latest_ohlcv_data(securities)

            logger.info(f"Fetched {len(securities)} securities for OHLCV import.")
        except Exception as exc:
            logger.error("Failed to import OHLCV data.", exc_info=True)
            return APIResponse(success=False, message="OHLCV_IMPORT_FAILED", data={ "error": str(exc) })

    def import_historical_ohlcv_data(self, securities: list, start_date: str = None, end_date: str = None, timeframe: str = None) -> APIResponse:
        """Import historical OHLCV data for the specified securities and date range."""
        logger.info(f"Importing historical OHLCV data for securities: {len(securities)} securities from {start_date} to {end_date}")
        try:
            start_date = start_date or self.start_date
            end_date = end_date or self.end_date
            timeframe = get_provider_timeframe(OHLCVTimeFrame(timeframe or self.timeframe), OHLCVDataSource.YAHOO_FINANCE)

            per_ticker_frames = []
            loaded_tickers = 0
            failed_tickers = []

            for index, ticker in enumerate(securities, start=1):
                logger.info(f"Fetching OHLCV data for {ticker} from {start_date} to {end_date} with timeframe {timeframe}")

                try:
                    yahoo_ticker = f"{ticker}.NS" if ticker != "NIFTY 50" else "^NSEI"
                    downloaded = yf.download(yahoo_ticker, interval=timeframe, start=start_date, end=end_date, auto_adjust=True, progress=False, threads=False)
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

            logger.info(f"Loaded {loaded_tickers} tickers with {len(data):,} total candles (failed downloads: {len(failed_tickers)})")

            if failed_tickers:
                logger.warning(f"Failed to fetch OHLCV data for the following tickers: {', '.join(failed_tickers)}")

            return APIResponse(success=True, message="HISTORICAL_OHLCV_IMPORT_SUCCESS", data={ "loaded_tickers": loaded_tickers, "failed_tickers": failed_tickers, "total_candles": len(data) })
        except Exception as exc:
            logger.error("Failed to import historical OHLCV data.", exc_info=True)
            return APIResponse(success=False, message="HISTORICAL_OHLCV_IMPORT_FAILED", data={ "error": str(exc) })

    def import_latest_ohlcv_data(self, securities: list) -> APIResponse:
        """Import the latest OHLCV data for the specified securities."""
        logger.info(f"Importing latest OHLCV data for securities: {securities}")
        try:
            pass
        except Exception as exc:
            logger.error("Failed to import latest OHLCV data.", exc_info=True)
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
