"""Generic scraper for various career page formats."""

import re
import json
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


class GenericHTMLScraper(BaseScraper):
    def __init__(self, company_name, base_url,
                 filter_internships=True,
                 job_link_pattern=None,
                 custom_selectors=None):
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
            results = self._scrape_job_listings(soup)
            if not results:
                results = self._extract_from_script_data(soup)
            if not results:
                results = self._scrape_links(soup)
        except Exception as e:
            logger.error(
                f"[{self.company_name}] Generic error: {e}"
            )

        # Sort newest first
        results.sort(
            key=lambda p: p.date_posted or '',
            reverse=True
        )
        return results

    def _apply_filters(self, title, location):
        if self.filter_internships and \
                not matches_role_keywords(title):
            return False
        if location and not is_us_location(location):
            return False
        return True

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

                location = ''
                loc_el = item.select_one(
                    '.location, [class*="location"]'
                )
                if loc_el:
                    location = clean_text(loc_el.get_text())

                date_str = ''
                date_el = item.select_one(
                    '[class*="date"], [class*="posted"], '
                    'time, [datetime]'
                )
                if date_el:
                    date_str = (
                        date_el.get('datetime') or
                        clean_text(date_el.get_text())
                    )

                if not self._apply_filters(title, location):
                    continue

                results.append(JobPosting(
                    title=title,
                    company=self.company_name,
                    url=job_url,
                    date_posted=date_str,
                    location=location or 'N/A',
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

        location = ''
        loc_data = data.get('jobLocation', {})
        if isinstance(loc_data, dict):
            addr = loc_data.get('address', {})
            if isinstance(addr, dict):
                city = addr.get('addressLocality', '')
                region = addr.get('addressRegion', '')
                country = addr.get('addressCountry', '')
                location = f"{city}, {region}, {country}"

        if not self._apply_filters(title, location):
            return None
        if date and not is_within_last_24_hours(date):
            return None

        return JobPosting(
            title=title, company=self.company_name,
            url=url, date_posted=date,
            location=location or 'N/A',
        )

    def _scrape_links(self, soup):
        results = []
        seen_urls = set()
        job_url_patterns = [
            r'/jobs?/', r'/career', r'/position',
            r'/opening', r'/requisition', r'/vacancy',
            r'job_id=', r'jobId=', r'req_id='
        ]
        pattern = self.job_link_pattern or '|'.join(job_url_patterns)

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
            if not self._apply_filters(title, ''):
                continue
            results.append(JobPosting(
                title=title,
                company=self.company_name,
                url=job_url,
                location='N/A',
            ))
        return results


class AshbyScraper(BaseScraper):
    def __init__(self, company_name, base_url,
                 board_slug=None, filter_internships=True):
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
                return results

            jobs = data.get('jobs', [])
            # Sort newest first
            jobs.sort(
                key=lambda j: j.get('publishedDate', '') or '',
                reverse=True
            )

            for job in jobs:
                title = job.get('title', '')
                job_id = job.get('id', '')
                published = job.get('publishedDate', '')
                location = job.get('location', '')

                if self.filter_internships and \
                        not matches_role_keywords(title):
                    continue
                if published and \
                        not is_within_last_24_hours(published):
                    continue
                if not is_us_location(location):
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
                    location=location or 'N/A',
                ))
        except Exception as e:
            logger.error(
                f"[{self.company_name}] Ashby error: {e}"
            )
        return results
