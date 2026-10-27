"""Scraper adapter for Reed.co.uk recruitment portal."""

import logging
from typing import List
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedJob
from app.utils.dates import parse_date
from app.utils.text import clean_html

logger = logging.getLogger("scrapers.reed")


class ReedScraper(BaseScraper):
    """Monitors Reed.co.uk for Vivid Healthcare Search Limited postings."""

    name: str = "reed"
    priority: int = 5

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.reed.co.uk"
        self.profile_url = "https://www.reed.co.uk/jobs/vivid-healthcare-search-limited/p45258"

    async def scrape(self) -> List[ScrapedJob]:
        """Fetch and parse Reed profile and search results."""
        logger.info(f"[{self.name}] Fetching {self.profile_url}")
        html_content = await self.fetch(self.profile_url)

        if not html_content:
            return []

        return self._parse_html(html_content)

    def _parse_html(self, html_content: str) -> List[ScrapedJob]:
        jobs: List[ScrapedJob] = []
        soup = BeautifulSoup(html_content, "html.parser")

        cards = soup.select("article.job-card, .job-result-card, [data-qa='job-card']")
        for card in cards:
            title_elem = card.select_one("h2 a, .job-card__title a, [data-qa='job-card-title']")
            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)
            link = urljoin(self.base_url, title_elem.get("href", ""))

            company_elem = card.select_one(".job-card__posted-by a, [data-qa='posted-by'], .posted-by")
            company = company_elem.get_text(strip=True) if company_elem else "Vivid Healthcare Search Limited"

            comp_lower = company.lower()
            if "vivid" not in comp_lower and "vivid" not in title.lower():
                continue

            location_elem = card.select_one(".job-card__location, [data-qa='job-card-location'], .location")
            location = location_elem.get_text(strip=True) if location_elem else "Belfast, Northern Ireland"

            salary_elem = card.select_one(".job-card__salary, [data-qa='job-card-salary'], .salary")
            salary = salary_elem.get_text(strip=True) if salary_elem else None

            desc_elem = card.select_one(".job-card__description, .description")
            description = clean_html(desc_elem.get_text(strip=True)) if desc_elem else None

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
                    raw_payload={"platform": "reed.co.uk", "employer_id": "p45258"},
                )
            )

        logger.info(f"[{self.name}] Found {len(jobs)} genuine matching jobs on Reed")
        return jobs
