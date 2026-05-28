"""Persistent URL-based history of all jobs ever seen."""

import json
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# File location: repo root (two levels up from .github/workflows)
HISTORY_FILE = Path('../../job_history.json')


def _normalize_url(url: str) -> str:
    """Normalize URLs so trivial differences don't create duplicates."""
    if not url:
        return ''
    u = url.strip().lower()
    # Strip trailing slashes
    u = u.rstrip('/')
    # Strip common tracking params
    for sep in ['?utm_', '&utm_', '?src=', '&src=',
                '?source=', '&source=', '?ref=', '&ref=']:
        idx = u.find(sep)
        if idx > 0:
            u = u[:idx]
    return u


def load_history() -> dict:
    """Load the permanent job-history dictionary from disk.

    Structure:
    {
        "<normalized_url>": {
            "first_seen": "2025-01-15T12:00:00",
            "title": "Mechanical Engineer Intern",
            "company": "Acme Corp"
        },
        ...
    }
    """
    if not HISTORY_FILE.exists():
        logger.info("No job_history.json found — starting fresh")
        return {}
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} URLs from job history")
        return data
    except Exception as e:
        logger.warning(f"Could not load history file: {e}")
        return {}


def filter_new_postings(postings: list, history: dict) -> list:
    """Return only postings whose URL is NOT in history."""
    new_postings = []
    for p in postings:
        key = _normalize_url(p.url)
        if not key:
            continue
        if key not in history:
            new_postings.append(p)
    logger.info(
        f"URL history check: {len(postings)} scraped, "
        f"{len(new_postings)} are brand-new URLs, "
        f"{len(postings) - len(new_postings)} were already seen before"
    )
    return new_postings


def add_to_history(postings: list, history: dict) -> dict:
    """Permanently add URLs to history. Existing entries unchanged."""
    now = datetime.now().isoformat()
    added = 0
    for p in postings:
        key = _normalize_url(p.url)
        if not key:
            continue
        if key not in history:
            history[key] = {
                'first_seen': now,
                'title': p.title[:200],
                'company': p.company[:100],
            }
            added += 1
    logger.info(
        f"Added {added} new URLs to history "
        f"(total now: {len(history)})"
    )
    return history


def save_history(history: dict) -> None:
    """Save the permanent job-history to disk."""
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, sort_keys=True)
        logger.info(
            f"Saved job_history.json with {len(history)} entries"
        )
    except Exception as e:
        logger.error(f"Failed to save history file: {e}")
