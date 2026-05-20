import logging
from typing import List

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, JobPosting
from ..utils.helpers import (
    is_internship_role, normalize_url, clean_text
)

logger = logging.getLogger(__name__)


class ICIMSScraper(BaseScraper):
    def __init__(self, company_name: str, base_url: str,
                 filter_internships: bool = True):
        super().__init__(company_name, base_url)
        self.filter_internships = filter_internships

    async def scrape(self) -> List[JobPosting]:
        results = []
        try:
            for page_num in range(1, 6):
                url = self.base_url
                url += f'&pr={page_num}' if '?' in url \
                    else f'?pr={page_num}'

                html = await self.fetch(url)
                if not html:
                    break

                soup = BeautifulSoup(html, 'lxml')
                job_rows = soup.select(
                    '.iCIMS_JobsTable .row, '
                    '.iCIMS-JobList .iCIMS-JobListItem, '
                    'div[class*="job"]'
                )

                if not job_rows:
                    job_rows = soup.select('a[href*="/jobs/"]')

                found_any = False
                for row in job_rows:
                    link_tag = row if row.name == 'a' else \
                        row.select_one('a[href*="/jobs/"]')
                    if not link_tag:
                        continue

                    title = clean_text(link_tag.get_text())
                    href = link_tag.get('href', '')
                    if not title or len(title) < 3:
                        continue

                    found_any = True
                    job_url = normalize_url(self.base_url, href)

                    if self.filter_internships and \
                            not is_internship_role(title):
                        continue

                    results.append(JobPosting(
                        title=title,
                        company=self.company_name,
                        url=job_url,
                    ))

                if not found_any:
                    break

        except Exception as e:
            logger.error(
                f"[{self.company_name}] iCIMS error: {e}"
            )

        return results
