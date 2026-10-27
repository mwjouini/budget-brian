"""Text manipulation and normalization utilities."""

import html
import re
from typing import Optional
from bs4 import BeautifulSoup


def clean_html(raw_html: Optional[str]) -> str:
    """Strip HTML tags and convert entities into clean plaintext."""
    if not raw_html:
        return ""
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(raw_html, "html.parser")
    
    # Remove script and style elements
    for element in soup(["script", "style", "noscript", "svg"]):
        element.extract()
        
    text = soup.get_text(separator=" ")
    text = html.unescape(text)
    # Collapse multiple whitespaces and newlines
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_string(text: Optional[str]) -> str:
    """Normalize text to lowercase, stripped, with single spaces."""
    if not text:
        return ""
    text = clean_html(text)
    text = text.lower()
    text = re.sub(r"[^\w\s\-\.\&]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_excerpt(text: Optional[str], max_length: int = 300) -> str:
    """Extract a clean, concise excerpt of text for previews."""
    cleaned = clean_html(text)
    if not cleaned:
        return ""
    if len(cleaned) <= max_length:
        return cleaned
    
    truncated = cleaned[:max_length]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated + "..."
