import re
import json
import logging
from typing import List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, JobPosting
from ..utils.helpers import (
    is_within_last_24_hours, is_internship_role,
    normalize_url, clean_text
)

logger = logging.getLogger(__name__)


class GenericHTMLScraper(BaseScraper):
    def __init__(self, company_name: str, base_url: str,
                 filter_internships: bool = True,
                 job_link_pattern: str = None,
                 custom_selectors: dict = None):
        super().__init__(company_name, base_url)
        self.filter_internships = filter_internships
        self.job_link_pattern = job_link_pattern
        self.custom_selectors = custom_selectors or {}

    async def scrape(self) -> List[JobPosting]:
        results = []
        try:
            html = await self.fetch(self.base_url)
            if not html:
                return results

            soup = BeautifulSoup(html, 'lxml')

            if self.custom_selectors:
                results = self._scrape_with_selectors(soup)
                if results:
                    return results

            results = self._scrape_job_listings(soup)
            if results:
                return results

            results = self._extract_from_script_data(soup)
            if results:
                return results

            results = self._scrape_links(soup)

        except Exception as e:
            logger.error(
                f"[{self.company_name}] Generic scrape error: {e}"
            )

        return results

    def _scrape_with_selectors(self, soup):
        results = []
        container_sel = self.custom_selectors.get(
            'container', '.job-listing'
        )
        title_sel = self.custom_selectors.get(
            'title', 'a, .title, h3, h4'
        )
        link_sel = self.custom_selectors.get('link', 'a')
        date_sel = self.custom_selectors.get('date', '.date')
        location_sel = self.custom_selectors.get(
            'location', '.location'
        )

        for container in soup.select(container_sel):
            title_el = container.select_one(title_sel)
            link_el = container.select_one(link_sel)
            if not title_el:
                continue

            title = clean_text(title_el.get_text())
            href = ''
            if link_el:
                href = link_el.get('href', '')
            elif title_el.name == 'a':
                href = title_el.get('href', '')

            job_url = normalize_url(self.base_url, href)

            if self.filter_internships and \
                    not is_internship_role(title):
                continue

            date_text = ''
            date_el = container.select_one(date_sel)
            if date_el:
                date_text = clean_text(date_el.get_text())

            location = ''
            loc_el = container.select_one(location_sel)
            if loc_el:
                location = clean_text(loc_el.get_text())

            results.append(JobPosting(
                title=title,
                company=self.company_name,
                url=job_url,
                date_posted=date_text,
                location=location,
            ))

        return results

    def _scrape_job_listings(self, soup):
        results = []
        common_selectors = [
            '.job-listing', '.job-card', '.job-item',
            '.position-card', '.opening', '.career-item',
            '.vacancy', 'article[class*="job"]',
            'div[class*="job-row"]', 'li[class*="job"]',
            'tr[class*="job"]', '.search-results-item',
            '.result-item',
        ]

        for selector in common_selectors:
            items = soup.select(selector)
            if not items:
                continue

            for item in items:
                link = item.select_one('a')
                if not link:
                    continue

                title = clean_text(link.get_text())
                if not title or len(title) < 5:
                    for t_sel in [
                        'h2', 'h3', 'h4', '.title',
                        '.job-title', '.position-title'
                    ]:
                        t_el = item.select_one(t_sel)
                        if t_el:
                            title = clean_text(t_el.get_text())
                            break

                if not title:
                    continue

                href = link.get('href', '')
                job_url = normalize_url(self.base_url, href)

                if self.filter_internships and \
                        not is_internship_role(title):
                    continue

                results.append(JobPosting(
                    title=title,
                    company=self.company_name,
                    url=job_url,
                ))

            if results:
                break

        return results

    def _extract_from_script_data(self, soup):
        results = []
        for script in soup.select(
            'script[type="application/ld+json"]'
        ):
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    for item in data:
                        if item.get('@type') == 'JobPosting':
                            r = self._parse_jsonld_job(item)
                            if r:
                                results.append(r)
                elif isinstance(data, dict):
                    if data.get('@type') == 'JobPosting':
                        r = self._parse_jsonld_job(data)
                        if r:
                            results.append(r)
            except (json.JSONDecodeError, TypeError):
                continue
        return results

    def _parse_jsonld_job(self, data):
        title = data.get('title', '')
        date = data.get('datePosted', '')
        url = data.get('url', self.base_url)

        if self.filter_internships and not is_internship_role(title):
            return None
        if date and not is_within_last_24_hours(date):
            return None

        location = ''
        loc_data = data.get('jobLocation', {})
        if isinstance(loc_data, dict):
            addr = loc_data.get('address', {})
            if isinstance(addr, dict):
                location = addr.get('addressLocality', '')

        return JobPosting(
            title=title,
            company=self.company_name,
            url=url,
            date_posted=date,
            location=location,
        )

    def _scrape_links(self, soup):
        results = []
        seen_urls = set()
        job_url_patterns = [
            r'/jobs?/', r'/career', r'/position',
            r'/opening', r'/requisition', r'/vacancy',
            r'job_id=', r'jobId=', r'req_id='
        ]
        pattern = self.job_link_pattern or \
            '|'.join(job_url_patterns)

        for link in soup.select('a[href]'):
            href = link.get('href', '')
            if not re.search(pattern, href, re.IGNORECASE):
                continue
            title = clean_text(link.get_text())
            if not title or len(title) < 5:
                continue
            job_url = normalize_url(self.base_url, href)
            if job_url in seen_urls:
                continue
            seen_urls.add(job_url)
            if self.filter_internships and \
                    not is_internship_role(title):
                continue
            results.append(JobPosting(
                title=title,
                company=self.company_name,
                url=job_url,
            ))

        return results


