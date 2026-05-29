"""Scraper for SAP SuccessFactors career sites.

These sites have a predictable URL structure with a JSON
endpoint and support sort by date desc.
Examples: jobs.ametek.com, jobs.bd.com, jobs.danfoss.com
"""

import json
import logging
import re
from typing import List
from urllib.parse import urlparse, urlencode, parse_qs

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, JobPosting
from ..utils.helpers import normalize_url, clean_text
from ..utils.keywords import (
    matches_role_keywords, is_us_location, SEARCH_KEYWORDS
)

logger = logging.getLogger(__name__)

MAX_PAGES = 10
PAGE_SIZE = 25


class SuccessFactorsScraper(BaseScraper):
    """Scraper for SAP SuccessFactors career sites."""

    def __init__(self, company_name, base_url,
                 filter_internships=True):
        super().__init__(company_name, base_url)
        self.filter_internships = filter_internships

    async def _fetch_search_page(self, search_url):
        """Fetch one HTML page of search results."""
        html = await self.fetch(search_url)
        return html

    def _parse_search_results(self, html, base):
        """Parse SuccessFactors search results HTML."""
        results = []
        if not html:
            return results

        soup = BeautifulSoup(html, 'lxml')

        # SuccessFactors job rows
        job_rows = soup.select(
            '.jobTitle-link, '
            'a.jobTitle-link, '
            'tr.data-row, '
            '.searchResultItem, '
            'li.list-item-bg, '
            '[data-careersection-job-id], '
            'a[href*="/job/"]'
        )

        # If nothing matched, fallback to all job links
        if not job_rows:
            job_rows = soup.select('a[href*="/job/"]')

        seen = set()
        for row in job_rows:
            # Find the link
            if row.name == 'a':
                link = row
            else:
                link = row.select_one('a[href*="/job/"]')
                if not link:
                    link = row.select_one('a')
            if not link:
                continue

            title = clean_text(link.get_text())
            if not title or len(title) < 3:
                # Try parent for title
                parent = link.find_parent(['tr', 'li', 'div'])
                if parent:
                    for sel in ['.jobTitle', 'h2', 'h3', 'h4']:
                        t = parent.select_one(sel)
                        if t:
                            title = clean_text(t.get_text())
                            break

            if not title:
                continue

            href = link.get('href', '')
            if not href or href.startswith('#'):
                continue

            job_url = normalize_url(base, href)
            if job_url in seen:
                continue
            seen.add(job_url)

            # Extract location & date from nearby siblings
            location = ''
            date_str = ''
            container = link.find_parent(
                ['tr', 'li', 'div', 'article']
            )
            if container:
                loc_el = container.select_one(
                    '.jobLocation, .job-location, '
                    '[class*="location"], [class*="Location"]'
                )
                if loc_el:
                    location = clean_text(loc_el.get_text())

                date_el = container.select_one(
                    '.jobDate, '
                    '[class*="date"], [class*="Date"], '
                    '[class*="posted"], time'
                )
                if date_el:
                    date_str = (
                        date_el.get('datetime') or
                        clean_text(date_el.get_text())
                    )

            # Apply filters
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

    def _build_search_url(self, keyword, page_num):
        """Build a SuccessFactors search URL with sort + page."""
        parsed = urlparse(self.base_url)
        base = f"{parsed.scheme}://{parsed.hostname}"

        # Parse existing query params and add ours
        existing = parse_qs(parsed.query)
        # Flatten single-value lists
        params = {
            k: (v[0] if len(v) == 1 else v)
            for k, v in existing.items()
        }

        # SuccessFactors standard sort & pagination params
        params['q'] = keyword
        params['sortColumn'] = 'referencedate'
        params['sortDirection'] = 'desc'
        params['startrow'] = (page_num - 1) * PAGE_SIZE

        # Reconstruct URL preserving original path
        path = parsed.path or '/search/'
        if 'search' not in path.lower():
            path = path.rstrip('/') + '/search/'

        return f"{base}{path}?{urlencode(params, doseq=True)}"

    async def scrape(self) -> List[JobPosting]:
        all_results = []
        seen_urls = set()

        try:
            parsed = urlparse(self.base_url)
            base = f"{parsed.scheme}://{parsed.hostname}"

            for keyword in SEARCH_KEYWORDS:
                for page_num in range(1, MAX_PAGES + 1):
                    search_url = self._build_search_url(
                        keyword, page_num
                    )
                    html = await self._fetch_search_page(
                        search_url
                    )
                    if not html:
                        break

                    page_results = self._parse_search_results(
                        html, base
                    )

                    new_count = 0
                    for r in page_results:
                        if r.url not in seen_urls:
                            seen_urls.add(r.url)
                            all_results.append(r)
                            new_count += 1

                    logger.debug(
                        f"[{self.company_name}] '{keyword}' "
                        f"page {page_num}: "
                        f"{len(page_results)} found, "
                        f"{new_count} new"
                    )

                    # Stop if no new results on this page
                    if new_count == 0:
                        break

        except Exception as e:
            logger.error(
                f"[{self.company_name}] SuccessFactors error: {e}"
            )

        all_results.sort(
            key=lambda p: p.date_posted or '',
            reverse=True
        )
        return all_results
