"""Scraper adapter for NHS Jobs (jobs.nhs.uk)."""

import logging
from typing import List
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedJob
from app.utils.dates import parse_date

logger = logging.getLogger("scrapers.nhs_jobs")


class NHSJobsScraper(BaseScraper):
    """Monitors NHS Jobs for registered manager and senior care management roles."""

    name: str = "nhs_jobs"
    priority: int = 9

    def __init__(self):
        super().__init__()
        self.search_url = (
            "https://www.jobs.nhs.uk/candidate/search/results"
            "?keyword=Registered%20Manager&location=Belfast"
        )

    async def scrape(self) -> List[ScrapedJob]:
        """Fetch and parse NHS Jobs listings."""
        logger.info(f"[{self.name}] Fetching {self.search_url}")
        html_content = await self.fetch(self.search_url)

        if not html_content:
            return []

        return self._parse_html(html_content)

    def _parse_html(self, html_content: str) -> List[ScrapedJob]:
        jobs: List[ScrapedJob] = []
        soup = BeautifulSoup(html_content, "html.parser")

        cards = soup.select(".nhsuk-card, .search-result, [data-test='search-result']")
        for card in cards:
            title_tag = card.select_one("h2 a, .nhsuk-card__heading a")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            link = title_tag.get("href", "")
            if link.startswith("/"):
                link = f"https://www.jobs.nhs.uk{link}"

            comp_tag = card.select_one(".nhsuk-card__description, .trust-name")
            company = comp_tag.get_text(strip=True) if comp_tag else "Unknown"

            comp_lower = company.lower()
            title_lower = title.lower()
            if "vivid" not in comp_lower and "vivid" not in title_lower:
                continue

            loc_tag = card.select_one(".location")
            location = loc_tag.get_text(strip=True) if loc_tag else "Belfast, Northern Ireland"

            sal_tag = card.select_one(".salary")
            salary = sal_tag.get_text(strip=True) if sal_tag else None

            jobs.append(
                ScrapedJob(
                    source=self.name,
                    source_url=link,
                    title=title,
                    company=company,
                    location=location,
                    salary=salary,
                    description=f"{title} with {company}. Regulated care manager post in Belfast.",
                    published_at=parse_date("Today"),
                    raw_payload={"board": "jobs.nhs.uk"},
                )
            )

        logger.info(f"[{self.name}] Found {len(jobs)} genuine matching jobs on NHS Jobs")
        return jobs