class AshbyScraper(BaseScraper):
    def __init__(self, company_name: str, base_url: str,
                 board_slug: str = None,
                 filter_internships: bool = True):
        super().__init__(company_name, base_url)
        self.filter_internships = filter_internships
        if board_slug:
            self.board_slug = board_slug
        else:
            parsed = urlparse(base_url)
            parts = [p for p in parsed.path.split('/') if p]
            self.board_slug = parts[0] if parts else ''

    async def scrape(self) -> List[JobPosting]:
        results = []
        try:
            api_url = (
                f"https://api.ashbyhq.com/posting-api/"
                f"job-board/{self.board_slug}"
            )
            data = await self.fetch_json(api_url)

            if not data or 'jobs' not in data:
                return await self._scrape_html()

            for job in data.get('jobs', []):
                title = job.get('title', '')
                job_id = job.get('id', '')
                published = job.get('publishedDate', '')
                location = job.get('location', '')
                employment_type = job.get('employmentType', '')

                if self.filter_internships:
                    is_intern = (
                        is_internship_role(title) or
                        (employment_type and
                         'intern' in employment_type.lower())
                    )
                    if not is_intern:
                        continue

                if published and \
                        not is_within_last_24_hours(published):
                    continue

                job_url = (
                    f"https://jobs.ashbyhq.com/"
                    f"{self.board_slug}/{job_id}"
                )
                results.append(JobPosting(
                    title=title,
                    company=self.company_name,
                    url=job_url,
                    date_posted=published,
                    location=location,
                ))

        except Exception as e:
            logger.error(
                f"[{self.company_name}] Ashby error: {e}"
            )

        return results

    async def _scrape_html(self):
        results = []
        html = await self.fetch(self.base_url)
        if not html:
            return results
        soup = BeautifulSoup(html, 'lxml')
        for link in soup.select('a[href*="/jobs/"]'):
            title = clean_text(link.get_text())
            href = link.get('href', '')
            if title and (not self.filter_internships or
                         is_internship_role(title)):
                results.append(JobPosting(
                    title=title,
                    company=self.company_name,
                    url=normalize_url(self.base_url, href),
                ))
        return results
