"""Screener service for unauthenticated security enrichment scraping."""

import time
from difflib import SequenceMatcher
from typing import Optional

from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests

from utils.logger import logger


class ScreenerService:
    """Service to scrape company enrichment data from screener.in without login."""

    def __init__(self) -> None:
        self.base_url = 'https://www.screener.in'
        self.search_api = f'{self.base_url}/api/company/search/'
        self.session = curl_requests.Session(impersonate='chrome120')
        self.session.headers.update({
            'Accept-Language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': f'{self.base_url}/dash/',
        })

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Return fuzzy similarity score between two company names."""

        def normalize(name: str) -> str:
            normalized = name.lower().strip()
            for suffix in (' ltd', ' limited', ' corporation', ' corp', ' inc'):
                normalized = normalized.replace(suffix, '')
            return normalized.strip()

        return SequenceMatcher(None, normalize(name1), normalize(name2)).ratio()

    def search_company(self, query: str) -> list[dict] | None:
        """Search company candidates by ticker or display name."""
        if not query.strip():
            return None

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.get(
                    self.search_api,
                    params={
                        'q': query.strip(),
                        'v': '3',
                        'fts': '1'
                    },
                    headers={
                        'Accept': 'application/json, text/javascript, */*; q=0.01',
                        'X-Requested-With': 'XMLHttpRequest',
                        'Sec-Fetch-Dest': 'empty',
                        'Sec-Fetch-Mode': 'cors',
                        'Sec-Fetch-Site': 'same-origin'
                    },
                    timeout=15,
                )

                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        time.sleep((2**attempt) * 3)
                        continue
                    return None

                if response.status_code != 200:
                    if attempt < max_retries - 1:
                        time.sleep(2**attempt)
                        continue
                    return None

                data = response.json()
                results = [item for item in data if item.get('id') is not None and 'full-text-search' not in str(item.get('url', ''))]
                return results or None
            except Exception as exc:
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)
                    continue
                logger.error(f'Screener search failed for {query}: {exc}')
                return None

        return None

    def find_best_match(self, results: list[dict], ticker: str, display_name: str) -> Optional[dict]:
        """Select the best screener search result using ticker and name similarity."""
        if not results:
            return None

        ticker_normalized = ticker.strip().upper()
        exact_ticker_match = None

        best_result = None
        best_score = 0.0

        for item in results:
            candidate_name = str(item.get('name', '')).strip()
            candidate_url = str(item.get('url', '')).strip().upper()
            if ticker_normalized and ticker_normalized in candidate_url:
                exact_ticker_match = item
                break

            score = self._calculate_name_similarity(candidate_name, display_name)
            if score > best_score:
                best_score = score
                best_result = item

        if exact_ticker_match is not None:
            return exact_ticker_match

        if best_result is not None and best_score >= 0.55:
            return best_result

        return results[0]

    def fetch_company_page(self, company_url: str) -> Optional[str]:
        """Fetch company page HTML from screener.in."""
        if not company_url:
            return None

        if company_url.startswith('http'):
            full_url = company_url
        else:
            full_url = f"{self.base_url}/{company_url.lstrip('/')}"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.get(
                    full_url,
                    headers={
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'same-origin',
                        'Sec-Fetch-User': '?1'
                    },
                    timeout=20,
                )

                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        time.sleep((2**attempt) * 4)
                        continue
                    return None

                if response.status_code == 200:
                    return response.text

                if attempt < max_retries - 1:
                    time.sleep(2**attempt)
                    continue
                return None
            except Exception as exc:
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)
                    continue
                logger.error(f'Failed to fetch screener page {full_url}: {exc}')
                return None

        return None

    def parse_sector_info(self, html_content: str) -> dict[str, Optional[str]]:
        """Parse enrichment sector fields from screener company page HTML."""
        parsed = {'macro_economic_sector': None, 'sector': None, 'industry': None, 'basic_industry': None}

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            peers_section = soup.find('section', id='peers')
            if not peers_section:
                return parsed

            sub_line = peers_section.find('p', class_='sub')
            if not sub_line:
                return parsed

            links = sub_line.find_all('a', title=True)
            for link in links:
                title = str(link.get('title', '')).strip()
                value = link.get_text(strip=True)
                if not value:
                    continue

                if title == 'Broad Sector':
                    parsed['macro_economic_sector'] = value
                elif title == 'Sector':
                    parsed['sector'] = value
                elif title == 'Broad Industry':
                    parsed['industry'] = value
                elif title == 'Industry':
                    parsed['basic_industry'] = value

        except Exception as exc:
            logger.error(f'Failed to parse sector info: {exc}')

        return parsed

    def scrape_company_enrichment(self, ticker: str, display_name: str) -> dict[str, str] | None:
        """Run search -> match -> page fetch -> parse and return enrichment fields."""
        search_results = self.search_company(ticker)
        if not search_results and display_name.strip():
            search_results = self.search_company(display_name)
        if not search_results:
            return None

        best_match = self.find_best_match(search_results, ticker, display_name)
        if not best_match:
            return None

        company_url = str(best_match.get('url', '')).strip()
        html = self.fetch_company_page(company_url)
        if not html:
            return None

        parsed = self.parse_sector_info(html)
        has_any = any(parsed.get(field) for field in ('macro_economic_sector', 'sector', 'industry', 'basic_industry'))
        return parsed if has_any else None

    def close(self) -> None:
        """Close underlying HTTP session."""
        if self.session:
            self.session.close()
