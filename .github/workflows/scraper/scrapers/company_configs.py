from typing import List
from .base_scraper import BaseScraper
from .workday_scraper import WorkdayScraper
from .greenhouse_scraper import GreenhouseScraper
from .oracle_scraper import OracleHCMScraper
from .icims_scraper import ICIMSScraper
from .taleo_scraper import TaleoScraper
from .generic_scraper import GenericHTMLScraper, AshbyScraper


def get_all_scrapers() -> List[BaseScraper]:
    scrapers = []

    # ===== WORKDAY =====
    workday_configs = [
        {
            'company': 'Stanley Black & Decker',
            'url': 'https://sbdinc.wd1.myworkdayjobs.com/Stanley_Black_Decker_Career_Site',
        },
        {
            'company': 'Bose',
            'url': 'https://boseallaboutme.wd503.myworkdayjobs.com/en-US/Bose_Careers',
            'params': {'workerSubType': '1f9406d5717e109875eae116f2c007e5'},
        },
        {
            'company': 'Hargrove EPC',
            'url': 'https://hargroveepc.wd12.myworkdayjobs.com/Hargrove_Careers',
        },
        {
            'company': 'NVIDIA',
            'url': 'https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite',
            'params': {'q': 'intern'},
        },
        {
            'company': 'Xylem',
            'url': 'https://xylem.wd5.myworkdayjobs.com/en-US/xylem-careers',
            'params': {'q': 'intern'},
        },
        {
            'company': 'Nidec',
            'url': 'https://nidec.wd1.myworkdayjobs.com/en-US/Nidec',
        },
        {
            'company': 'ResMed',
            'url': 'https://resmed.wd3.myworkdayjobs.com/en-US/ResMed_External_Careers',
            'params': {'q': 'intern'},
        },
        {
            'company': 'Taylor',
            'url': 'https://taylor.wd1.myworkdayjobs.com/en-US/External',
        },
        {
            'company': 'Terex',
            'url': 'https://terex.wd1.myworkdayjobs.com/terexcareers',
        },
        {
            'company': 'STV Inc',
            'url': 'https://stvinc.wd5.myworkdayjobs.com/en-US/stv',
        },
        {
            'company': 'Calista/Yulista',
            'url': 'https://calistacorp.wd1.myworkdayjobs.com/Yulista',
            'params': {'q': 'intern'},
        },
    ]

    for cfg in workday_configs:
        scrapers.append(WorkdayScraper(
            company_name=cfg['company'],
            base_url=cfg['url'],
            search_params=cfg.get('params', {}),
        ))

    # ===== GREENHOUSE =====
    greenhouse_configs = [
        {'company': 'SharkNinja', 'token': 'sharkninjaoperatingllc', 'offices': ['4005623006']},
        {'company': 'Axon', 'token': 'axon'},
        {'company': 'Neuralink', 'token': 'neuralink'},
        {'company': 'Scout Motors', 'token': 'scoutmotors'},
        {'company': 'DLR Group', 'token': 'dlrgroup'},
        {'company': 'Rugged Robotics', 'token': 'ruggedrobotics'},
        {'company': 'Fellow Products', 'token': 'fellowproducts'},
        {'company': 'Salient Motion', 'token': 'salientmotion'},
        {'company': 'Amperesand', 'token': 'amperesand', 'offices': ['4017340009']},
    ]

    for cfg in greenhouse_configs:
        scrapers.append(GreenhouseScraper(
            company_name=cfg['company'],
            base_url=f"https://job-boards.greenhouse.io/{cfg['token']}",
            board_token=cfg['token'],
            office_ids=cfg.get('offices', []),
        ))

    # ===== ORACLE HCM =====
    oracle_configs = [
        {
            'company': 'Eaton',
            'url': 'https://efds.fa.em5.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs',
            'keyword': 'student',
        },
        {
            'company': 'Nokia',
            'url': 'https://jobs.nokia.com/en/sites/CX_1/jobs',
        },
        {
            'company': 'Centrus Energy',
            'url': 'https://eese.fa.us8.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CentrusEnergyCareers/jobs',
        },
    ]

    for cfg in oracle_configs:
        scrapers.append(OracleHCMScraper(
            company_name=cfg['company'],
            base_url=cfg['url'],
            keyword=cfg.get('keyword'),
        ))

    # ===== iCIMS =====
    icims_configs = [
        {'company': 'SSOE Group', 'url': 'https://careers-ssoe.icims.com/jobs/search?ss=1'},
        {'company': 'Marvin', 'url': 'https://careers-marvin.icims.com/jobs/search'},
        {'company': 'EMCOR Group', 'url': 'https://careers-emcorgroup.icims.com/jobs/search?ss=1'},
    ]

    for cfg in icims_configs:
        scrapers.append(ICIMSScraper(
            company_name=cfg['company'],
            base_url=cfg['url'],
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

    # ===== GENERIC HTML =====
    generic_configs = [
        {'company': 'Tesla', 'url': 'https://www.tesla.com/careers/search/?region=5&site=US&query=summer', 'pattern': r'/careers/search/job/'},
        {'company': 'Apple', 'url': 'https://jobs.apple.com/en-us/search?location=united-states-USA&team=internships-STDNT-INTRN', 'filter': False},
        {'company': 'AMD', 'url': 'https://careers.amd.com/careers-home/jobs?page=1&categories=Student%20%2F%20Intern%20%2F%20Temp&limit=100', 'filter': False},
        {'company': 'ASML', 'url': 'https://www.asml.com/en/careers/find-your-job?job_country=US&job_type=Internship', 'filter': False},
        {'company': 'Knorr-Bremse/Bendix', 'url': 'https://careers.knorr-bremse.com/Bendix/content/search/?locale=en_US&keyword=united+states'},
        {'company': 'Altec', 'url': 'https://jobs.altec.com/search/intern/jobs/within/50/miles?location_country=United+States', 'filter': False},
        {'company': 'Cummins', 'url': 'https://cummins.jobs/jobs/?location=united+states'},
        {'company': 'Veeco', 'url': 'https://careers.veeco.com/'},
        {'company': 'HARMAN', 'url': 'https://jobsearch.harman.com/en_US/careers/SearchJobs/intern?2039=%5B60006%5D&2039_format=2669&listFilterMode=1', 'filter': False},
        {'company': 'Hyundai', 'url': 'https://careers-americas.hyundai.com/hatci/search/?q=intern', 'filter': False},
        {'company': 'Tenneco', 'url': 'https://jobs.tenneco.com/search/?q=&locationsearch=united+states'},
        {'company': 'Siemens Energy', 'url': 'https://jobs.siemens-energy.com/en_US/jobs/Jobs/'},
        {'company': 'Atlas Copco', 'url': 'https://www.atlascopco.com/en-in/jobs/job-overview?country=United%20States&keyword=intern', 'filter': False},
        {'company': 'Danfoss', 'url': 'https://jobs.danfoss.com/search/?searchResultView=LIST'},
        {'company': 'ASSA ABLOY', 'url': 'https://assaabloy.jobs2web.com/search/?title=intern&optionsFacetsDD_country=US', 'filter': False},
        {'company': 'Applied Materials', 'url': 'https://careers.appliedmaterials.com/careers?query=intern&location=United+States', 'filter': False},
        {'company': 'The Boring Company', 'url': 'https://www.boringcompany.com/careers#Jobs'},
        {'company': 'Volvo Group', 'url': 'https://jobs.volvogroup.com/?locale=en-EN'},
        {'company': 'Dana Inc', 'url': 'https://jobs.dana.com/search/?q=intern'},
        {'company': 'ams-OSRAM', 'url': 'https://jobs.ams-osram.com/en?locations.country=United%20States'},
        {'company': 'ZF Group', 'url': 'https://jobs.zf.com/search/?optionsFacetsDD_shifttype=Internship+%2F+Co-Op&optionsFacetsDD_country=US', 'filter': False},
        {'company': 'ChargePoint', 'url': 'https://www.chargepoint.com/en-gb/about/opportunities'},
        {'company': 'AMETEK', 'url': 'https://jobs.ametek.com/search?q=intern'},
        {'company': 'The Boring Company', 'url': 'https://www.boringcompany.com/careers'},
        {'company': 'Agility Robotics', 'url': 'https://www.agilityrobotics.com/careers'},
        {'company': 'Formlabs', 'url': 'https://careers.formlabs.com/'},
        {'company': 'Skyryse', 'url': 'https://www.skyryse.com/jobs'},
        {'company': 'Schaeffler', 'url': 'https://jobs.schaeffler.com/?locale=en_US'},
        {'company': 'ATS Automation', 'url': 'https://jobs.atsautomation.com/search/?q=intern&optionsFacetsDD_country=US', 'filter': False},
        {'company': 'BD', 'url': 'https://jobs.bd.com/en/search-jobs/United%20States/159/2/6252001/39x76/-98x5/100/2'},
        {'company': 'Lunar Energy', 'url': 'https://www.lunarenergy.com/careers'},
        {'company': 'Fortive', 'url': 'https://fortive.eightfold.ai/careers?query=intern&location=United+States'},
        {'company': 'Brunswick', 'url': 'https://www.brunswick.com/careers/search-jobs'},
        {'company': 'ITW', 'url': 'https://careers.itw.com/us/en/search-results?category=Internships'},
        {'company': 'WSP', 'url': 'https://www.wsp.com/en-us/careers/job-opportunities?country=US'},
        {'company': 'AECOM', 'url': 'https://aecom.jobs/locations/usa/jobs/?q=intern&sort=date', 'filter': False},
        {'company': 'Addium', 'url': 'https://addium.bamboohr.com/careers'},
        {'company': 'Fresenius Medical Care', 'url': 'https://jobs.freseniusmedicalcare.com/?location_name=United%20States'},
        {'company': 'Vantedge Medical', 'url': 'https://recruiting.paylocity.com/recruiting/jobs/All/73eb21ac-b2c3-4172-930c-67b6252d5b8b/Vantedge-Medical-Group'},
        {'company': 'Halo Industries', 'url': 'https://apply.workable.com/halo-industries/'},
        {'company': 'ProMach', 'url': 'https://recruiting.ultipro.com/PRO1027PROMA/JobBoard/4f2e6cdb-74ae-4dd0-a40e-ad85f30f189c/?q=co-op'},
        {'company': 'CIRTEC Medical', 'url': 'https://cirteccareers.ttcportals.com/search/jobs?q=intern'},
        {'company': 'Amperesand.io', 'url': 'https://amperesand.io/careers#open-roles'},
        {'company': 'Legence', 'url': 'https://jobs.dayforcehcm.com/legence/studentportal'},
        {'company': 'Clark Nexsen', 'url': 'https://jobs.silkroad.com/JMT/ClarkNexsenCareers'},
        {'company': 'Manitou Group', 'url': 'https://careers.manitou-group.com/offers/?type_contrat=3686', 'filter': False},
    ]

    for cfg in generic_configs:
        scrapers.append(GenericHTMLScraper(
            company_name=cfg['company'],
            base_url=cfg['url'],
            filter_internships=cfg.get('filter', True),
            job_link_pattern=cfg.get('pattern'),
        ))

    return scrapers
