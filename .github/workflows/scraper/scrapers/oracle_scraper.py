import logging
from typing import List
from urllib.parse import urlparse

from .base_scraper import BaseScraper, JobPosting
from ..utils.helpers import is_within_last_24_hours, is_internship_role

logger = logging.getLogger(__name__)


class OracleHCMScraper(BaseScraper):
    def __init__(self, company_name: str, base_url: str,
                 filter_internships: bool = True,
                 keyword: str = None):
        super().__init__(company_name, base_url)
        self.filter_internships = filter_internships
        self.keyword = keyword

    async def scrape(self) -> List[JobPosting]:
        results = []
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

            finder = f'findReqs;siteNumber={site_name}'
            if self.keyword:
                finder += f',keyword={self.keyword}'

            params = {
                'onlyData': 'true',
                'finder': finder,
                'limit': 25,
                'offset': 0,
            }

            offset = 0
            for page in range(10):
                params['offset'] = offset
                data = await self.fetch_json(api_url, params=params)
                if not data:
                    break

                items = data.get('items', [])
                if not items:
                    break

                for item in items:
                    title = (
                        item.get('Title', '') or
                        item.get('title', '')
                    )
                    req_id = (
                        item.get('Id', '') or
                        item.get('id', '')
                    )
                    posted_date = (
                        item.get('PostedDate', '') or
                        item.get('postedDate', '')
                    )
                    location = (
                        item.get('PrimaryLocation', '') or
                        item.get('primaryLocation', '')
                    )

                    if self.filter_internships and \
                            not is_internship_role(title):
                        continue

                    if not is_within_last_24_hours(posted_date):
                        continue

                    job_url = (
                        f"{base_host}/hcmUI/CandidateExperience/"
                        f"en/sites/{site_name}/job/{req_id}"
                    )

                    results.append(JobPosting(
                        title=title,
                        company=self.company_name,
                        url=job_url,
                        date_posted=posted_date,
                        location=location,
                    ))

                if len(items) < 25:
                    break
                offset += 25

        except Exception as e:
            logger.error(
                f"[{self.company_name}] Oracle HCM error: {e}"
            )

        return results
