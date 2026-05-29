"""Browser-based scraper using Playwright for JS-rendered pages."""

import asyncio
import logging
import re
from typing import List

from .base_scraper import BaseScraper, JobPosting
from ..utils.helpers import normalize_url, clean_text
from ..utils.keywords import matches_role_keywords, is_us_location

logger = logging.getLogger(__name__)

MAX_PAGES = 10

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


def _try_parse_date(text):
    if not text:
        return ''
    import re
    from datetime import datetime
    from dateutil import parser as dp
    try:
        lower = text.lower()
        if 'just' in lower or 'today' in lower or 'hour' in lower \
                or 'minute' in lower:
            return datetime.now().isoformat()
        if 'yesterday' in lower:
            from datetime import timedelta
            return (datetime.now() - timedelta(days=1)).isoformat()
        m = re.search(r'(\d+)\s*day', lower)
        if m:
            from datetime import timedelta
            return (
                datetime.now() - timedelta(days=int(m.group(1)))
            ).isoformat()
        return dp.parse(text, fuzzy=True).isoformat()
    except Exception:
        return ''


def _build_paginated_url(base_url: str, page_num: int) -> str:
    """Try common pagination URL patterns."""
    # If page parameter already in URL, replace it
    patterns = [
        (r'([?&])page=\d+', rf'\g<1>page={page_num}'),
        (r'([?&])p=\d+', rf'\g<1>p={page_num}'),
        (r'([?&])startrow=\d+',
         rf'\g<1>startrow={(page_num - 1) * 25}'),
        (r'([?&])offset=\d+',
         rf'\g<1>offset={(page_num - 1) * 25}'),
        (r'([?&])from=\d+',
         rf'\g<1>from={(page_num - 1) * 10}'),
    ]
    for pattern, replacement in patterns:
        if re.search(pattern, base_url):
            return re.sub(pattern, replacement, base_url)

    # No existing pagination param: append page= for page > 1
    if page_num == 1:
        return base_url
    sep = '&' if '?' in base_url else '?'
    return f"{base_url}{sep}page={page_num}"


class PlaywrightScraper(BaseScraper):
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
        all_results = []
        seen_urls = set()
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

            # ALWAYS start at page 1 and iterate up to MAX_PAGES
            for page_num in range(1, MAX_PAGES + 1):
                page_url = _build_paginated_url(
                    self.base_url, page_num
                )

                try:
                    await page.goto(
                        page_url,
                        wait_until='domcontentloaded',
                        timeout=45000
                    )
                except Exception as e:
                    logger.warning(
                        f"[{self.company_name}] page "
                        f"{page_num} nav error: {e}"
                    )
                    break

                if self.wait_selector:
                    try:
                        await page.wait_for_selector(
                            self.wait_selector, timeout=10000
                        )
                    except Exception:
                        pass

                await page.wait_for_timeout(
                    self.wait_seconds * 1000
                )

                # On page 1, try to click "sort by most recent"
                if page_num == 1:
                    await self._try_sort_by_date(page)
                    await page.wait_for_timeout(2000)

                html = await page.content()
                page_results = self._parse_html(html, page.url)

                # Track new links from this page
                new_count = 0
                for r in page_results:
                    if r.url not in seen_urls:
                        seen_urls.add(r.url)
                        all_results.append(r)
                        new_count += 1

                logger.debug(
                    f"[{self.company_name}] page {page_num}: "
                    f"{len(page_results)} found, "
                    f"{new_count} new"
                )

                # If this page added 0 new postings, stop early
                if new_count == 0 and page_num > 1:
                    break

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

        # Sort newest-first
        all_results.sort(
            key=lambda p: p.date_posted or '',
            reverse=True
        )
        return all_results

    async def _try_sort_by_date(self, page):
        """Try clicking common 'Most Recent' sort controls."""
        sort_candidates = [
            'button:has-text("Most Recent")',
            'button:has-text("Newest")',
            'button:has-text("Date Posted")',
            'button:has-text("Sort by Date")',
            'option:has-text("Most Recent")',
            'option:has-text("Newest")',
            'a:has-text("Most Recent")',
            'a:has-text("Newest")',
            '[aria-label*="ort"]',
            '[data-sort*="date"]',
        ]
        for selector in sort_candidates:
            try:
                el = await page.query_selector(selector)
                if el:
                    await el.click(timeout=2000)
                    await page.wait_for_timeout(1500)
                    return
            except Exception:
                continue

    def _parse_html(self, html: str, current_url: str):
        from bs4 import BeautifulSoup
        results = []
        seen = set()

        soup = BeautifulSoup(html, 'lxml')

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
            parent = link.find_parent(
                ['div', 'li', 'article', 'tr']
            )

            if (not title or len(title) < 3) and parent:
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

            location = ''
            date_str = ''
            if parent:
                loc_el = parent.select_one(
                    '[class*="location"], [class*="city"], '
                    '.region, [data-automation*="location"]'
                )
                if loc_el:
                    location = clean_text(loc_el.get_text())

                date_el = parent.select_one(
                    '[class*="date"], [class*="posted"], '
                    'time, [datetime]'
                )
                if date_el:
                    raw = date_el.get('datetime') or \
                          clean_text(date_el.get_text())
                    date_str = _try_parse_date(raw)

            if self.filter_internships and \
                    not matches_role_keywords(title):
                continue
            if location and not is_us_location(location):
                continue

            results.append(JobPosting(
                title=title,
                company=self.company_name,
                url=job_url,
                date_posted=date_str,
                location=location or 'N/A',
            ))

        return results
