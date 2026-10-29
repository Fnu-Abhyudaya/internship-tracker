"""TEMPORARY diagnostics for sites that returned 0 jobs."""
import asyncio, re, aiohttp
from bs4 import BeautifulSoup
from .scrapers.playwright_scraper import get_browser, shutdown_browser

PAGES = {
 'Shinkei': 'https://careers.kula.ai/shinkei',
 'Pelican': 'https://www.pelicanenergy.com/careers-employment',
 'EwingCole': 'https://recruiting.paylocity.com/recruiting/jobs/All/51ea68bb-1bab-467d-89a7-f55fce6e8647/EwingCole-Inc',
 'Hendrickson': 'https://myjobs.adp.com/hendrickson/cx/job-listing',
 'Audubon': 'https://myjobs.adp.com/auduboncorporatecareers/cx/job-listing',
 'Modine': 'https://careers.modine.com/search/?q=engineer&sortColumn=referencedate&sortDirection=desc',
 'Titan-PW': 'https://careers-usa-titanmaterials.icims.com/jobs/search?ss=1&in_iframe=1',
 'DMC-site': 'https://www.dmcinfo.com/careers/open-positions/',
}
API = [
 'https://boards-api.greenhouse.io/v1/boards/dmcengineering/jobs',
 'https://boards-api.greenhouse.io/v1/boards/dmcinc/jobs',
 'https://boards-api.greenhouse.io/v1/boards/dmc/jobs',
 'https://boards-api.greenhouse.io/v1/boards/dmcinfo/jobs',
 'https://careers-usa-titanmaterials.icims.com/jobs/search?ss=1&in_iframe=1',
 'https://careers-usa-titanmaterials.icims.com/jobs/search?ss=1&searchKeyword=mechanical&in_iframe=1',
]
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

async def main():
    async with aiohttp.ClientSession(headers={'User-Agent': UA}) as s:
        for u in API:
            try:
                async with s.get(u) as r:
                    t = await r.text()
                    print(f'API {r.status} {u} len={len(t)} jobs_mentions={t.count("/jobs/")}')
            except Exception as e:
                print('API ERR', u, e)
    b = await get_browser()
    for name, url in PAGES.items():
        ctx = await b.new_context(user_agent=UA, viewport={'width': 1920, 'height': 1080})
        pg = await ctx.new_page()
        try:
            resp = await pg.goto(url, wait_until='domcontentloaded', timeout=45000)
            await pg.wait_for_timeout(9000)
            print(f'\n==== {name} status={resp.status if resp else None} final={pg.url}')
            frames = [f.url for f in pg.frames if f.url and f.url != pg.url]
            print('FRAMES', frames[:5])
            htmls = [await pg.content()]
            for f in pg.frames[1:4]:
                try: htmls.append(await f.content())
                except Exception: pass
            hrefs = []
            for h in htmls:
                for a in BeautifulSoup(h, 'lxml').select('a[href]'):
                    hrefs.append((a['href'], ' '.join(a.get_text().split())[:50]))
            seen = list(dict.fromkeys(hrefs))
            print('ANCHORS', len(seen))
            for href, txt in seen[:400]:
                if re.search(r'job|career|position|opening|req|detail|\d{4,}', href, re.I):
                    print('  A', href[:140], '|', txt)
            body = BeautifulSoup(htmls[0], 'lxml').get_text(' ', strip=True)
            print('TEXT', body[:600])
            clickables = await pg.eval_on_selector_all('[role=button],[role=link],button,[onclick],[data-job-id],[data-id]', 'els => els.slice(0,40).map(e => (e.tagName+" "+(e.getAttribute("data-job-id")||e.getAttribute("data-id")||"")+" "+(e.innerText||"").replace(/\\s+/g," ").slice(0,60)))')
            print('CLICKABLE', clickables[:25])
        except Exception as e:
            print('PW ERR', name, e)
        await ctx.close()
    await shutdown_browser()

asyncio.run(main())
