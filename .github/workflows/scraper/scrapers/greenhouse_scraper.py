import logging
from typing import List
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, JobPosting
from ..utils.helpers import (
    is_within_last_24_hours, is_internship_role,
    normalize_url, clean_text
)

logger = logging.getLogger(__name__)


class GreenhouseScraper(BaseScraper):
    def __init__(self, company_name: str, base_url: str,
                 board_token: str = None,
                 filter_internships: bool = True,
                 office_ids: list = None):
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
                return await self._scrape_html()

            for job in data.get('jobs', []):
                title = job.get('title', '')
                job_id = job.get('id', '')
                updated_at = job.get('updated_at', '')
                abs_url = job.get('absolute_url', '')
                location_name = ''
                loc = job.get('location', {})
                if loc:
                    location_name = loc.get('name', '')

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
                        not is_internship_role(title):
                    continue

                if not is_within_last_24_hours(updated_at):
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
                    location=location_name,
                ))

        except Exception as e:
            logger.error(
                f"[{self.company_name}] Greenhouse error: {e}"
            )

        return results

    async def _scrape_html(self) -> List[JobPosting]:
        results = []
        html = await self.fetch(self.base_url)
        if not html:
            return results

        soup = BeautifulSoup(html, 'lxml')
        for opening in soup.select('.opening'):
            link_tag = opening.select_one('a')
            if not link_tag:
                continue
            title = clean_text(link_tag.get_text())
            href = link_tag.get('href', '')
            job_url = normalize_url(
                'https://boards.greenhouse.io', href
            )
            location = ''
            loc_tag = opening.select_one('.location')
            if loc_tag:
                location = clean_text(loc_tag.get_text())
            if self.filter_internships and \
                    not is_internship_role(title):
                continue
            results.append(JobPosting(
                title=title,
                company=self.company_name,
                url=job_url,
                location=location,
            ))

        return results
