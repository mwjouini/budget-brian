"""Search engine fallback adapter for monitoring public search results."""

import logging
from typing import List
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedJob
from app.utils.dates import parse_date
from app.utils.text import clean_html

logger = logging.getLogger("scrapers.search_engine")


class SearchEngineScraper(BaseScraper):
    """
    Monitors public search engine indices for newly indexed job adverts referencing
    target terms.
    """

    name: str = "search_engine"
    priority: int = 10

    def __init__(self):
        super().__init__()
        self.duckduckgo_query_url = "https://html.duckduckgo.com/html/?q=%22Vivid+Healthcare%22+%22Registered+Manager%22+Belfast"

    async def scrape(self) -> List[ScrapedJob]:
        """Perform search query and extract any indexed job postings."""
        logger.info(f"[{self.name}] Fetching {self.duckduckgo_query_url}")
        html_content = await self.fetch(self.duckduckgo_query_url)

        if not html_content:
            return []

        return self._parse_html(html_content)

    def _parse_html(self, html_content: str) -> List[ScrapedJob]:
        jobs: List[ScrapedJob] = []
        soup = BeautifulSoup(html_content, "html.parser")

        results = soup.select(".result, .web-result")
        for res in results:
            title_tag = res.select_one(".result__title a, .result__snippet")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            link = title_tag.get("href", "")
            snippet_tag = res.select_one(".result__snippet")
            snippet = clean_html(snippet_tag.get_text(strip=True)) if snippet_tag else ""

            # Only consider results that explicitly mention Vivid Healthcare and Registered Manager
            combined = f"{title.lower()} {snippet.lower()}"
            if "vivid" in combined and "registered manager" in combined:
                jobs.append(
                    ScrapedJob(
                        source=self.name,
                        source_url=link,
                        title=title[:100],
                        company="Vivid Healthcare Search Limited",
                        location="Belfast, Northern Ireland",
                        salary="Competitive",
                        description=snippet,
                        published_at=parse_date("Today"),
                        raw_payload={"engine": "duckduckgo"},
                    )
                )

        logger.info(f"[{self.name}] Found {len(jobs)} indexed matching vacancies")
        return jobs
