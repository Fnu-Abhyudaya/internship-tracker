"""TEMPORARY: test new + fixed sites with filters relaxed."""
import asyncio, json
from .scrapers import greenhouse_scraper, workday_scraper, oracle_scraper, adp_scraper
from .scrapers.company_configs import get_all_scrapers
from .scrapers.playwright_scraper import shutdown_browser

for m in (greenhouse_scraper, workday_scraper, oracle_scraper):
    m.is_within_last_24_hours = lambda *_: True
_orig = adp_scraper.ADPScraper._to_posting
_shown = set()
def _peek(self, job, feed):
    if self.company_name not in _shown:
        _shown.add(self.company_name)
        print(f'KEYS {self.company_name}: {sorted(job.keys())}')
        print(f'SAMPLE {self.company_name}: {json.dumps(job)[:700]}')
    return _orig(self, job, feed)
adp_scraper.ADPScraper._to_posting = _peek

NEW = {'Shinkei', 'Bosch'}

async def main():
    from .scrapers.playwright_scraper import PlaywrightScraper
    scrapers = [s for s in get_all_scrapers() if s.company_name in NEW]
    scrapers.append(PlaywrightScraper('Bosch-pages5', 'https://jobs.bosch.com/en/?country=us&pages=5'))
    sem = asyncio.Semaphore(5)
    async def one(s):
        async with sem:
            s.filter_internships = False
            try:
                return s, await asyncio.wait_for(s.run(), 240)
            except asyncio.TimeoutError:
                return s, None
    out = await asyncio.gather(*(one(s) for s in scrapers))
    await shutdown_browser()
    print('\n######## RESULTS ########')
    for s, res in sorted(out, key=lambda x: x[0].company_name):
        n = 'TIMEOUT' if res is None else len(res)
        print(f'@@ {s.company_name} | {type(s).__name__} | jobs={n} | pages_ok={s.pages_ok} | errors={len(s.errors)}')
        for e in list(dict.fromkeys(s.errors))[:2]:
            print(f'     ERR {e}')
        for r in (res or [])[:200 if s.company_name == 'Shinkei' else 3]:
            print(f'     JOB {r.title[:60]} | {r.location} | {r.date_posted} | {r.url[:100]}')

asyncio.run(main())
