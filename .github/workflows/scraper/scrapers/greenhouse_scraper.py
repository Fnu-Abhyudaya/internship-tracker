"""Scraper for Greenhouse job board pages."""

import logging
from typing import List
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, JobPosting
from ..utils.helpers import (
    is_within_last_24_hours, normalize_url, clean_text
)
from ..utils.keywords import matches_role_keywords, is_us_location

logger = logging.getLogger(__name__)


class GreenhouseScraper(BaseScraper):
    def __init__(self, company_name, base_url, board_token=None,
                 filter_internships=True, office_ids=None):
        super().__init__(company_name, base_url)
        self.filter_internships = filter_internships
        self.office_ids = office_ids or []
        if board_token:
            self.board_token = board_token
        else:
            parsed = urlparse(base_url)
            parts = [p for p in parsed.path.split('/') if p]
            self.board_token = parts[0] if parts else ''

    async def scrape(self) -> List[JobPosting]:
        results = []
        try:
            api_url = (
                f"https://boards-api.greenhouse.io/v1/boards/"
                f"{self.board_token}/jobs"
            )
            data = await self.fetch_json(
                api_url, params={'content': 'true'}
            )
            if not data or 'jobs' not in data:
                return results

            for job in data.get('jobs', []):
                title = job.get('title', '')
                job_id = job.get('id', '')
                updated_at = job.get('updated_at', '')
                abs_url = job.get('absolute_url', '')
                loc = job.get('location', {})
                location_name = loc.get('name', '') if loc else ''

                if self.office_ids:
                    job_offices = [
                        str(o.get('id', ''))
                        for o in job.get('offices', [])
                    ]
                    if not any(
                        oid in job_offices
                        for oid in self.office_ids
                    ):
                        continue

                if self.filter_internships and \
                        not matches_role_keywords(title):
                    continue
                if not is_within_last_24_hours(updated_at):
                    continue
                if not is_us_location(location_name):
                    continue

                job_url = abs_url or (
                    f"https://boards.greenhouse.io/"
                    f"{self.board_token}/jobs/{job_id}"
                )
                results.append(JobPosting(
                    title=title,
                    company=self.company_name,
                    url=job_url,
                    date_posted=updated_at,
                    location=location_name or 'N/A',
                ))
        except Exception as e:
            logger.error(
                f"[{self.company_name}] Greenhouse error: {e}"
            )
        return results
