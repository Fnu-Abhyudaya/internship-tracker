"""Scraper for iCIMS career pages."""

import logging
from typing import List

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, JobPosting
from ..utils.helpers import (
    normalize_url, clean_text
)
from ..utils.keywords import matches_role_keywords, is_us_location

logger = logging.getLogger(__name__)

MAX_PAGES = 10


class ICIMSScraper(BaseScraper):
    def __init__(self, company_name, base_url,
                 filter_internships=True):
        super().__init__(company_name, base_url)
        self.filter_internships = filter_internships

    async def scrape(self) -> List[JobPosting]:
        results = []
        try:
            # iCIMS sort: usually &searchSortField=postedDate&searchSortDirection=desc
            # Always start at page 1
            for page_num in range(1, MAX_PAGES + 1):
                url = self.base_url
                sort_params = (
                    f'searchSortField=postedDate&'
                    f'searchSortDirection=desc&pr={page_num}'
                )
                if '?' in url:
                    url += f'&{sort_params}'
                else:
                    url += f'?{sort_params}'

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
                            not matches_role_keywords(title):
                        continue

                    location = ''
                    if row.name != 'a':
                        loc_el = row.select_one(
                            '.iCIMS_JobLocation, '
                            '[class*="location"]'
                        )
                        if loc_el:
                            location = clean_text(loc_el.get_text())
                    if location and not is_us_location(location):
                        continue

                    results.append(JobPosting(
                        title=title,
                        company=self.company_name,
                        url=job_url,
                        location=location or 'N/A',
                    ))

                if not found_any:
                    break
        except Exception as e:
            logger.error(
                f"[{self.company_name}] iCIMS error: {e}"
            )

        return results
