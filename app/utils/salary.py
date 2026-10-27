"""Salary extraction and normalization utilities."""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedSalary:
    """Structured salary representation."""
    raw: str
    salary_min: Optional[float]
    salary_max: Optional[float]
    salary_period: Optional[str]  # 'year', 'hour', 'month', 'day', etc.


def _normalize_num(val_str: str) -> float:
    """Convert number string to float, handling 'k' multiplier."""
    val_str = val_str.strip().lower().replace(",", "")
    if val_str.endswith("k"):
        return float(val_str[:-1]) * 1000.0
    return float(val_str)


def parse_salary(salary_text: Optional[str]) -> ParsedSalary:
    """
    Parse a freeform salary string into min, max, and period.
    Examples:
      - '£45,000 - £55,000 per annum' -> min=45000, max=55000, period='year'
      - '£22.50 - £25.00 per hour' -> min=22.5, max=25.0, period='hour'
      - 'Up to £60,000 a year' -> min=None, max=60000, period='year'
      - '£40k - £50k' -> min=40000, max=50000, period='year'
      - 'Competitive' -> min=None, max=None, period=None
    """
    if not salary_text or not salary_text.strip():
        return ParsedSalary(raw="", salary_min=None, salary_max=None, salary_period=None)

    raw = salary_text.strip()
    text = raw.lower()

    # Determine period
    period: Optional[str] = None
    if any(p in text for p in ["hour", "/hr", "per hr", "p/h"]):
        period = "hour"
    elif any(p in text for p in ["day", "/day", "per day", "daily"]):
        period = "day"
    elif any(p in text for p in ["month", "/month", "per month", "monthly"]):
        period = "month"
    elif any(p in text for p in ["annum", "year", "/yr", "per year", "annual", "p.a", "pa"]):
        period = "year"

    # Pattern for numbers like 45k or 45,000 or 22.50
    num_pattern = r"(?:[£$€]\s*)?(\d+(?:\.\d+)?k|\d{1,3}(?:,\d{3})*(?:\.\d+)?)"

    # Check for range: e.g., £45,000 - £55,000 or 45k to 55k
    range_match = re.search(
        rf"{num_pattern}\s*(?:-|–|—|to)\s*{num_pattern}",
        text
    )
    if range_match:
        try:
            min_val = _normalize_num(range_match.group(1))
            max_val = _normalize_num(range_match.group(2))
            
            # Infer period if not specified
            if not period:
                if max_val > 1000:
                    period = "year"
                elif max_val < 150:
                    period = "hour"
                    
            return ParsedSalary(raw=raw, salary_min=min_val, salary_max=max_val, salary_period=period)
        except (ValueError, TypeError):
            pass

    # Check for "up to" pattern
    up_to_match = re.search(rf"(?:up\s+to|max(?:imum)?)\s*{num_pattern}", text)
    if up_to_match:
        try:
            max_val = _normalize_num(up_to_match.group(1))
            if not period:
                period = "year" if max_val > 1000 else "hour"
            return ParsedSalary(raw=raw, salary_min=None, salary_max=max_val, salary_period=period)
        except (ValueError, TypeError):
            pass

    # Check for "from" or "starting at" pattern
    from_match = re.search(rf"(?:from|starts?\s+at|min(?:imum)?)\s*{num_pattern}", text)
    if from_match:
        try:
            min_val = _normalize_num(from_match.group(1))
            if not period:
                period = "year" if min_val > 1000 else "hour"
            return ParsedSalary(raw=raw, salary_min=min_val, salary_max=None, salary_period=period)
        except (ValueError, TypeError):
            pass

    # Single amount match with currency symbol
    single_match = re.search(rf"(?:[£$€]\s*)(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+k)", text)
    if single_match:
        try:
            val = _normalize_num(single_match.group(1))
            if not period:
                period = "year" if val > 1000 else "hour"
            return ParsedSalary(raw=raw, salary_min=val, salary_max=val, salary_period=period)
        except (ValueError, TypeError):
            pass

    return ParsedSalary(raw=raw, salary_min=None, salary_max=None, salary_period=period)
