import re
import logging
from datetime import datetime, timedelta
from typing import Optional
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


def is_within_last_24_hours(date_str: Optional[str]) -> bool:
    if not date_str:
        return True
    try:
        date_str = date_str.strip()
        lower = date_str.lower()
        if any(word in lower for word in [
            'just now', 'today', 'hour ago', 'hours ago',
            'minute ago', 'minutes ago', 'just posted',
            'new', 'recently'
        ]):
            return True
        if 'yesterday' in lower:
            return True
        if any(word in lower for word in [
            'days ago', 'week ago', 'weeks ago',
            'month ago', 'months ago', 'year ago'
        ]):
            match = re.search(r'(\d+)', date_str)
            if match:
                num = int(match.group(1))
                if 'day' in lower and num <= 1:
                    return True
            return False
        parsed_date = date_parser.parse(date_str, fuzzy=True)
        cutoff = datetime.now() - timedelta(hours=24)
        if parsed_date.tzinfo:
            from datetime import timezone
            cutoff = cutoff.replace(tzinfo=timezone.utc)
        return parsed_date >= cutoff
    except (ValueError, TypeError) as e:
        logger.debug(f"Could not parse date '{date_str}': {e}")
        return True


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
    if not title:
        return False
    lower = title.lower()
    keywords = [
        'intern', 'internship', 'co-op', 'coop', 'co op',
        'student', 'apprentice', 'trainee', 'summer',
        'undergraduate', 'graduate intern'
    ]
    return any(kw in lower for kw in keywords)
