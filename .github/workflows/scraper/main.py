"""Main entry point for the internship scraper."""

import os
import sys
import asyncio
import logging
import traceback
from collections import Counter
from dataclasses import dataclass
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
from .scrapers.playwright_scraper import shutdown_browser
from .email_sender import send_email, send_no_results_email
from .utils.keywords import matches_role_keywords, is_us_location
from .utils.seen_tracker import (
    load_history, filter_new_postings,
    add_to_history, save_history
)

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
MAX_CONCURRENT = 5
SCRAPER_TIMEOUT_SECONDS = 180
MAX_DETAILS_PER_SITE = 3


@dataclass
class ScanIssue:
    """A website that could not be scanned cleanly."""
    company: str
    website: str
    status: str      # 'Failed', 'Partial' or 'Timed out'
    details: str


def summarize_errors(errors: List[str]) -> str:
    """Collapse repeated error messages into a short readable string."""
    counts = Counter(errors)
    parts = []
    for msg, n in counts.most_common(MAX_DETAILS_PER_SITE):
        parts.append(f"{msg} (x{n})" if n > 1 else msg)
    extra = len(counts) - len(parts)
    if extra > 0:
        parts.append(f"...and {extra} other error type(s) - see scraper.log")
    return '\n'.join(parts)


def build_scan_issue(scraper, timed_out=False, crash=None):
    """Return a ScanIssue for this scraper, or None if it ran cleanly."""
    errors = list(getattr(scraper, 'errors', []) or [])
    pages_ok = getattr(scraper, 'pages_ok', 0)
    if crash is not None:
        errors.append(f"Unexpected crash: {crash}")

    if timed_out:
        details = (
            f"Did not finish within {SCRAPER_TIMEOUT_SECONDS} seconds; "
            f"jobs from this site may be missing."
        )
        if errors:
            details += '\n' + summarize_errors(errors)
        return ScanIssue(scraper.company_name, scraper.base_url,
                         'Timed out', details)
    if not errors:
        return None
    status = 'Partial' if pages_ok > 0 else 'Failed'
    return ScanIssue(scraper.company_name, scraper.base_url,
                     status, summarize_errors(errors))


async def run_scraper_with_semaphore(scraper, semaphore, stats,
                                    scan_issues):
    async with semaphore:
        try:
            results = await asyncio.wait_for(
                scraper.run(), timeout=SCRAPER_TIMEOUT_SECONDS
            )
            stats[scraper.company_name] = len(results)
            issue = build_scan_issue(scraper)
            if issue:
                scan_issues.append(issue)
            return results
        except asyncio.TimeoutError:
            logger.warning(f"[{scraper.company_name}] Timed out")
            stats[scraper.company_name] = 'TIMEOUT'
            scan_issues.append(build_scan_issue(scraper, timed_out=True))
            return []
        except Exception as e:
            logger.error(f"[{scraper.company_name}] Error: {e}")
            stats[scraper.company_name] = f'ERROR: {e}'
            scan_issues.append(build_scan_issue(scraper, crash=e))
            return []


