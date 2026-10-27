"""Scraper adapter for NIJobs.com."""

import logging
from typing import List
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedJob
from app.utils.dates import parse_date
from app.utils.text import clean_html

logger = logging.getLogger("scrapers.nijobs")


class NIJobsScraper(BaseScraper):
    """Monitors NIJobs.com for Vivid Healthcare Registered Manager roles in Northern Ireland."""

    name: str = "nijobs"
    priority: int = 4

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.nijobs.com"
        self.search_url = (
            "https://www.nijobs.com/jobs/registered-manager/in-northern-ireland"
            "?keywords=%22Vivid+Healthcare%22"
        )

    async def scrape(self) -> List[ScrapedJob]:
        """Scrape jobs from NIJobs."""
        logger.info(f"[{self.name}] Fetching {self.search_url}")
        html_content = await self.fetch(self.search_url)

        if not html_content:
            return []

        return self._parse_html(html_content)

    def _parse_html(self, html_content: str) -> List[ScrapedJob]:
        jobs: List[ScrapedJob] = []
        soup = BeautifulSoup(html_content, "html.parser")

        cards = soup.select(".job-item, .job-result, article, [data-testid='job-item']")
        for card in cards:
            title_tag = card.select_one("h2 a, .job-title a, a[data-testid='job-title']")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            link = title_tag.get("href", "")
            if link.startswith("/"):
                link = f"https://www.nijobs.com{link}"

            comp_tag = card.select_one(".company-name, .recruiter, [data-testid='company-name'], .company")
            company = comp_tag.get_text(strip=True) if comp_tag else "Unknown"

            # Strictly require "vivid" in company name or title
            comp_lower = company.lower()
            title_lower = title.lower()
            if "vivid" not in comp_lower and "vivid" not in title_lower:
                continue

            loc_tag = card.select_one(".location, [data-testid='location']")
            location = loc_tag.get_text(strip=True) if loc_tag else "Belfast, Northern Ireland"

            sal_tag = card.select_one(".salary, [data-testid='salary']")
            salary = sal_tag.get_text(strip=True) if sal_tag else None

            desc_tag = card.select_one(".job-intro, .description, p")
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
                    raw_payload={"board": "nijobs.com"},
                )
            )

        logger.info(f"[{self.name}] Found {len(jobs)} genuine matching jobs on NIJobs")
        return jobs
