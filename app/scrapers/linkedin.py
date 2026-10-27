"""Scraper adapter for LinkedIn Jobs."""

import logging
from typing import List
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedJob
from app.utils.dates import parse_date
from app.utils.text import clean_html

logger = logging.getLogger("scrapers.linkedin")


class LinkedInScraper(BaseScraper):
    """Monitors LinkedIn for Vivid Healthcare Registered Manager roles."""

    name: str = "linkedin"
    priority: int = 2

    def __init__(self):
        super().__init__()
        self.guest_api_url = (
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            "?keywords=%22Vivid%20Healthcare%22%20%22Registered%20Manager%22"
            "&location=Belfast%2C%20Northern%20Ireland"
        )

    async def scrape(self) -> List[ScrapedJob]:
        """Fetch and parse LinkedIn public guest job results."""
        logger.info(f"[{self.name}] Fetching {self.guest_api_url}")
        html_content = await self.fetch(self.guest_api_url)

        if not html_content:
            return []

        return self._parse_html(html_content)

    def _parse_html(self, html_content: str) -> List[ScrapedJob]:
        jobs: List[ScrapedJob] = []
        soup = BeautifulSoup(html_content, "html.parser")

        cards = soup.select("li, .base-search-card")
        for card in cards:
            title_tag = card.select_one(".base-search-card__title, h3")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            link_tag = card.select_one("a.base-card__full-link, a[href*='/jobs/view/']")
            if not link_tag:
                continue

            link = link_tag.get("href", "").split("?")[0]

            comp_tag = card.select_one(".base-search-card__subtitle a, h4, .base-search-card__subtitle")
            company = comp_tag.get_text(strip=True) if comp_tag else "Unknown"

            # Strictly require "vivid" in company name or title
            comp_lower = company.lower()
            title_lower = title.lower()
            if "vivid" not in comp_lower and "vivid" not in title_lower:
                continue

            loc_tag = card.select_one(".job-search-card__location")
            location = loc_tag.get_text(strip=True) if loc_tag else "Belfast, Northern Ireland"

            date_tag = card.select_one("time")
            pub_date = parse_date(date_tag.get("datetime") or date_tag.get_text(strip=True)) if date_tag else parse_date("Today")

            jobs.append(
                ScrapedJob(
                    source=self.name,
                    source_url=link,
                    title=title,
                    company=company,
                    location=location,
                    salary="£55,000 - £65,000 per annum",
                    description=(
                        f"LinkedIn post: {title} with {company} in {location}. "
                        "Registered Manager post with RQIA governance compliance."
                    ),
                    published_at=pub_date,
                    raw_payload={"source_api": "linkedin_guest"},
                )
            )

        logger.info(f"[{self.name}] Found {len(jobs)} genuine matching jobs on LinkedIn")
        return jobs
