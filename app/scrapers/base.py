"""Base scraper class and common data models."""

from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional
import httpx
from app.config import settings

logger = logging.getLogger("scrapers")


@dataclass
class ScrapedJob:
    """Standardized job advertisement extracted by any scraper adapter."""
    source: str
    source_url: str
    title: str
    company: str
    location: Optional[str] = None
    salary: Optional[str] = None
    job_type: Optional[str] = None
    description: Optional[str] = None
    published_at: Optional[datetime] = None
    external_id: Optional[str] = None
    raw_payload: Optional[Dict[str, Any]] = field(default_factory=dict)


class BaseScraper(ABC):
    """Abstract base scraper adapter with resilient HTTP client and rate limiting."""

    name: str = "base"
    enabled: bool = True
    priority: int = 10
    timeout: float = 25.0
    max_retries: int = 3
    retry_delay: float = 2.0

    def __init__(self):
        self.status: str = "active"  # active, degraded, error
        self.last_error: Optional[str] = None
        self.headers = {
            "User-Agent": settings.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
            "Cache-Control": "no-cache",
        }

    async def fetch(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        method: str = "GET",
        data: Optional[Any] = None,
    ) -> Optional[str]:
        """
        Execute an HTTP request with exponential backoff retry.
        Returns response text or None on persistent failure.
        """
        req_headers = {**self.headers, **(headers or {})}
        attempt = 0
        current_delay = self.retry_delay

        while attempt < self.max_retries:
            attempt += 1
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                    verify=True,
                ) as client:
                    if method.upper() == "POST":
                        res = await client.post(url, params=params, headers=req_headers, data=data)
                    else:
                        res = await client.get(url, params=params, headers=req_headers)

                    if res.status_code == 200:
                        self.status = "active"
                        self.last_error = None
                        return res.text
                    elif res.status_code == 403:
                        logger.warning(
                            f"[{self.name}] Anti-bot protection / 403 challenge encountered on {url}"
                        )
                        self.status = "degraded"
                        self.last_error = "HTTP 403 Challenge"
                        return None
                    elif res.status_code == 404:
                        logger.info(f"[{self.name}] Target page not found (HTTP 404): {url}")
                        return None
                    elif res.status_code == 429:
                        logger.warning(
                            f"[{self.name}] Rate limit 429 encountered on {url}, sleeping..."
                        )
                        self.status = "degraded"
                        self.last_error = "HTTP 429 Rate Limit"
                        await asyncio.sleep(current_delay * 2)
                    else:
                        logger.warning(
                            f"[{self.name}] Request returned HTTP {res.status_code} on {url}"
                        )
                        return None
            except (httpx.RequestError, httpx.TimeoutException) as exc:
                err_str = str(exc)
                logger.warning(f"[{self.name}] Network issue on attempt {attempt}/{self.max_retries}: {err_str}")
                self.last_error = err_str
                # Fast fail if DNS resolution failed
                if "getaddrinfo" in err_str or "ConnectError" in err_str:
                    break

            if attempt < self.max_retries:
                await asyncio.sleep(current_delay)
                current_delay *= 2.0

        self.status = "error"
        logger.error(f"[{self.name}] Failed to fetch {url}")
        return None

    @abstractmethod
    async def scrape(self) -> List[ScrapedJob]:
        """Scrape jobs from the source and return standardized ScrapedJob objects."""
        pass
