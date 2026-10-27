"""Scraper adapter for Indeed UK."""

import logging
from typing import List
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedJob
from app.utils.dates import parse_date
from app.utils.text import clean_html

logger = logging.getLogger("scrapers.indeed")


class IndeedScraper(BaseScraper):
    """Monitors Indeed UK for Vivid Healthcare Registered Manager roles."""

    name: str = "indeed"
    priority: int = 3

    def __init__(self):
        super().__init__()
        self.search_url = (
            "https://uk.indeed.com/jobs"
            "?q=%22Vivid+Healthcare%22+%22Registered+Manager%22&l=Northern+Ireland"
        )

    async def scrape(self) -> List[ScrapedJob]:
        """Fetch and parse Indeed search results."""
        logger.info(f"[{self.name}] Fetching {self.search_url}")
        html_content = await self.fetch(self.search_url)

        if not html_content:
            return []

        return self._parse_html(html_content)

    def _parse_html(self, html_content: str) -> List[ScrapedJob]:
        jobs: List[ScrapedJob] = []
        soup = BeautifulSoup(html_content, "html.parser")

        cards = soup.select(".job_seen_beacon, .result, .jobCard_mainContent")
        for card in cards:
            title_tag = card.select_one("h2.jobTitle a, [data-jk]")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            job_key = card.get("data-jk") or title_tag.get("data-jk", "")
            link = f"https://uk.indeed.com/viewjob?jk={job_key}" if job_key else self.search_url

            comp_tag = card.select_one("[data-testid='company-name'], .companyName")
            company = comp_tag.get_text(strip=True) if comp_tag else "Unknown"

            # Strictly require "vivid" in company name or title
            comp_lower = company.lower()
            title_lower = title.lower()
            if "vivid" not in comp_lower and "vivid" not in title_lower:
                continue

            loc_tag = card.select_one("[data-testid='text-location'], .companyLocation")
            location = loc_tag.get_text(strip=True) if loc_tag else "Belfast, Northern Ireland"

            sal_tag = card.select_one(".metadata.salary-snippet-container, [data-testid='attribute_snippet_testid']")
            salary = sal_tag.get_text(strip=True) if sal_tag else None

            desc_tag = card.select_one(".job-snippet, .underShelfFooter")
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
                    external_id=job_key or None,
                    raw_payload={"platform": "indeed"},
                )
            )

        logger.info(f"[{self.name}] Found {len(jobs)} genuine matching jobs on Indeed")
        return jobs