async def run_all_scrapers():
    try:
        scrapers = get_all_scrapers()
    except Exception as e:
        logger.error(f"Failed to load scrapers: {e}")
        logger.error(traceback.format_exc())
        return [], {}, [ScanIssue(
            'ALL WEBSITES', 'N/A', 'Failed',
            f"The list of websites could not be loaded, so nothing "
            f"was scanned: {e}"
        )]

    logger.info(f"Starting {len(scrapers)} scrapers...")
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    stats = {}
    scan_issues = []
    tasks = [
        run_scraper_with_semaphore(s, semaphore, stats, scan_issues)
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
            scan_issues.append(
                build_scan_issue(scrapers[i], crash=result)
            )

    try:
        await shutdown_browser()
    except Exception as e:
        logger.warning(f"Browser shutdown error: {e}")

    logger.info(f"Total raw postings: {len(all_postings)}")
    logger.info(
        f"Websites with scan issues: {len(scan_issues)} "
        f"of {len(scrapers)}"
    )
    return all_postings, stats, scan_issues


def final_filter(postings):
    """Filter by role keywords and US location."""
    filtered = []
    rejected_kw = 0
    rejected_loc = 0
    for p in postings:
        if not matches_role_keywords(p.title):
            rejected_kw += 1
            continue
        if p.location and p.location != 'N/A':
            if not is_us_location(p.location):
                rejected_loc += 1
                continue
        filtered.append(p)
    logger.info(
        f"Filter results: kept {len(filtered)}, "
        f"rejected {rejected_kw} (keyword), "
        f"rejected {rejected_loc} (location)"
    )
    return filtered


def deduplicate_within_run(postings):
    """Remove duplicates within this single run (by URL)."""
    seen_urls = set()
    unique = []
    for p in postings:
        url_key = (p.url or '').lower().strip().rstrip('/')
        if url_key and url_key not in seen_urls:
            seen_urls.add(url_key)
            unique.append(p)
    logger.info(
        f"Within-run dedup: {len(postings)} -> {len(unique)}"
    )
    return unique


def log_company_stats(stats):
    """Print a per-company summary to the log."""
    logger.info("=" * 60)
    logger.info("PER-COMPANY RESULTS:")
    logger.info("=" * 60)
    for company in sorted(stats.keys()):
        count = stats[company]
        if isinstance(count, int):
            marker = "OK " if count > 0 else "-- "
            logger.info(f"  {marker} {company}: {count}")
        else:
            logger.info(f"  ERR {company}: {count}")
    logger.info("=" * 60)


def sort_newest_first(postings):
    """Sort by date_posted DESC; undated entries go to bottom."""
    with_date = [p for p in postings if p.date_posted]
    without_date = [p for p in postings if not p.date_posted]
    with_date.sort(
        key=lambda p: p.date_posted or '',
        reverse=True
    )
    without_date.sort(
        key=lambda p: (p.company.lower(), p.title.lower())
    )
    return with_date + without_date


def create_excel(postings, scan_issues=None):
    """Build and save the styled Excel report."""
    scan_issues = scan_issues or []
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime('%Y-%m-%d')
    filepath = OUTPUT_DIR / f'internship_postings_{today}.xlsx'

    postings = sort_newest_first(postings)

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

    add_scan_issues_sheet(wb, scan_issues, thin)

    # Summary sheet
    ws2 = wb.create_sheet('Summary')
    ws2['A1'] = 'Internship Tracker Summary'
    ws2['A1'].font = Font(bold=True, size=14)
    ws2['A3'] = f'Date: {today}'
    ws2['A4'] = f'New Postings Today: {len(postings)}'
    companies = set(p.company for p in postings)
    ws2['A5'] = f'Companies: {len(companies)}'
    ws2['A6'] = f'Generated: {datetime.now().isoformat()}'
    ws2['A7'] = 'Sorted by: Most recent first'
    ws2['A8'] = (
        f'Websites with scan issues: {len(scan_issues)} '
        f'(see "Scan Issues" sheet)'
    )
    if scan_issues:
        ws2['A8'].font = Font(bold=True, color='B91C1C')
    ws2['A10'] = 'By Company:'
    ws2['A10'].font = Font(bold=True)
    ws2['A11'] = 'Company'
    ws2['B11'] = 'Count'
    ws2['A11'].font = Font(bold=True)
    ws2['B11'].font = Font(bold=True)

    counts = {}
    for p in postings:
        counts[p.company] = counts.get(p.company, 0) + 1
    for i, (co, cnt) in enumerate(sorted(counts.items()), 12):
        ws2[f'A{i}'] = co
        ws2[f'B{i}'] = cnt

    ws2.column_dimensions['A'].width = 35
    ws2.column_dimensions['B'].width = 12

    wb.save(filepath)
    logger.info(f"Saved: {filepath}")
    return str(filepath)


def add_scan_issues_sheet(wb, scan_issues, border):
    """Add a sheet listing websites that failed or partly failed."""
    ws = wb.create_sheet('Scan Issues')
    status_order = {'Failed': 0, 'Timed out': 1, 'Partial': 2}
    issues = sorted(
        scan_issues,
        key=lambda i: (status_order.get(i.status, 9), i.company.lower())
    )

    headers = ['S.No', 'Company', 'Website', 'Status', 'What went wrong']
    widths = [8, 25, 60, 12, 90]
    header_fill = PatternFill(
        start_color='B91C1C', end_color='B91C1C', fill_type='solid'
    )
    for col, (h, w) in enumerate(zip(headers, widths), 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True, size=12, color='FFFFFF')
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border
        ws.column_dimensions[get_column_letter(col)].width = w
    ws.freeze_panes = 'A2'

    if not issues:
        ws.sheet_properties.tabColor = '16A34A'
        cell = ws.cell(row=2, column=1,
                       value='All websites were scanned without errors.')
        cell.font = Font(bold=True, color='16A34A')
        ws.merge_cells('A2:E2')
        return

    ws.sheet_properties.tabColor = 'B91C1C'
    ws.auto_filter.ref = f'A1:E{len(issues) + 1}'
    status_fills = {
        'Failed': 'FEE2E2', 'Timed out': 'FFEDD5', 'Partial': 'FEF9C3',
    }
    link_font = Font(color='2563EB', underline='single', size=11)
    data_align = Alignment(vertical='top', wrap_text=True)

    for row_num, issue in enumerate(issues, 2):
        values = [row_num - 1, issue.company, issue.website,
                  issue.status, issue.details]
        for col, value in enumerate(values, 1):
            cell = ws.cell(row=row_num, column=col, value=value)
            cell.alignment = data_align
            cell.border = border
            if col == 3 and str(value).startswith('http'):
                cell.font = link_font
                cell.hyperlink = value
            if col == 4:
                cell.font = Font(bold=True)
                color = status_fills.get(issue.status)
                if color:
                    cell.fill = PatternFill(
                        start_color=color, end_color=color,
                        fill_type='solid'
                    )

    note_row = len(issues) + 3
    ws.cell(row=note_row, column=1, value=(
        'Failed = nothing could be read from the site. '
        'Partial = some pages/searches failed, so some jobs may be missing. '
        'Timed out = the site took too long and was skipped.'
    )).font = Font(italic=True, color='6B7280')
    ws.merge_cells(f'A{note_row}:E{note_row}')


def main():
    logger.info("=" * 50)
    logger.info("INTERNSHIP TRACKER STARTING")
    logger.info(f"Time: {datetime.now().isoformat()}")
    logger.info("=" * 50)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ===== Load permanent job-history =====
    history = load_history()
    history_size_before = len(history)

    # ===== Scrape all sites =====
    try:
        all_postings, stats, scan_issues = asyncio.run(
            run_all_scrapers()
        )
    except Exception as e:
        logger.error(f"Scraping crashed: {e}")
        logger.error(traceback.format_exc())
        all_postings, stats = [], {}
        scan_issues = [ScanIssue(
            'ALL WEBSITES', 'N/A', 'Failed',
            f"The scraping run crashed before finishing: {e}"
        )]

    log_company_stats(stats)

    # ===== Filter & dedupe within today's run =====
    filtered = final_filter(all_postings)
    unique = deduplicate_within_run(filtered)

    # ===== Compare URLs against permanent history =====
    new_jobs = filter_new_postings(unique, history)

    # ===== Update history with ALL of today's URLs =====
    history = add_to_history(unique, history)
    save_history(history)

    logger.info(
        f"History grew from {history_size_before} "
        f"to {len(history)} URLs"
    )

    # ===== Email handling =====
    if not new_jobs:
        logger.info("No NEW URLs since last run.")
        filepath = None
        try:
            filepath = create_excel([], scan_issues)
        except Exception as e:
            logger.error(f"Excel error: {e}")
        try:
            send_no_results_email(
                RECIPIENT_EMAIL,
                filepath=filepath,
                failed_sites=len(scan_issues),
            )
        except Exception as e:
            logger.error(f"Email error: {e}")
        return

    try:
        filepath = create_excel(new_jobs, scan_issues)
    except Exception as e:
        logger.error(f"Failed to create Excel: {e}")
        return

    companies = set(p.company for p in new_jobs)
    try:
        send_email(
            filepath=filepath,
            recipient=RECIPIENT_EMAIL,
            total_jobs=len(new_jobs),
            total_companies=len(companies),
            failed_sites=len(scan_issues),
        )
        logger.info(
            f"Report sent with {len(new_jobs)} NEW URLs!"
        )
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
