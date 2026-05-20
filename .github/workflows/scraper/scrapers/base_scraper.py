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
                    return await response.text()
                else:
                    logger.warning(
                        f"[{self.company_name}] "
                        f"HTTP {response.status} for {url}"
                    )
                    return None
        except Exception as e:
            logger.error(
                f"[{self.company_name}] Error fetching {url}: {e}"
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
                    return await response.json(content_type=None)
                else:
                    logger.warning(
                        f"[{self.company_name}] "
                        f"HTTP {response.status}"
                    )
                    return None
        except Exception as e:
            logger.error(
                f"[{self.company_name}] JSON error: {e}"
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
            return []
        finally:
            await self.close_session()
