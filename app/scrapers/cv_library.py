"""Scraper adapter for CV-Library.co.uk."""

import logging
from typing import List
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedJob
from app.utils.dates import parse_date
from app.utils.text import clean_html

logger = logging.getLogger("scrapers.cv_library")


class CVLibraryScraper(BaseScraper):
    """Monitors CV-Library for Registered Manager vacancies with Vivid Healthcare."""

    name: str = "cv_library"
    priority: int = 7

    def __init__(self):
        super().__init__()
        self.search_url = (
            "https://www.cv-library.co.uk/registered-manager-jobs-in-belfast"
            "?q=Vivid+Healthcare"
        )

    async def scrape(self) -> List[ScrapedJob]:
        """Fetch and parse CV-Library listings."""
        logger.info(f"[{self.name}] Fetching {self.search_url}")
        html_content = await self.fetch(self.search_url)

        if not html_content:
            return []

        return self._parse_html(html_content)

    def _parse_html(self, html_content: str) -> List[ScrapedJob]:
        jobs: List[ScrapedJob] = []
        soup = BeautifulSoup(html_content, "html.parser")

        cards = soup.select(".job-search-description, article.job, .job-result")
        for card in cards:
            title_tag = card.select_one("h2 a, .job__title a")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            link = title_tag.get("href", "")
            if link.startswith("/"):
                link = f"https://www.cv-library.co.uk{link}"

            comp_tag = card.select_one(".job__details-value, .agency, .posted-by")
            company = comp_tag.get_text(strip=True) if comp_tag else "Unknown"

            comp_lower = company.lower()
            title_lower = title.lower()
            if "vivid" not in comp_lower and "vivid" not in title_lower:
                continue

            loc_tag = card.select_one(".job__details-location, .location")
            location = loc_tag.get_text(strip=True) if loc_tag else "Belfast, Northern Ireland"

            sal_tag = card.select_one(".job__details-salary, .salary")
            salary = sal_tag.get_text(strip=True) if sal_tag else None

            desc_tag = card.select_one(".job__description, .desc")
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
                    raw_payload={"board": "cv-library"},
                )
            )

        logger.info(f"[{self.name}] Found {len(jobs)} genuine matching jobs on CV-Library")
        return jobs
