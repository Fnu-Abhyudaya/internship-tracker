"""TEMPORARY diagnostics round 2: ADP data feeds + EPTA Oracle."""
import asyncio, json, re, aiohttp
from .scrapers.playwright_scraper import get_browser, shutdown_browser
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
PAGES = {
 'Hendrickson': 'https://myjobs.adp.com/hendrickson/cx/job-listing',
 'Pelican': 'https://www.pelicanenergy.com/careers-employment',
}

async def main():
    b = await get_browser()
    for name, url in PAGES.items():
        ctx = await b.new_context(user_agent=UA)
        pg = await ctx.new_page()
        caught = []
        async def on_resp(r):
            ct = r.headers.get('content-type', '')
            if 'json' in ct and r.request.resource_type in ('xhr', 'fetch'):
                try:
                    body = await r.text()
                except Exception:
                    body = ''
                caught.append((r.request.method, r.url, r.status, body))
        pg.on('response', on_resp)
        await pg.goto(url, wait_until='domcontentloaded', timeout=45000)
        await pg.wait_for_timeout(10000)
        print(f'\n==== {name}')
        for m, u, st, body in caught:
            print(f'XHR {m} {st} {u[:200]} len={len(body)}')
            if re.search(r'requisition|jobTitle|job', body, re.I) and len(body) > 500:
                print('   BODY', body[:1500].replace('\n', ' '))
        html = await pg.content()
        for mt in sorted(set(re.findall(r'https?://[^"\'\s<>]*adp[^"\'\s<>]*', html)))[:15]:
            print('ADPURL', mt[:200])
        for f in pg.frames:
            print('FRAME', f.url[:200])
        await ctx.close()
    await shutdown_browser()
    api = ('https://fa-eukp-saasfaprod1.fa.ocs.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions'
           '?onlyData=true&expand=requisitionList&finder=findReqs;siteNumber=CX_1,keyword=engineer,sortBy=POSTING_DATES_DESC&limit=5')
    async with aiohttp.ClientSession(headers={'User-Agent': UA}) as s:
        async with s.get(api) as r:
            t = await r.text()
            print('\n==== EPTA', r.status, t[:2500].replace('\n', ' '))

asyncio.run(main())
