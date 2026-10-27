"""Scraper adapter for Vivid Healthcare official website."""

import logging
from typing import List
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from app.scrapers.base import BaseScraper, ScrapedJob
from app.utils.dates import parse_date
from app.utils.text import clean_html

logger = logging.getLogger("scrapers.vivid_website")


class VividWebsiteScraper(BaseScraper):
    """Monitors Vivid Healthcare's official website and contact/service portals."""

    name: str = "vivid_website"
    priority: int = 1

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.vivid-healthcare.co.uk"
        self.search_paths = [
            "/contact-2/",
            "/",
        ]

    async def scrape(self) -> List[ScrapedJob]:
        """Scrape jobs and career notices from Vivid Healthcare."""
        jobs: List[ScrapedJob] = []
        seen_urls = set()

        for path in self.search_paths:
            target_url = urljoin(self.base_url, path)
            logger.info(f"[{self.name}] Fetching {target_url}")
            html_content = await self.fetch(target_url)

            if not html_content:
                continue

            parsed = self._parse_html(html_content, target_url)
            for j in parsed:
                if j.source_url not in seen_urls:
                    seen_urls.add(j.source_url)
                    jobs.append(j)

        logger.info(f"[{self.name}] Found {len(jobs)} jobs on Vivid Healthcare website")
        return jobs

    def _parse_html(self, html_content: str, page_url: str) -> List[ScrapedJob]:
        """Parse vacancy cards from HTML."""
        jobs: List[ScrapedJob] = []
        soup = BeautifulSoup(html_content, "html.parser")

        cards = soup.select(".job-item, .job-listing, article.job, .vacancy-card, .search-result-item")
        for card in cards:
            title_elem = card.select_one(".job-title, h2, h3, a.title")
            if not title_elem:
                continue
            title = title_elem.get_text(strip=True)

            link_elem = card.select_one("a[href]")
            link = urljoin(self.base_url, link_elem.get("href", "")) if link_elem else page_url

            location_elem = card.select_one(".job-location, .location, span.loc")
            location = location_elem.get_text(strip=True) if location_elem else "Belfast, Northern Ireland"

            salary_elem = card.select_one(".job-salary, .salary, span.sal")
            salary = salary_elem.get_text(strip=True) if salary_elem else None

            desc_elem = card.select_one(".job-summary, .description, p")
            description = clean_html(desc_elem.get_text(strip=True)) if desc_elem else None

            jobs.append(
                ScrapedJob(
                    source=self.name,
                    source_url=link,
                    title=title,
                    company="Vivid Healthcare Limited",
                    location=location,
                    salary=salary,
                    description=description,
                    published_at=parse_date("Today"),
                    raw_payload={"page_url": page_url},
                )
            )

        return jobs
