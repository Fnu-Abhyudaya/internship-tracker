"""Scraper for Taleo career pages."""

import logging
from typing import List

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, JobPosting
from ..utils.helpers import normalize_url, clean_text
from ..utils.keywords import matches_role_keywords, is_us_location

logger = logging.getLogger(__name__)

MAX_PAGES = 10


class TaleoScraper(BaseScraper):
    def __init__(self, company_name, base_url,
                 filter_internships=True):
        super().__init__(company_name, base_url)
        self.filter_internships = filter_internships

    async def scrape(self) -> List[JobPosting]:
        results = []
        try:
            # Taleo URLs use pageNo parameter, start at 1
            for page_num in range(1, MAX_PAGES + 1):
                url = self.base_url
                # Add sort & pagination
                extras = (
                    f'jobReqType=ALL&pageNo={page_num}&'
                    f'sortColumn=referencedate&'
                    f'sortDirection=desc'
                )
                if '?' in url:
                    url += f'&{extras}'
                else:
                    url += f'?{extras}'

                html = await self.fetch(url)
                if not html:
                    break

                soup = BeautifulSoup(html, 'lxml')
                job_rows = soup.select(
                    'tr.dataRow, .requisition-list-item, '
                    '.job-listing, [class*="requisition"]'
                )

                if not job_rows:
                    break

                page_added = 0
                for row in job_rows:
                    link_tag = row.select_one('a')
                    if not link_tag:
                        continue
                    title = clean_text(link_tag.get_text())
                    href = link_tag.get('href', '')
                    job_url = normalize_url(self.base_url, href)

                    if self.filter_internships and \
                            not matches_role_keywords(title):
                        continue

                    results.append(JobPosting(
                        title=title,
                        company=self.company_name,
                        url=job_url,
                    ))
                    page_added += 1

                if page_added == 0:
                    break

        except Exception as e:
            logger.error(
                f"[{self.company_name}] Taleo error: {e}"
            )

        return results
