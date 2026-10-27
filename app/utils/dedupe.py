"""Deduplication, URL normalization, and change detection utilities."""

import hashlib
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from app.utils.text import normalize_string


TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "ref",
    "trk",
    "fbclid",
    "gclid",
    "source",
    "sessionId",
    "trackingId",
}


def normalize_url(url: Optional[str]) -> str:
    """
    Produce a canonical URL by:
    - Stripping common analytics and tracking query parameters
    - Normalizing scheme and netloc to lowercase
    - Removing trailing slashes
    """
    if not url:
        return ""

    parsed = urlparse(url.strip())
    # Keep only non-tracking query parameters
    filtered_queries = [
        (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=False)
        if k.lower() not in TRACKING_PARAMS
    ]
    # Sort remaining parameters deterministically
    filtered_queries.sort(key=lambda x: x[0])
    new_query = urlencode(filtered_queries)

    # Strip trailing slash from path unless it's just '/'
    path = parsed.path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    canonical = urlunparse((
        parsed.scheme.lower() or "https",
        parsed.netloc.lower(),
        path,
        parsed.params,
        new_query,
        ""  # Strip fragment
    ))
    return canonical


def compute_content_hash(
    title: str,
    company: str,
    location: Optional[str] = None,
    description: Optional[str] = None
) -> str:
    """
    Compute a deterministic SHA-256 hash of normalized core attributes
    to detect identical job advertisements across reposts or scrapers.
    """
    norm_title = normalize_string(title)
    norm_company = normalize_string(company)
    norm_loc = normalize_string(location or "")
    norm_desc = normalize_string(description or "")[:500]  # First 500 chars of normalized text

    payload = f"{norm_title}|{norm_company}|{norm_loc}|{norm_desc}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def detect_material_changes(
    existing_job: Any,
    new_title: str,
    new_salary: Optional[str],
    new_location: Optional[str],
    new_description: Optional[str],
) -> List[Dict[str, Any]]:
    """
    Detect material updates between an existing stored Job and a newly scraped version.
    Returns a list of change records with field_name, old_value, new_value.
    """
    changes: List[Dict[str, Any]] = []

    # Title check
    if normalize_string(existing_job.title) != normalize_string(new_title):
        changes.append({
            "field_name": "title",
            "old_value": existing_job.title,
            "new_value": new_title,
        })

    # Location check
    if normalize_string(existing_job.location or "") != normalize_string(new_location or ""):
        changes.append({
            "field_name": "location",
            "old_value": existing_job.location,
            "new_value": new_location,
        })

    # Salary check
    old_sal = (existing_job.salary or "").strip()
    new_sal = (new_salary or "").strip()
    if old_sal != new_sal and (old_sal or new_sal):
        changes.append({
            "field_name": "salary",
            "old_value": old_sal or None,
            "new_value": new_sal or None,
        })

    # Description significant change check
    old_desc_norm = normalize_string(existing_job.description or "")[:300]
    new_desc_norm = normalize_string(new_description or "")[:300]
    if old_desc_norm and new_desc_norm and old_desc_norm != new_desc_norm:
        changes.append({
            "field_name": "description",
            "old_value": (existing_job.description or "")[:100] + "...",
            "new_value": (new_description or "")[:100] + "...",
        })

    return changes
