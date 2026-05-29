"""Helper utilities for the scraper."""

import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from dateutil import parser as date_parser

from .keywords import matches_role_keywords, is_us_location

logger = logging.getLogger(__name__)


def is_within_last_24_hours(date_str: Optional[str]) -> bool:
    """Check if a date string represents a time within last 24h.

    Lenient: if we can't parse, we INCLUDE (don't reject).
    This prevents losing valid postings due to weird date formats.
    """
    if not date_str:
        return True  # No date = include

    try:
        date_str = str(date_str).strip()
        lower = date_str.lower()

        # Relative-date keywords (case-insensitive)
        immediate_keywords = [
            'just now', 'today', 'just posted', 'new',
            'recently', 'hour ago', 'hours ago',
            'minute ago', 'minutes ago', 'min ago',
            'mins ago', 'a moment ago', 'an hour ago',
            '< 1 day', 'less than a day',
        ]
        for kw in immediate_keywords:
            if kw in lower:
                return True

        if 'yesterday' in lower:
            return True

        # "X days ago" - only accept 0 or 1
        days_match = re.search(r'(\d+)\s*day', lower)
        if days_match:
            days = int(days_match.group(1))
            return days <= 1

        # Reject older relative dates
        if any(w in lower for w in [
            'week ago', 'weeks ago', 'month ago',
            'months ago', 'year ago', 'years ago'
        ]):
            return False

        # Try parsing as actual date
        parsed_date = date_parser.parse(date_str, fuzzy=True)
        now = datetime.now()
        cutoff = now - timedelta(hours=24)

        # Handle timezone-aware vs naive
        if parsed_date.tzinfo:
            cutoff = cutoff.replace(tzinfo=timezone.utc)
            now_aware = now.replace(tzinfo=timezone.utc)
            # Don't accept future dates either
            if parsed_date > now_aware + timedelta(hours=1):
                return False
        else:
            if parsed_date > now + timedelta(hours=1):
                return False

        return parsed_date >= cutoff

    except (ValueError, TypeError) as e:
        logger.debug(
            f"Could not parse date '{date_str}': {e} "
            f"-- including by default"
        )
        return True  # If we can't parse, include


def normalize_url(base_url: str, relative_url: str) -> str:
    if not relative_url:
        return base_url
    if relative_url.startswith(('http://', 'https://')):
        return relative_url
    if relative_url.startswith('//'):
        return 'https:' + relative_url
    if relative_url.startswith('/'):
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{relative_url}"
    return base_url.rstrip('/') + '/' + relative_url.lstrip('/')


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def is_internship_role(title: str) -> bool:
    """Now uses the expanded keyword matcher."""
    return matches_role_keywords(title)
