"""Date parsing and normalization utilities."""

from datetime import datetime, timedelta, timezone
import re
from typing import Optional
from dateutil import parser as dateutil_parser


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse a variety of absolute and relative date strings into a naive UTC datetime.
    Supports:
      - '2026-10-27T10:00:00Z'
      - '27/10/2026'
      - '27 Oct 2026'
      - 'Just posted', 'Today', 'Yesterday'
      - '3 days ago', '2 weeks ago', '5 hours ago'
    """
    if not date_str or not date_str.strip():
        return None

    cleaned = date_str.strip().lower()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Relative shortcuts
    if "just posted" in cleaned or "now" in cleaned or "today" in cleaned:
        return now
    if "yesterday" in cleaned:
        return now - timedelta(days=1)

    # Relative: X hours ago
    hours_match = re.search(r"(\d+)\s*(?:hour|hr)s?\s*ago", cleaned)
    if hours_match:
        return now - timedelta(hours=int(hours_match.group(1)))

    # Relative: X days ago
    days_match = re.search(r"(\d+)\s*days?\s*ago", cleaned)
    if days_match:
        return now - timedelta(days=int(days_match.group(1)))

    # Relative: X weeks ago
    weeks_match = re.search(r"(\d+)\s*weeks?\s*ago", cleaned)
    if weeks_match:
        return now - timedelta(weeks=int(weeks_match.group(1)))

    # Relative: X months ago (approximate 30 days)
    months_match = re.search(r"(\d+)\s*months?\s*ago", cleaned)
    if months_match:
        return now - timedelta(days=int(months_match.group(1)) * 30)

    # Fallback to dateutil parser
    try:
        dt = dateutil_parser.parse(date_str, fuzzy=True, dayfirst=True)
        # Convert timezone-aware to naive UTC
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except (ValueError, TypeError, OverflowError):
        return None
