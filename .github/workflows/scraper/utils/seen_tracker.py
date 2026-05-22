"""Track previously-seen job postings across runs."""

import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# File location: stored at repo root (one level up from .github/workflows)
SEEN_FILE = Path('../../seen_jobs.json')

# Keep entries for this many days, then auto-prune
RETENTION_DAYS = 30


def _job_key(posting) -> str:
    """Create a unique stable key for a job posting."""
    raw = (
        posting.url.lower().strip() + '|' +
        posting.title.lower().strip() + '|' +
        posting.company.lower().strip()
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def load_seen() -> dict:
    """Load the seen-jobs dictionary from disk."""
    if not SEEN_FILE.exists():
        logger.info("No seen_jobs.json found — starting fresh")
        return {}
    try:
        with open(SEEN_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} previously-seen jobs")
        return data
    except Exception as e:
        logger.warning(f"Could not load seen file: {e}")
        return {}


def prune_old(seen: dict) -> dict:
    """Remove entries older than RETENTION_DAYS."""
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    cutoff_str = cutoff.isoformat()
    pruned = {
        k: v for k, v in seen.items()
        if v.get('first_seen', '9999') >= cutoff_str
    }
    removed = len(seen) - len(pruned)
    if removed > 0:
        logger.info(f"Pruned {removed} entries older than {RETENTION_DAYS}d")
    return pruned


def filter_new_postings(postings: list, seen: dict) -> list:
    """Return only postings not in seen dict."""
    new_postings = []
    for p in postings:
        key = _job_key(p)
        if key not in seen:
            new_postings.append(p)
    logger.info(
        f"Filtered by seen-tracker: "
        f"{len(postings)} input -> {len(new_postings)} new"
    )
    return new_postings


def mark_as_seen(postings: list, seen: dict) -> dict:
    """Add postings to the seen dict and return updated dict."""
    now = datetime.now().isoformat()
    for p in postings:
        key = _job_key(p)
        if key not in seen:
            seen[key] = {
                'first_seen': now,
                'title': p.title[:200],
                'company': p.company[:100],
                'url': p.url[:500],
            }
    return seen


def save_seen(seen: dict) -> None:
    """Save the seen-jobs dictionary to disk."""
    try:
        SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SEEN_FILE, 'w', encoding='utf-8') as f:
            json.dump(seen, f, indent=2)
        logger.info(f"Saved {len(seen)} entries to seen_jobs.json")
    except Exception as e:
        logger.error(f"Failed to save seen file: {e}")
