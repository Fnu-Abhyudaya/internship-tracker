"""Browser-based scraper using Playwright for JS-rendered pages."""

import asyncio
import logging
import re
from typing import List

from .base_scraper import BaseScraper, JobPosting
from ..utils.helpers import (
    is_within_last_24_hours, normalize_url, clean_text
)
from ..utils.keywords import matches_role_keywords, is_us_location

logger = logging.getLogger(__name__)

# Shared browser instance (created on first use)
_browser = None
_playwright = None
_browser_lock = asyncio.Lock()


async def get_browser():
    global _browser, _playwright
    async with _browser_lock:
        if _browser is None:
            from playwright.async_api import async_playwright
            _playwright = await async_playwright().start()
            _browser = await _playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                ]
            )
    return _browser


async def shutdown_browser():
    global _browser, _playwright
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright:
        await _playwright.stop()
        _playwright = None


class PlaywrightScraper(BaseScraper):
    """Scraper that uses Playwright to render JavaScript pages."""

    def __init__(self, company_name, base_url,
                 wait_selector=None,
                 job_link_pattern=None,
                 filter_internships=True,
                 wait_seconds=4):
        super().__init__(company_name, base_url)
        self.wait_selector = wait_selector
        self.job_link_pattern = job_link_pattern
        self.filter_internships = filter_internships
        self.wait_seconds = wait_seconds

    async def scrape(self) -> List[JobPosting]:
        results = []
        page = None
        context = None
        try:
            browser = await get_browser()
            context = await browser.new_context(
                user_agent=(
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
                viewport={'width': 1920, 'height': 1080},
            )
            page = await context.new_page()
            page.set_default_timeout(45000)

            await page.goto(
                self.base_url,
                wait_until='domcontentloaded',
                timeout=45000
            )

            # Wait for content to load
            if self.wait_selector:
                try:
                    await page.wait_for_selector(
                        self.wait_selector, timeout=15000
                    )
                except Exception:
                    pass

            # Extra wait for JS rendering
            await page.wait_for_timeout(
                self.wait_seconds * 1000
            )

            # Get rendered HTML
            html = await page.content()
            results = self._parse_html(html, page.url)

        except Exception as e:
            logger.error(
                f"[{self.company_name}] Playwright error: {e}"
            )
        finally:
            try:
                if page:
                    await page.close()
                if context:
                    await context.close()
            except Exception:
                pass

        return results

    def _parse_html(self, html: str, current_url: str):
        from bs4 import BeautifulSoup
        results = []
        seen = set()

        soup = BeautifulSoup(html, 'lxml')

        # Strategy 1: Look for structured job listing containers
        selectors = [
            'a[href*="/job/"]',
            'a[href*="/jobs/"]',
            'a[href*="/career"]',
            'a[href*="/position"]',
            'a[href*="/opening"]',
            'a[href*="JobDetail"]',
            'a[href*="job-details"]',
            'a[href*="requisition"]',
            'a[href*="JobReq"]',
            'a[href*="?id="]',
            'a[href*="jobId"]',
        ]

        all_links = []
        for sel in selectors:
            all_links.extend(soup.select(sel))

        # Also generic patterns
        if self.job_link_pattern:
            for link in soup.select('a[href]'):
                href = link.get('href', '')
                if re.search(
                    self.job_link_pattern, href, re.IGNORECASE
                ):
                    all_links.append(link)

        for link in all_links:
            href = link.get('href', '')
            if not href or href.startswith('#'):
                continue

            title = clean_text(link.get_text())

            # Try parent for richer text
            if not title or len(title) < 3:
                parent = link.find_parent(
                    ['div', 'li', 'article', 'tr']
                )
                if parent:
                    for sel in [
                        '.title', '.job-title', 'h2',
                        'h3', 'h4', '[class*="title"]'
                    ]:
                        t_el = parent.select_one(sel)
                        if t_el:
                            title = clean_text(t_el.get_text())
                            break

            if not title or len(title) < 3:
                continue

            job_url = normalize_url(current_url, href)
            if job_url in seen:
                continue
            seen.add(job_url)

            # Try to extract location from nearby element
            location = ''
            parent = link.find_parent(
                ['div', 'li', 'article', 'tr']
            )
            if parent:
                loc_el = parent.select_one(
                    '[class*="location"], [class*="city"], '
                    '.region, [data-automation*="location"]'
                )
                if loc_el:
                    location = clean_text(loc_el.get_text())

            if self.filter_internships and \
                    not matches_role_keywords(title):
                continue

            # Lenient location filter - only reject if clearly non-US
            if location and not is_us_location(location):
                continue

            results.append(JobPosting(
                title=title,
                company=self.company_name,
                url=job_url,
                location=location or 'N/A',
            ))

        return results
