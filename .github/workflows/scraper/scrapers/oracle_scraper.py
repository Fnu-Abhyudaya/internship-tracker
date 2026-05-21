"""Scraper for Oracle Cloud HCM career pages."""

import logging
from typing import List
from urllib.parse import urlparse

from .base_scraper import BaseScraper, JobPosting
from ..utils.helpers import is_within_last_24_hours
from ..utils.keywords import (
    matches_role_keywords, is_us_location, SEARCH_KEYWORDS
)

logger = logging.getLogger(__name__)


class OracleHCMScraper(BaseScraper):
    def __init__(self, company_name, base_url,
                 filter_internships=True, keyword=None):
        super().__init__(company_name, base_url)
        self.filter_internships = filter_internships

    async def _fetch_keyword(self, api_url, site_name,
                             base_host, keyword):
        results = []
        finder = (
            f'findReqs;siteNumber={site_name},'
            f'keyword={keyword},locationId=300000000149325'
        )
        params = {
            'onlyData': 'true',
            'finder': finder,
            'limit': 25,
            'offset': 0,
        }
        for _ in range(5):
            data = await self.fetch_json(api_url, params=params)
            if not data:
                break

            items = data.get('items', [])
            if items and isinstance(items[0], dict) and \
                    'requisitionList' in items[0]:
                items = items[0].get('requisitionList', [])

            if not items:
                break

            for item in items:
                title = item.get('Title', '') or item.get('title', '')
                req_id = item.get('Id', '') or item.get('id', '')
                posted = (
                    item.get('PostedDate', '') or
                    item.get('postedDate', '')
                )
                loc = (
                    item.get('PrimaryLocation', '') or
                    item.get('primaryLocation', '')
                )

                if self.filter_internships and \
                        not matches_role_keywords(title):
                    continue
                if not is_within_last_24_hours(posted):
                    continue
                if not is_us_location(loc):
                    continue

                job_url = (
                    f"{base_host}/hcmUI/CandidateExperience/"
                    f"en/sites/{site_name}/job/{req_id}"
                )
                results.append(JobPosting(
                    title=title,
                    company=self.company_name,
                    url=job_url,
                    date_posted=posted,
                    location=loc or 'N/A',
                ))

            if len(items) < 25:
                break
            params['offset'] += 25

        return results

    async def scrape(self) -> List[JobPosting]:
        all_results = []
        try:
            parsed = urlparse(self.base_url)
            base_host = f"{parsed.scheme}://{parsed.hostname}"
            path_parts = [p for p in parsed.path.split('/') if p]
            site_name = ''
            for i, part in enumerate(path_parts):
                if part == 'sites' and i + 1 < len(path_parts):
                    site_name = path_parts[i + 1]
                    break

            api_url = (
                f"{base_host}/hcmRestApi/resources/latest/"
                f"recruitingCEJobRequisitions"
            )

            for keyword in SEARCH_KEYWORDS:
                kw_results = await self._fetch_keyword(
                    api_url, site_name, base_host, keyword
                )
                all_results.extend(kw_results)

        except Exception as e:
            logger.error(
                f"[{self.company_name}] Oracle HCM error: {e}"
            )

        # Dedupe
        seen = set()
        unique = []
        for r in all_results:
            if r.url not in seen:
                seen.add(r.url)
                unique.append(r)
        return unique
