"""Main entry point for the internship scraper."""

import os
import sys
import asyncio
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import List

import openpyxl
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side
)
from openpyxl.utils import get_column_letter

from .scrapers.base_scraper import JobPosting
from .scrapers.company_configs import get_all_scrapers
from .email_sender import send_email, send_no_results_email
from .utils.keywords import matches_role_keywords, is_us_location

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('scraper.log', mode='w'),
    ]
)
logger = logging.getLogger(__name__)

RECIPIENT_EMAIL = os.environ.get(
    'RECIPIENT_EMAIL', 'abhyudaya.manipal@gmail.com'
)
OUTPUT_DIR = Path('output')
MAX_CONCURRENT = 10


async def run_scraper_with_semaphore(scraper, semaphore):
    async with semaphore:
        try:
            return await asyncio.wait_for(
                scraper.run(), timeout=120
            )
        except asyncio.TimeoutError:
            logger.warning(f"[{scraper.company_name}] Timed out")
            return []
        except Exception as e:
            logger.error(f"[{scraper.company_name}] Error: {e}")
            return []


async def run_all_scrapers() -> List[JobPosting]:
    try:
        scrapers = get_all_scrapers()
    except Exception as e:
        logger.error(f"Failed to load scrapers: {e}")
        logger.error(traceback.format_exc())
        return []

    logger.info(f"Starting {len(scrapers)} scrapers...")
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    tasks = [
        run_scraper_with_semaphore(s, semaphore)
        for s in scrapers
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_postings = []
    for i, result in enumerate(results):
        if isinstance(result, list):
            all_postings.extend(result)
        elif isinstance(result, Exception):
            logger.error(
                f"Scraper {scrapers[i].company_name} "
                f"failed: {result}"
            )

    logger.info(f"Total raw postings: {len(all_postings)}")
    return all_postings


def final_filter(postings: List[JobPosting]) -> List[JobPosting]:
    """Final sanity-check filter for keywords and US location."""
    filtered = []
    for p in postings:
        if not matches_role_keywords(p.title):
            continue
        # Only filter location if we have one
        if p.location and p.location != 'N/A':
            if not is_us_location(p.location):
                continue
        filtered.append(p)
    logger.info(
        f"After keyword/location filter: {len(filtered)} postings"
    )
    return filtered


def deduplicate(postings: List[JobPosting]) -> List[JobPosting]:
    seen = set()
    unique = []
    for p in postings:
        key = (
            p.title.lower().strip(),
            p.company.lower().strip(),
            p.url.lower().strip(),
        )
        if key not in seen:
            seen.add(key)
            unique.append(p)
    logger.info(
        f"Deduplicated: {len(postings)} -> {len(unique)}"
    )
    return unique


def create_excel(postings: List[JobPosting]) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime('%Y-%m-%d')
    filepath = OUTPUT_DIR / f'internship_postings_{today}.xlsx'

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Internship Postings'

    header_font = Font(bold=True, size=12, color='FFFFFF')
    header_fill = PatternFill(
        start_color='2563EB', end_color='2563EB',
        fill_type='solid'
    )
    header_align = Alignment(
        horizontal='center', vertical='center'
    )
    thin = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin'),
    )

    headers = ['S.No', 'Role', 'Company', 'Link',
               'Date Posted', 'Location']
    widths = [8, 55, 25, 60, 18, 30]

    for col, (h, w) in enumerate(zip(headers, widths), 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin
        ws.column_dimensions[get_column_letter(col)].width = w

    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f'A1:F{max(len(postings) + 1, 2)}'

    alt_fill = PatternFill(
        start_color='EFF6FF', end_color='EFF6FF',
        fill_type='solid'
    )
    link_font = Font(
        color='2563EB', underline='single', size=11
    )
    data_align = Alignment(vertical='center', wrap_text=True)

    postings.sort(
        key=lambda p: (p.company.lower(), p.title.lower())
    )

    for row_num, posting in enumerate(postings, 2):
        row_data = [
            row_num - 1,
            posting.title,
            posting.company,
            posting.url,
            posting.date_posted or 'N/A',
            posting.location or 'N/A',
        ]
        for col, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_num, column=col, value=value)
            cell.alignment = data_align
            cell.border = thin
            if row_num % 2 == 0:
                cell.fill = alt_fill
            if col == 4 and value and value != 'N/A':
                cell.font = link_font
                cell.hyperlink = value

    ws2 = wb.create_sheet('Summary')
    ws2['A1'] = 'Internship Tracker Summary'
    ws2['A1'].font = Font(bold=True, size=14)
    ws2['A3'] = f'Date: {today}'
    ws2['A4'] = f'Total Postings: {len(postings)}'
    companies = set(p.company for p in postings)
    ws2['A5'] = f'Companies: {len(companies)}'
    ws2['A6'] = f'Generated: {datetime.now().isoformat()}'
    ws2['A8'] = 'By Company:'
    ws2['A8'].font = Font(bold=True)

    counts = {}
    for p in postings:
        counts[p.company] = counts.get(p.company, 0) + 1
    for i, (co, cnt) in enumerate(sorted(counts.items()), 10):
        ws2[f'A{i}'] = co
        ws2[f'B{i}'] = cnt

    ws2.column_dimensions['A'].width = 35
    ws2.column_dimensions['B'].width = 12

    wb.save(filepath)
    logger.info(f"Saved: {filepath}")
    return str(filepath)


def main():
    logger.info("=" * 50)
    logger.info("INTERNSHIP TRACKER STARTING")
    logger.info(f"Time: {datetime.now().isoformat()}")
    logger.info("=" * 50)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        all_postings = asyncio.run(run_all_scrapers())
    except Exception as e:
        logger.error(f"Scraping crashed: {e}")
        logger.error(traceback.format_exc())
        all_postings = []

    # Final filter against ROLE_KEYWORDS + US location
    filtered = final_filter(all_postings)
    unique = deduplicate(filtered)

    if not unique:
        logger.info("No new matching postings found.")
        try:
            filepath = create_excel([])
        except Exception as e:
            logger.error(f"Excel error: {e}")
        try:
            send_no_results_email(RECIPIENT_EMAIL)
        except Exception as e:
            logger.error(f"Email error: {e}")
        return

    try:
        filepath = create_excel(unique)
    except Exception as e:
        logger.error(f"Failed to create Excel: {e}")
        return

    companies = set(p.company for p in unique)
    try:
        send_email(
            filepath=filepath,
            recipient=RECIPIENT_EMAIL,
            total_jobs=len(unique),
            total_companies=len(companies),
        )
        logger.info("Report sent!")
    except Exception as e:
        logger.error(f"Email failed: {e}")
        logger.error(traceback.format_exc())

    logger.info("DONE")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"FATAL: {e}")
        logger.error(traceback.format_exc())
        sys.exit(0)
