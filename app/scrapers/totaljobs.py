"""Scraper adapter for Totaljobs.com."""

import logging
from typing import List
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedJob
from app.utils.dates import parse_date
from app.utils.text import clean_html

logger = logging.getLogger("scrapers.totaljobs")


class TotaljobsScraper(BaseScraper):
    """Monitors Totaljobs for Vivid Healthcare Registered Manager listings."""

    name: str = "totaljobs"
    priority: int = 6

    def __init__(self):
        super().__init__()
        self.search_url = (
            "https://www.totaljobs.com/jobs/registered-manager/in-belfast"
            "?keywords=Vivid+Healthcare"
        )

    async def scrape(self) -> List[ScrapedJob]:
        """Fetch and parse Totaljobs listings."""
        logger.info(f"[{self.name}] Fetching {self.search_url}")
        html_content = await self.fetch(self.search_url)

        if not html_content:
            return []

        return self._parse_html(html_content)

    def _parse_html(self, html_content: str) -> List[ScrapedJob]:
        jobs: List[ScrapedJob] = []
        soup = BeautifulSoup(html_content, "html.parser")

        cards = soup.select("[data-qa='job-item'], article, .job-item")
        for card in cards:
            title_tag = card.select_one("h2 a, [data-qa='job-title-link']")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            link = title_tag.get("href", "")
            if link.startswith("/"):
                link = f"https://www.totaljobs.com{link}"

            comp_tag = card.select_one("[data-qa='company-name'], .company-name, [data-at='job-item-company-name']")
            company = comp_tag.get_text(strip=True) if comp_tag else "Unknown"

            # Strictly require "vivid" in company name or title
            comp_lower = company.lower()
            title_lower = title.lower()
            if "vivid" not in comp_lower and "vivid" not in title_lower:
                continue

            loc_tag = card.select_one("[data-qa='location-snippet'], .location, [data-at='job-item-location']")
            location = loc_tag.get_text(strip=True) if loc_tag else "Belfast, Northern Ireland"

            sal_tag = card.select_one("[data-qa='salary-snippet'], .salary, [data-at='job-item-salary']")
            salary = sal_tag.get_text(strip=True) if sal_tag else None

            desc_tag = card.select_one("[data-qa='job-summary'], .job-intro")
            description = clean_html(desc_tag.get_text(strip=True)) if desc_tag else None

            jobs.append(
                ScrapedJob(
                    source=self.name,
                    source_url=link,
                    title=title,
                    company=company,
                    location=location,
                    salary=salary,
                    description=description,
                    published_at=parse_date("Today"),
                    raw_payload={"board": "totaljobs.com"},
                )
            )

        logger.info(f"[{self.name}] Found {len(jobs)} genuine matching jobs on Totaljobs")
        return jobs
