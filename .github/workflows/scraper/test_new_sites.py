"""TEMPORARY: test only the newly added sites, with filters relaxed."""
import asyncio
from .scrapers import (greenhouse_scraper, workday_scraper, oracle_scraper)
from .scrapers.company_configs import get_all_scrapers
from .scrapers.greenhouse_scraper import GreenhouseScraper
from .scrapers.playwright_scraper import shutdown_browser

for m in (greenhouse_scraper, workday_scraper, oracle_scraper):
    m.is_within_last_24_hours = lambda *_: True

NEW = {'Insulet', 'Figure', 'DMC Engineering', 'Vast', 'EPTA Refrigeration',
       'Titan America', 'Landis+Gyr', 'Modine', 'Lincoln Electric', 'Shinkei',
       'Jordan & Skala Engineers', 'JTEKT North America',
       'Pelican Energy Consultants', 'AprilAire', 'EwingCole', 'Hendrickson',
       'Audubon', 'Linewise', 'Bosch', 'Quantum Computing Inc', 'Panasonic',
       'Formlabs'}

async def one(s):
    s.filter_internships = False
    try:
        res = await asyncio.wait_for(s.run(), 240)
    except asyncio.TimeoutError:
        res = None
    return s, res

async def main():
    scrapers = [s for s in get_all_scrapers() if s.company_name in NEW]
    for tok in ('vastspace', 'vastspacellc', 'vastspacecompany'):
        scrapers.append(GreenhouseScraper(f'Vast?{tok}', f'https://job-boards.greenhouse.io/{tok}', board_token=tok))
    sem = asyncio.Semaphore(5)
    async def guarded(s):
        async with sem:
            return await one(s)
    out = await asyncio.gather(*(guarded(s) for s in scrapers))
    await shutdown_browser()
    print('\n######## RESULTS ########')
    for s, res in sorted(out, key=lambda x: x[0].company_name):
        n = 'TIMEOUT' if res is None else len(res)
        print(f'@@ {s.company_name} | {type(s).__name__} | jobs={n} | pages_ok={s.pages_ok} | errors={len(s.errors)}')
        for e in list(dict.fromkeys(s.errors))[:2]:
            print(f'     ERR {e}')
        for r in (res or [])[:3]:
            print(f'     JOB {r.title[:70]} | {r.location} | {r.url[:90]}')

asyncio.run(main())
