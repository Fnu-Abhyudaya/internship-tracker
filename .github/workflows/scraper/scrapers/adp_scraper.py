"""Scraper for ADP-hosted career sites.

Handles both ADP flavours:
  * ADP "myjobs" career sites  (myjobs.adp.com/<company>/cx/...)
  * ADP Workforce Now career centers / widgets embedded on a company's
    own website (workforcenow.adp.com/.../careercenter/...)

These pages show jobs without normal links, so instead of reading the
page we let a real browser load it, spot the job-list data request the
page makes, and replay that request asking for many more results.
"""

import logging
import re
from typing import List, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from .base_scraper import BaseScraper, JobPosting
from .playwright_scraper import get_browser
from ..utils.keywords import matches_role_keywords, is_us_location

logger = logging.getLogger(__name__)

PAGE_SIZE = 100
MAX_JOBS = 500
MYJOBS_FEED = re.compile(r'/job-requisitions/apply-custom-filters\?')
WFN_FEED = re.compile(r'/careercenter/public/events/staffing/v1/job-requisitions\?')
SKIP_HEADERS = {'host', 'content-length', 'cookie', 'accept-encoding'}


def _set_query(url: str, **updates) -> str:
    parts = urlparse(url)
    query = parse_qs(parts.query, keep_blank_values=True)
    for key, value in updates.items():
        query[key] = [str(value)]
    return urlunparse(parts._replace(query=urlencode(query, doseq=True)))


def _first(*values):
    for v in values:
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ''


class ADPScraper(BaseScraper):
    def __init__(self, company_name, base_url, filter_internships=True):
        super().__init__(company_name, base_url)
        self.filter_internships = filter_internships

    async def scrape(self) -> List[JobPosting]:
        results = []
        context = None
        try:
            browser = await get_browser()
            context = await browser.new_context(
                user_agent=self.headers['User-Agent'],
                viewport={'width': 1920, 'height': 1080},
            )
            page = await context.new_page()
            feed = {}

            def on_request(req):
                if feed:
                    return
                if MYJOBS_FEED.search(req.url):
                    feed.update(kind='myjobs', url=req.url,
                                headers=dict(req.headers))
                elif WFN_FEED.search(req.url):
                    feed.update(kind='wfn', url=req.url,
                                headers=dict(req.headers))

            page.on('request', on_request)
            response = await page.goto(
                self.base_url, wait_until='domcontentloaded', timeout=45000
            )
            if response is not None and response.status >= 400:
                self.record_error(
                    f"HTTP {response.status} when loading {self.base_url}"
                )
                return results

            for i in range(45):          # wait up to ~45 s for the feed
                if feed:
                    break
                if i % 5 == 0:           # scroll to wake lazy-loaded widgets
                    try:
                        await page.mouse.wheel(0, 4000)
                    except Exception:
                        pass
                await page.wait_for_timeout(1000)
            if not feed:
                self.record_error(
                    "Page loaded but its ADP job list never appeared "
                    "(site layout may have changed)"
                )
                return results

            headers = {k: v for k, v in feed['headers'].items()
                       if k.lower() not in SKIP_HEADERS
                       and not k.startswith(':')}
            raw_jobs = []
            for skip in range(0, MAX_JOBS, PAGE_SIZE):
                url = _set_query(feed['url'], **{'$top': PAGE_SIZE,
                                                 '$skip': skip})
                resp = await context.request.get(url, headers=headers)
                if resp.status != 200:
                    self.record_error(
                        f"HTTP {resp.status} from ADP job feed"
                    )
                    break
                data = await resp.json()
                self.record_success()
                batch = data.get('jobRequisitions') or []
                raw_jobs.extend(batch)
                total = data.get('count') or data.get('meta', {}).get(
                    'totalNumber')
                if len(batch) < PAGE_SIZE or (
                        total and len(raw_jobs) >= int(total)):
                    break

            for job in raw_jobs:
                posting = self._to_posting(job, feed)
                if not posting:
                    continue
                if self.filter_internships and \
                        not matches_role_keywords(posting.title):
                    continue
                if posting.location != 'N/A' and \
                        not is_us_location(posting.location):
                    continue
                results.append(posting)
        except Exception as e:
            logger.error(f"[{self.company_name}] ADP error: {e}")
            self.record_error(
                f"ADP scraper error: {self.describe_exception(e)}"
            )
        finally:
            if context:
                try:
                    await context.close()
                except Exception:
                    pass

        results.sort(key=lambda p: p.date_posted or '', reverse=True)
        return results

    def _to_posting(self, job: dict, feed: dict) -> Optional[JobPosting]:
        title = _first(job.get('publishedJobTitle'), job.get('jobTitle'),
                       job.get('requisitionTitle'), job.get('title'))
        if not title:
            return None

        location = 'N/A'
        locs = (job.get('requisitionLocations') or
                job.get('workLocations') or [])
        if locs:
            addr = (locs[0] or {}).get('address') or {}
            city = addr.get('cityName') or ''
            state = (addr.get('countrySubdivisionLevel1') or {}).get(
                'codeValue') or ''
            country = (addr.get('country') or {}).get('codeValue') or ''
            location = ', '.join(x for x in (city, state, country) if x) \
                or 'N/A'

        date_posted = _first(job.get('postDate'), job.get('postingDate'),
                             job.get('publishedDate'))
        if not date_posted:
            for field in (job.get('customFieldGroup') or {}).get(
                    'dateFields', []) or []:
                code = (field.get('nameCode') or {}).get('codeValue')
                if code == 'PostingDate':
                    date_posted = field.get('dateValue') or ''
                    break
        date_posted = date_posted[:10] if date_posted else None

        if feed['kind'] == 'myjobs':
            req_id = job.get('reqId') or job.get('itemID') or ''
            domain = urlparse(self.base_url).path.strip('/').split('/')[0]
            url = (f"https://myjobs.adp.com/{domain}/cx/job-details"
                   f"?reqId={req_id}")
        else:
            q = parse_qs(urlparse(feed['url']).query)
            cid = (q.get('cid') or [''])[0]
            cc_id = (q.get('ccId') or [''])[0]
            url = ("https://workforcenow.adp.com/mascsr/default/mdf/"
                   "recruitment/recruitment.html"
                   f"?cid={cid}&ccId={cc_id}"
                   f"&jobId={job.get('itemID', '')}&lang=en_US")

        return JobPosting(title=title, company=self.company_name, url=url,
                          date_posted=date_posted, location=location)
