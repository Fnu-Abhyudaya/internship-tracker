"""Configuration for all company career page scrapers."""

from typing import List
from .base_scraper import BaseScraper
from .workday_scraper import WorkdayScraper
from .greenhouse_scraper import GreenhouseScraper
from .oracle_scraper import OracleHCMScraper
from .icims_scraper import ICIMSScraper
from .taleo_scraper import TaleoScraper
from .generic_scraper import GenericHTMLScraper, AshbyScraper
from .playwright_scraper import PlaywrightScraper


def get_all_scrapers() -> List[BaseScraper]:
    scrapers = []

    # ===== WORKDAY (API-based, reliable) =====
    workday_configs = [
        {'company': 'Stanley Black & Decker',
         'url': 'https://sbdinc.wd1.myworkdayjobs.com/Stanley_Black_Decker_Career_Site'},
        {'company': 'Bose',
         'url': 'https://boseallaboutme.wd503.myworkdayjobs.com/en-US/Bose_Careers'},
        {'company': 'Hargrove EPC',
         'url': 'https://hargroveepc.wd12.myworkdayjobs.com/Hargrove_Careers'},
        {'company': 'NVIDIA',
         'url': 'https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite'},
        {'company': 'Xylem',
         'url': 'https://xylem.wd5.myworkdayjobs.com/en-US/xylem-careers'},
        {'company': 'Nidec',
         'url': 'https://nidec.wd1.myworkdayjobs.com/en-US/Nidec'},
        {'company': 'ResMed',
         'url': 'https://resmed.wd3.myworkdayjobs.com/en-US/ResMed_External_Careers'},
        {'company': 'Taylor',
         'url': 'https://taylor.wd1.myworkdayjobs.com/en-US/External'},
        {'company': 'Terex',
         'url': 'https://terex.wd1.myworkdayjobs.com/terexcareers'},
        {'company': 'STV Inc',
         'url': 'https://stvinc.wd5.myworkdayjobs.com/en-US/stv'},
        {'company': 'Calista/Yulista',
         'url': 'https://calistacorp.wd1.myworkdayjobs.com/Yulista'},
    ]
    for cfg in workday_configs:
        scrapers.append(WorkdayScraper(
            company_name=cfg['company'], base_url=cfg['url']
        ))

    # ===== GREENHOUSE (API-based, reliable) =====
    greenhouse_configs = [
        {'company': 'SharkNinja', 'token': 'sharkninjaoperatingllc'},
        {'company': 'Axon', 'token': 'axon'},
        {'company': 'Neuralink', 'token': 'neuralink'},
        {'company': 'Scout Motors', 'token': 'scoutmotors'},
        {'company': 'DLR Group', 'token': 'dlrgroup'},
        {'company': 'Rugged Robotics', 'token': 'ruggedrobotics'},
        {'company': 'Fellow Products', 'token': 'fellowproducts'},
        {'company': 'Salient Motion', 'token': 'salientmotion'},
        {'company': 'Amperesand', 'token': 'amperesand'},
    ]
    for cfg in greenhouse_configs:
        scrapers.append(GreenhouseScraper(
            company_name=cfg['company'],
            base_url=f"https://job-boards.greenhouse.io/{cfg['token']}",
            board_token=cfg['token'],
        ))

    # ===== ORACLE HCM (API-based) =====
    oracle_configs = [
        {'company': 'Eaton',
         'url': 'https://efds.fa.em5.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs'},
        {'company': 'Nokia',
         'url': 'https://jobs.nokia.com/en/sites/CX_1/jobs'},
        {'company': 'Centrus Energy',
         'url': 'https://eese.fa.us8.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CentrusEnergyCareers/jobs'},
    ]
    for cfg in oracle_configs:
        scrapers.append(OracleHCMScraper(
            company_name=cfg['company'], base_url=cfg['url']
        ))

    # ===== iCIMS =====
    icims_configs = [
        {'company': 'SSOE Group', 'url': 'https://careers-ssoe.icims.com/jobs/search?ss=1'},
        {'company': 'Marvin', 'url': 'https://careers-marvin.icims.com/jobs/search'},
        {'company': 'EMCOR Group', 'url': 'https://careers-emcorgroup.icims.com/jobs/search?ss=1'},
    ]
    for cfg in icims_configs:
        scrapers.append(ICIMSScraper(
            company_name=cfg['company'], base_url=cfg['url']
        ))

    # ===== ASHBY =====
    ashby_configs = [
        {'company': 'Mariana Minerals', 'slug': 'marianaminerals'},
        {'company': 'Matic Robots', 'slug': 'Maticrobots'},
    ]
    for cfg in ashby_configs:
        scrapers.append(AshbyScraper(
            company_name=cfg['company'],
            base_url=f"https://jobs.ashbyhq.com/{cfg['slug']}",
            board_slug=cfg['slug'],
        ))

    # ===== TALEO =====
    scrapers.append(TaleoScraper(
        company_name='Dyno Nobel',
        base_url='https://phh.tbe.taleo.net/phh02/ats/careers/v2/searchResults?org=DYNONOBEL&cws=43',
    ))

    # ===== PLAYWRIGHT (for JS-rendered sites) =====
    # These sites NEED a browser to see the job listings
    playwright_configs = [
        {
            'company': 'Bendix (Knorr-Bremse)',
            'url': 'https://careers.knorr-bremse.com/Bendix/content/search/?locale=en_US&keyword=intern',
            'wait': '.jobTitle, .jobs-list, [class*="job"]',
        },
        {
            'company': 'Tesla',
            'url': 'https://www.tesla.com/careers/search/?region=5&site=US&query=intern',
            'wait': '[class*="result"]',
        },
        {
            'company': 'Apple',
            'url': 'https://jobs.apple.com/en-us/search?location=united-states-USA&team=internships-STDNT-INTRN',
            'wait': 'a[href*="/details/"]',
        },
        {
            'company': 'AMD',
            'url': 'https://careers.amd.com/careers-home/jobs?categories=Student%20%2F%20Intern%20%2F%20Temp&limit=100',
            'wait': '[class*="job"]',
        },
        {
            'company': 'ASML',
            'url': 'https://www.asml.com/en/careers/find-your-job?job_country=US&job_type=Internship',
            'wait': '[class*="job"]',
        },
        {
            'company': 'Altec',
            'url': 'https://jobs.altec.com/search/intern/jobs/within/50/miles?location_country=United+States',
            'wait': '[class*="job"]',
        },
        {
            'company': 'Cummins',
            'url': 'https://cummins.jobs/jobs/?location=united+states&q=intern',
            'wait': '[class*="job"]',
        },
        {
            'company': 'Veeco',
            'url': 'https://careers.veeco.com/',
        },
        {
            'company': 'HARMAN',
            'url': 'https://jobsearch.harman.com/en_US/careers/SearchJobs/intern?2039=%5B60006%5D&2039_format=2669',
            'wait': '[class*="job"]',
        },
        {
            'company': 'Hyundai',
            'url': 'https://careers-americas.hyundai.com/hatci/search/?q=intern',
            'wait': '[class*="job"]',
        },
        {
            'company': 'Tenneco',
            'url': 'https://jobs.tenneco.com/search/?q=intern&locationsearch=united+states',
            'wait': '[class*="job"]',
        },
        {
            'company': 'Siemens Energy',
            'url': 'https://jobs.siemens-energy.com/en_US/jobs/Jobs/',
        },
        {
            'company': 'Atlas Copco',
            'url': 'https://www.atlascopco.com/en-in/jobs/job-overview?country=United%20States&keyword=intern',
        },
        {
            'company': 'Danfoss',
            'url': 'https://jobs.danfoss.com/search/?q=intern&searchResultView=LIST',
            'wait': '[class*="job"]',
        },
        {
            'company': 'ASSA ABLOY',
            'url': 'https://assaabloy.jobs2web.com/search/?title=intern&optionsFacetsDD_country=US',
        },
        {
            'company': 'Applied Materials',
            'url': 'https://careers.appliedmaterials.com/careers?query=intern&location=United+States',
        },
        {
            'company': 'The Boring Company',
            'url': 'https://www.boringcompany.com/careers',
        },
        {
            'company': 'Volvo Group',
            'url': 'https://jobs.volvogroup.com/?locale=en-EN',
        },
        {
            'company': 'Dana Inc',
            'url': 'https://jobs.dana.com/search/?q=intern',
        },
        {
            'company': 'ams-OSRAM',
            'url': 'https://jobs.ams-osram.com/en?locations.country=United%20States',
        },
        {
            'company': 'ZF Group',
            'url': 'https://jobs.zf.com/search/?optionsFacetsDD_shifttype=Internship+%2F+Co-Op&optionsFacetsDD_country=US',
        },
        {
            'company': 'ChargePoint',
            'url': 'https://www.chargepoint.com/en-gb/about/opportunities',
        },
        {
            'company': 'AMETEK',
            'url': 'https://jobs.ametek.com/search?q=intern',
        },
        {
            'company': 'Agility Robotics',
            'url': 'https://www.agilityrobotics.com/careers',
        },
        {
            'company': 'Formlabs',
            'url': 'https://careers.formlabs.com/',
        },
        {
            'company': 'Skyryse',
            'url': 'https://www.skyryse.com/jobs',
        },
        {
            'company': 'Schaeffler',
            'url': 'https://jobs.schaeffler.com/?locale=en_US',
        },
        {
            'company': 'ATS Automation',
            'url': 'https://jobs.atsautomation.com/search/?q=intern&optionsFacetsDD_country=US',
        },
        {
            'company': 'BD',
            'url': 'https://jobs.bd.com/en/search-jobs/intern/United%20States',
        },
        {
            'company': 'Lunar Energy',
            'url': 'https://www.lunarenergy.com/careers',
        },
        {
            'company': 'Fortive',
            'url': 'https://fortive.eightfold.ai/careers?query=intern&location=United+States',
        },
        {
            'company': 'Brunswick',
            'url': 'https://www.brunswick.com/careers/search-jobs',
        },
        {
            'company': 'ITW',
            'url': 'https://careers.itw.com/us/en/search-results?category=Internships',
        },
        {
            'company': 'WSP',
            'url': 'https://www.wsp.com/en-us/careers/job-opportunities?country=US',
        },
        {
            'company': 'AECOM',
            'url': 'https://aecom.jobs/locations/usa/jobs/?q=intern',
        },
        {
            'company': 'Addium',
            'url': 'https://addium.bamboohr.com/careers',
        },
        {
            'company': 'Fresenius Medical Care',
            'url': 'https://jobs.freseniusmedicalcare.com/?location_name=United%20States',
        },
        {
            'company': 'Vantedge Medical',
            'url': 'https://recruiting.paylocity.com/recruiting/jobs/All/73eb21ac-b2c3-4172-930c-67b6252d5b8b/Vantedge-Medical-Group',
        },
        {
            'company': 'Halo Industries',
            'url': 'https://apply.workable.com/halo-industries/',
        },
        {
            'company': 'ProMach',
            'url': 'https://recruiting.ultipro.com/PRO1027PROMA/JobBoard/4f2e6cdb-74ae-4dd0-a40e-ad85f30f189c/?q=intern',
        },
        {
            'company': 'CIRTEC Medical',
            'url': 'https://cirteccareers.ttcportals.com/search/jobs?q=intern',
        },
        {
            'company': 'Amperesand.io',
            'url': 'https://amperesand.io/careers',
        },
        {
            'company': 'Legence',
            'url': 'https://jobs.dayforcehcm.com/legence/studentportal',
        },
        {
            'company': 'Clark Nexsen',
            'url': 'https://jobs.silkroad.com/JMT/ClarkNexsenCareers',
        },
        {
            'company': 'Manitou Group',
            'url': 'https://careers.manitou-group.com/offers/?type_contrat=3686',
        },
        {
            'company': 'Sloan Valve',
            'url': 'https://jobs.sloan.com/search/?q=intern',
        },
        {
            'company': 'ASM International',
            'url': 'https://www.asm.com/open-vacancies?Location=us--arizona--chandler',
        },
        {
            'company': 'Lonza',
            'url': 'https://lonza.talent-community.com/app/project?userLocation=US%253A0',
        },
        {
            'company': 'Rep Fitness',
            'url': 'https://repfitness.com/pages/rep-careers',
        },
    ]

    for cfg in playwright_configs:
        scrapers.append(PlaywrightScraper(
            company_name=cfg['company'],
            base_url=cfg['url'],
            wait_selector=cfg.get('wait'),
        ))

    return scrapers
