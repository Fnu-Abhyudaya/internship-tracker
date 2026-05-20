import logging
from typing import List

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, JobPosting
from ..utils.helpers import (
    is_within_last_24_hours, is_internship_role,
    normalize_url, clean_text
)

logger = logging.getLogger(__name__)


class TaleoScraper(BaseScraper):
    def __init__(self, company_name: str, base_url: str,
                 filter_internships: bool = True):
        super().__init__(company_name, base_url)
        self.filter_internships = filter_internships

    async def scrape(self) -> List[JobPosting]:
        results = []
        try:
            html = await self.fetch(self.base_url)
            if not html:
                return results

            soup = BeautifulSoup(html, 'lxml')
            job_rows = soup.select(
                'tr.dataRow, .requisition-list-item, '
                '.job-listing, [class*="requisition"]'
            )

            for row in job_rows:
                link_tag = row.select_one('a')
                if not link_tag:
                    continue

                title = clean_text(link_tag.get_text())
                href = link_tag.get('href', '')
                job_url = normalize_url(self.base_url, href)

                if self.filter_internships and \
                        not is_internship_role(title):
                    continue

                date_text = ''
                date_el = row.select_one(
                    'td:last-child, .date, [class*="date"]'
                )
                if date_el:
                    date_text = clean_text(date_el.get_text())

                if date_text and \
                        not is_within_last_24_hours(date_text):
                    continue

                results.append(JobPosting(
                    title=title,
                    company=self.company_name,
                    url=job_url,
                    date_posted=date_text,
                ))

        except Exception as e:
            logger.error(
                f"[{self.company_name}] Taleo error: {e}"
            )

        return results
