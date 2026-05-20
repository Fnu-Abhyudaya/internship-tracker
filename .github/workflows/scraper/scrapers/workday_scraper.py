import logging
from typing import List
from urllib.parse import urlparse, parse_qs

from .base_scraper import BaseScraper, JobPosting
from ..utils.helpers import is_within_last_24_hours, is_internship_role

logger = logging.getLogger(__name__)


class WorkdayScraper(BaseScraper):
    def __init__(self, company_name: str, base_url: str,
                 search_params: dict = None,
                 filter_internships: bool = True):
        super().__init__(company_name, base_url)
        self.search_params = search_params or {}
        self.filter_internships = filter_internships

    async def scrape(self) -> List[JobPosting]:
        results = []
        try:
            parsed = urlparse(self.base_url)
            host = f"{parsed.scheme}://{parsed.hostname}"
            path_parts = [
                p for p in parsed.path.split('/')
                if p and p != 'en-US'
            ]
            site_path = path_parts[0] if path_parts else ''
            api_url = f"{host}/api/v1/{site_path}/jobs"

            params = {'limit': 20, 'offset': 0}

            if parsed.query:
                qs = parse_qs(parsed.query)
                for key, values in qs.items():
                    if key == 'q':
                        params['q'] = values[0]
                    elif key == 'workerSubType':
                        params['workerSubType'] = values
                    elif key == 'locationCountry':
                        params['locationCountry'] = values[0]
                    elif key == 'jobFamilyGroup':
                        params['jobFamilyGroup'] = values[0]

            params.update(self.search_params)

            offset = 0
            max_pages = 10

            for page in range(max_pages):
                params['offset'] = offset
                data = await self.fetch_json(api_url, params=params)

                if not data or 'jobPostings' not in data:
                    alt_api = f"{host}/{site_path}/jobs"
                    data = await self.fetch_json(
                        alt_api, params=params
                    )
                    if not data or 'jobPostings' not in data:
                        break

                postings = data.get('jobPostings', [])
                if not postings:
                    break

                for posting in postings:
                    title = posting.get('title', '')
                    posted_on = posting.get('postedOn', '')
                    external_path = posting.get('externalPath', '')

                    if self.filter_internships and \
                            not is_internship_role(title):
                        continue

                    if not is_within_last_24_hours(posted_on):
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
                        location=posting.get('locationsText', 'N/A'),
                    ))

                total = data.get('total', 0)
                offset += len(postings)
                if offset >= total:
                    break

        except Exception as e:
            logger.error(
                f"[{self.company_name}] Workday error: {e}"
            )

        return results
