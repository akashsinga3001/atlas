# backend/app/services/security.py

import io
from sqlalchemy.orm import Session
import httpx
import pandas as pd
import yfinance as yf

from app.services.brokers.kite import KiteService
from app.schemas.base import APIResponse
from app.repositories.security import SecurityRepository
from app.enums.security import SecurityType

from app.utils.logger import get_logger

logger = get_logger(__name__)

NSE_NIFTY500_CSV_URL = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"


class SecurityService:
    """Service class to manage securities data and interactions with the Kite API."""

    def __init__(self, db: Session):
        self.db = db
        self.kite_service = KiteService()
        self.security_repo = SecurityRepository(db)

    def _fetch_nifty500_tickers(self) -> set[str]:
        """Download the NIFTY 500 constituent list from NSE and return the set of NSE symbols."""
        logger.info("Fetching NIFTY 500 constituent list from NSE.")
        response = httpx.get(NSE_NIFTY500_CSV_URL, headers={ "User-Agent": "Mozilla/5.0"}, follow_redirects=True, timeout=30, )
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text))
        tickers = set(df["Symbol"].str.strip().tolist())
        logger.info(f"Fetched {len(tickers)} NIFTY 500 tickers from NSE.")
        return tickers

    def import_securities(self) -> APIResponse:
        """Synchronize the NIFTY 500 universe with the database.

        Fetches the NIFTY 500 constituent list from NSE, cross-references against Kite
        instruments to resolve broker tokens and instrument metadata, upserts into the
        securities table, and deactivates any security no longer in the universe.
        """
        try:
            nifty500_tickers = self._fetch_nifty500_tickers()

            all_instruments = self.kite_service.fetch_instruments()

            nse_eq = all_instruments[all_instruments['segment'] == 'NSE']
            nse_indices = all_instruments[all_instruments['segment'] == 'INDICES']

            nifty500_instruments = nse_eq[nse_eq['tradingsymbol'].isin(nifty500_tickers)]
            logger.info(f"Matched {len(nifty500_instruments)} NIFTY 500 tickers against Kite instruments.")

            unmatched = nifty500_tickers - set(nifty500_instruments['tradingsymbol'])
            if unmatched:
                logger.warning(f"{len(unmatched)} NIFTY 500 tickers not found in Kite instruments: {sorted(unmatched)}")

            combined = pd.concat([ nifty500_instruments, nse_indices ])
            securities_df = self.kite_service._to_security_row(combined)
            incoming_tickers = set(securities_df['ticker'].tolist())

            upsert_result = self.security_repo.bulk_upsert(securities_df.to_dict(orient="records"), active_tickers=incoming_tickers)

            return APIResponse(success=True, message="SECURITIES_IMPORTED", data={ "total": len(securities_df), "nifty500_matched": len(nifty500_instruments), "nifty500_unmatched": len(unmatched), "upsert_result": upsert_result, }, )
        except Exception:
            logger.error("Failed to import securities data.", exc_info=True)
            raise

    def enrich_securities(self) -> APIResponse:
        """Enrich securities data with additional information and update the database"""
        try:
            securities = self.security_repo.get_by_fields({ "type": SecurityType.EQUITY.value }, limit=None)
            enriched_data = []
            success = 0
            failed_tickers = []
            partial_tickers = []

            for index, security in enumerate(securities):
                logger.info(f"Enriching security {index + 1}/{len(securities)}: {security.ticker} ({security.exchange})")
                ticker = security.ticker
                try:
                    data = yf.Ticker(f"{ticker}.NS")
                    info = data.info

                    if not info.get("longName") or not info.get("sector") or not info.get("industry"):
                        partial_tickers.append(ticker)
                        logger.warning(f"Partial data for ticker {ticker}. Missing fields: {[field for field in ['longName', 'sector', 'industry'] if not info.get(field)]}")

                    enriched_data.append({ "ticker": ticker, "exchange": security.exchange, "display_name": info.get("longName"), "sector": info.get("sector"), "industry": info.get("industry") })
                    success += 1
                except Exception as e:
                    failed_tickers.append(ticker)
                    logger.warning(f"Failed to fetch data for ticker {ticker}. Error: {str(e)}", exc_info=True)

            self.security_repo.bulk_update_metadata(enriched_data)
            return APIResponse(success=True, message="SECURITIES_ENRICHED", data={ "enriched_securities": success, "failed_securities": failed_tickers, "partial_securities": partial_tickers })
        except Exception as e:
            logger.error(f"Failed to enrich securities data. Error: {str(e)}", exc_info=True)
            raise
