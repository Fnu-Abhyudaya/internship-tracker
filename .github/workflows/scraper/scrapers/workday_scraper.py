"""Scraper for Workday-based career pages."""

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

    async def _search_one_keyword(self, api_url, base_params,
                                  host, site_path, keyword):
        """Run a single keyword search and return postings."""
        results = []
        params = dict(base_params)
        params['searchText'] = keyword
        params['offset'] = 0

        for _ in range(5):  # max 5 pages per keyword
            data = await self.fetch_json(api_url, params=params)
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
            params['offset'] += len(postings)
            if params['offset'] >= total:
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
            api_url = f"{host}/wday/cxs/{parsed.hostname.split('.')[0]}/{site_path}/jobs"

            base_params = {'limit': 20}
            if parsed.query:
                qs = parse_qs(parsed.query)
                for key, values in qs.items():
                    if key == 'workerSubType':
                        base_params['workerSubType'] = values
                    elif key == 'locationCountry':
                        base_params['locationCountry'] = values[0]
            base_params.update(self.search_params)

            # Try POST-style API first (newer Workday)
            for keyword in SEARCH_KEYWORDS:
                kw_results = await self._search_one_keyword(
                    api_url, base_params, host, site_path, keyword
                )
                all_results.extend(kw_results)

            # If nothing found, try the older REST API style
            if not all_results:
                alt_api = f"{host}/api/v1/{site_path}/jobs"
                for keyword in SEARCH_KEYWORDS:
                    kw_results = await self._search_one_keyword(
                        alt_api, base_params, host,
                        site_path, keyword
                    )
                    all_results.extend(kw_results)

        except Exception as e:
            logger.error(
                f"[{self.company_name}] Workday error: {e}"
            )

        # Deduplicate by URL
        seen = set()
        unique = []
        for r in all_results:
            if r.url not in seen:
                seen.add(r.url)
                unique.append(r)
        return unique
