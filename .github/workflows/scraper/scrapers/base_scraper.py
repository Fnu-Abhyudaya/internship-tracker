import logging
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class JobPosting:
    title: str
    company: str
    url: str
    date_posted: Optional[str] = None
    location: Optional[str] = None
    scraped_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )

    def to_dict(self) -> dict:
        return {
            'Role': self.title,
            'Company': self.company,
            'Link': self.url,
            'Date Posted': self.date_posted or 'N/A',
            'Location': self.location or 'N/A',
        }


class BaseScraper(ABC):
    def __init__(self, company_name: str, base_url: str,
                 rate_limit: float = 1.0):
        self.company_name = company_name
        self.base_url = base_url
        self.rate_limit = rate_limit
        self.session: Optional[aiohttp.ClientSession] = None
        # Scan-health tracking (reported in the Excel "Scan Issues" sheet)
        self.errors: List[str] = []
        self.pages_ok: int = 0
        self.headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': (
                'text/html,application/xhtml+xml,application/xml;'
                'q=0.9,*/*;q=0.8'
            ),
            'Accept-Language': 'en-US,en;q=0.5',
        }

    def record_error(self, message: str):
        """Remember a problem hit while scanning this site."""
        message = ' '.join(str(message).split())
        if len(message) > 300:
            message = message[:297] + '...'
        self.errors.append(message)

    def record_success(self):
        """Note that a page/API request for this site loaded fine."""
        self.pages_ok += 1

    @staticmethod
    def describe_exception(e: Exception) -> str:
        text = str(e).strip()
        name = type(e).__name__
        return f"{name}: {text}" if text else name

    async def create_session(self):
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(limit=5, ssl=False)
            self.session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout,
                connector=connector
            )

    async def close_session(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def fetch(self, url: str,
                    params: dict = None) -> Optional[str]:
        try:
            await self.create_session()
            await asyncio.sleep(self.rate_limit)
            async with self.session.get(
                url, params=params, allow_redirects=True
            ) as response:
                if response.status == 200:
                    self.record_success()
                    return await response.text()
                else:
                    logger.warning(
                        f"[{self.company_name}] "
                        f"HTTP {response.status} for {url}"
                    )
                    self.record_error(
                        f"HTTP {response.status} when loading {url}"
                    )
                    return None
        except Exception as e:
            logger.error(
                f"[{self.company_name}] Error fetching {url}: {e}"
            )
            self.record_error(
                f"Could not load {url} "
                f"({self.describe_exception(e)})"
            )
            return None

    async def fetch_json(self, url: str,
                         params: dict = None) -> Optional[dict]:
        try:
            await self.create_session()
            await asyncio.sleep(self.rate_limit)
            async with self.session.get(
                url, params=params, allow_redirects=True
            ) as response:
                if response.status == 200:
                    data = await response.json(content_type=None)
                    self.record_success()
                    return data
                else:
                    logger.warning(
                        f"[{self.company_name}] "
                        f"HTTP {response.status}"
                    )
                    self.record_error(
                        f"HTTP {response.status} from {url}"
                    )
                    return None
        except Exception as e:
            logger.error(
                f"[{self.company_name}] JSON error: {e}"
            )
            self.record_error(
                f"Bad/unreadable response from {url} "
                f"({self.describe_exception(e)})"
            )
            return None

    @abstractmethod
    async def scrape(self) -> List[JobPosting]:
        pass

    async def run(self) -> List[JobPosting]:
        try:
            logger.info(f"Scraping {self.company_name}...")
            results = await self.scrape()
            logger.info(
                f"[{self.company_name}] "
                f"Found {len(results)} postings"
            )
            return results
        except Exception as e:
            logger.error(
                f"[{self.company_name}] Scraper failed: {e}"
            )
            self.record_error(
                f"Scraper crashed: {self.describe_exception(e)}"
            )
            return []
        finally:
            await self.close_session()
