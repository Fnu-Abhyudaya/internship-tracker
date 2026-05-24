"""Scraper for Workday-based career pages."""

import json
import logging
from typing import List
from urllib.parse import urlparse, parse_qs

from .base_scraper import BaseScraper, JobPosting
from ..utils.helpers import is_within_last_24_hours
from ..utils.keywords import (
    matches_role_keywords, is_us_location, SEARCH_KEYWORDS
)

logger = logging.getLogger(__name__)


class WorkdayScraper(BaseScraper):
    def __init__(self, company_name, base_url,
                 search_params=None, filter_internships=True):
        super().__init__(company_name, base_url)
        self.search_params = search_params or {}
        self.filter_internships = filter_internships

    async def _post_search(self, api_url, payload):
        """POST to Workday's search API."""
        import aiohttp
        await self.create_session()
        try:
            headers = dict(self.headers)
            headers['Content-Type'] = 'application/json'
            headers['Accept'] = 'application/json'
            async with self.session.post(
                api_url, json=payload, headers=headers,
                allow_redirects=True
            ) as response:
                if response.status == 200:
                    return await response.json(content_type=None)
                logger.warning(
                    f"[{self.company_name}] "
                    f"POST {api_url} returned {response.status}"
                )
        except Exception as e:
            logger.error(
                f"[{self.company_name}] POST error: {e}"
            )
        return None

    async def _search_one_keyword(self, api_url, host,
                                  site_path, keyword):
        """Run a single keyword search, requesting newest first."""
        results = []
        offset = 0

        for _ in range(5):
            # Workday returns by posting date desc by default
            payload = {
                'appliedFacets': {},
                'limit': 20,
                'offset': offset,
                'searchText': keyword,
            }
            data = await self._post_search(api_url, payload)
            if not data or 'jobPostings' not in data:
                break

            postings = data.get('jobPostings', [])
            if not postings:
                break

            for posting in postings:
                title = posting.get('title', '')
                posted_on = posting.get('postedOn', '')
                external_path = posting.get('externalPath', '')
                locs = posting.get('locationsText', '')

                if self.filter_internships and \
                        not matches_role_keywords(title):
                    continue
                if not is_within_last_24_hours(posted_on):
                    continue
                if not is_us_location(locs):
                    continue

                job_url = (
                    f"{host}/{site_path}{external_path}"
                    if external_path else self.base_url
                )
                results.append(JobPosting(
                    title=title,
                    company=self.company_name,
                    url=job_url,
                    date_posted=posted_on,
                    location=locs or 'N/A',
                ))

            total = data.get('total', 0)
            offset += len(postings)
            if offset >= total:
                break

        return results

    async def scrape(self) -> List[JobPosting]:
        all_results = []
        try:
            parsed = urlparse(self.base_url)
            host = f"{parsed.scheme}://{parsed.hostname}"
            path_parts = [
                p for p in parsed.path.split('/')
                if p and p != 'en-US'
            ]
            site_path = path_parts[0] if path_parts else ''
            tenant = parsed.hostname.split('.')[0]

            # Workday CXS API endpoint
            api_url = (
                f"{host}/wday/cxs/{tenant}/{site_path}/jobs"
            )

            for keyword in SEARCH_KEYWORDS:
                kw_results = await self._search_one_keyword(
                    api_url, host, site_path, keyword
                )
                all_results.extend(kw_results)

        except Exception as e:
            logger.error(
                f"[{self.company_name}] Workday error: {e}"
            )

        # Dedupe by URL
        seen = set()
        unique = []
        for r in all_results:
            if r.url not in seen:
                seen.add(r.url)
                unique.append(r)

        # Sort newest-first
        unique.sort(
            key=lambda p: p.date_posted or '',
            reverse=True
        )
        return unique
