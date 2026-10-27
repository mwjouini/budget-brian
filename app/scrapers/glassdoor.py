"""Scraper adapter for Glassdoor."""

import logging
from typing import List
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedJob
from app.utils.dates import parse_date
from app.utils.text import clean_html

logger = logging.getLogger("scrapers.glassdoor")


class GlassdoorScraper(BaseScraper):
    """Monitors Glassdoor for Vivid Healthcare Registered Manager roles."""

    name: str = "glassdoor"
    priority: int = 8

    def __init__(self):
        super().__init__()
        self.search_url = (
            "https://www.glassdoor.co.uk/Job/belfast-registered-manager-jobs-SRCH_IL.0,7_IN225_KO8,26.htm"
        )

    async def scrape(self) -> List[ScrapedJob]:
        """Fetch and parse Glassdoor listings."""
        logger.info(f"[{self.name}] Fetching {self.search_url}")
        html_content = await self.fetch(self.search_url)

        if not html_content:
            return []

        return self._parse_html(html_content)

    def _parse_html(self, html_content: str) -> List[ScrapedJob]:
        jobs: List[ScrapedJob] = []
        soup = BeautifulSoup(html_content, "html.parser")

        cards = soup.select("[data-test='jobListing'], li.JobsList_jobListItem__wjTHv")
        for card in cards:
            title_tag = card.select_one("a.JobCard_jobTitle___daqi, [data-test='job-title']")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            link = title_tag.get("href", "")
            if link.startswith("/"):
                link = f"https://www.glassdoor.co.uk{link}"

            comp_tag = card.select_one("[data-test='employer-name'], .EmployerProfile_employerName__8vlQw")
            company = comp_tag.get_text(strip=True) if comp_tag else "Unknown"

            comp_lower = company.lower()
            title_lower = title.lower()
            if "vivid" not in comp_lower and "vivid" not in title_lower:
                continue

            loc_tag = card.select_one("[data-test='job-location'], .JobCard_location__rCzjx")
            location = loc_tag.get_text(strip=True) if loc_tag else "Belfast, Northern Ireland"

            sal_tag = card.select_one("[data-test='detailSalary']")
            salary = sal_tag.get_text(strip=True) if sal_tag else None

            jobs.append(
                ScrapedJob(
                    source=self.name,
                    source_url=link,
                    title=title,
                    company=company,
                    location=location,
                    salary=salary,
                    description=f"{title} with {company} in {location}. RQIA regulated care.",
                    published_at=parse_date("Today"),
                    raw_payload={"board": "glassdoor.co.uk"},
                )
            )

        logger.info(f"[{self.name}] Found {len(jobs)} genuine matching jobs on Glassdoor")
        return jobs
