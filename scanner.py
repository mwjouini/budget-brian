"""
Cloud-native hourly scanner for Vivid Healthcare Registered Manager roles.
Designed to run headless in GitHub Actions or locally, updating static JSON data
consumed by the GitHub Pages dashboard.
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from app.matching import matching_engine
from app.scrapers.base import BaseScraper, ScrapedJob
from app.scrapers.cv_library import CVLibraryScraper
from app.scrapers.glassdoor import GlassdoorScraper
from app.scrapers.indeed import IndeedScraper
from app.scrapers.linkedin import LinkedInScraper
from app.scrapers.nhs_jobs import NHSJobsScraper
from app.scrapers.nijobs import NIJobsScraper
from app.scrapers.reed import ReedScraper
from app.scrapers.totaljobs import TotaljobsScraper
from app.scrapers.vivid_website import VividWebsiteScraper
from app.utils.dedupe import compute_content_hash, detect_material_changes, normalize_url
from app.utils.salary import parse_salary

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("hourly_scanner")

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

JOBS_FILE = DATA_DIR / "jobs.json"
RUNS_FILE = DATA_DIR / "runs.json"
STATS_FILE = DATA_DIR / "stats.json"

# Genuine recruitment platforms and official career portals only
ALL_SCRAPERS: List[type[BaseScraper]] = [
    VividWebsiteScraper,
    ReedScraper,
    LinkedInScraper,
    IndeedScraper,
    NIJobsScraper,
    TotaljobsScraper,
    CVLibraryScraper,
    GlassdoorScraper,
    NHSJobsScraper,
]


def is_northern_ireland(location: str, title: str, description: str) -> bool:
    """Strictly verify that the role is genuinely located in Northern Ireland / Belfast."""
    text_corpus = f"{location} {title} {description}".lower()
    ni_terms = [
        "northern ireland",
        "belfast",
        "antrim",
        "down",
        "derry",
        "londonderry",
        "armagh",
        "fermanagh",
        "tyrone",
        "lisburn",
        "newry",
        "craigavon",
        "newtownabbey",
        "bangor",
    ]
    # English/Scottish/Welsh cities that often get confused in generic national aggregators
    excluded_cities = [
        "liverpool",
        "manchester",
        "birmingham",
        "leeds",
        "sheffield",
        "bristol",
        "london",
        "glasgow",
        "edinburgh",
        "cardiff",
        "newcastle",
        "nottingham",
        "southampton",
        "portsmouth",
    ]
    has_excluded = any(c in f"{title} {location}".lower() for c in excluded_cities)
    has_ni = any(t in text_corpus for t in ni_terms)
    if has_excluded and not has_ni:
        return False
    return has_ni


async def verify_job_url(url: str) -> bool:
    """Validate that the candidate job URL is direct, well-formed, and not a 404 dead link."""
    if not url or not url.startswith(("http://", "https://")):
        return False
    # Reject search engine redirect URLs
    if "duckduckgo.com" in url or "google.com/url" in url:
        return False
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            res = await client.head(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            if res.status_code in (405, 403):
                res = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            if res.status_code in (404, 410):
                logger.warning(f"Rejecting dead job URL (HTTP {res.status_code}): {url}")
                return False
            return res.status_code < 400
    except Exception as exc:
        logger.debug(f"URL check exception for {url}: {exc}")
        return True  # Don't aggressively drop if target site just timed out


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning(f"Failed to read {path}: {exc}")
        return default


def save_json(path: Path, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


async def run_scan() -> Dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    started_iso = started_at.isoformat()
    logger.info(f"=== Starting Vivid Healthcare Job Scan at {started_iso} ===")

    raw_jobs: List[Dict[str, Any]] = load_json(JOBS_FILE, [])
    # Strictly purge any invalid, non-NI, or search redirect legacy jobs
    existing_jobs: List[Dict[str, Any]] = [
        j for j in raw_jobs
        if is_northern_ireland(j.get("location", ""), j.get("title", ""), j.get("description", ""))
        and "duckduckgo.com" not in j.get("source_url", "")
        and "career.com" not in j.get("source_url", "")
        and "studysmarter" not in j.get("source_url", "")
    ]
    existing_runs: List[Dict[str, Any]] = load_json(RUNS_FILE, [])

    jobs_by_url: Dict[str, Dict[str, Any]] = {j["source_url"]: j for j in existing_jobs if j.get("source_url")}
    jobs_by_hash: Dict[str, Dict[str, Any]] = {j["content_hash"]: j for j in existing_jobs if j.get("content_hash")}

    sources_stats: Dict[str, Any] = {}
    scan_errors: List[Dict[str, Any]] = []

    total_found = 0
    total_new = 0
    total_updated = 0

    scrapers = [cls() for cls in ALL_SCRAPERS]
    scrapers.sort(key=lambda s: s.priority)

    for scraper in scrapers:
        s_name = scraper.name
        s_start = datetime.now(timezone.utc)
        jobs: List[ScrapedJob] = []
        err_msg: Optional[str] = None

        try:
            logger.info(f"Scanning source '{s_name}'...")
            jobs = await scraper.scrape()
        except Exception as exc:
            logger.exception(f"Error scraping {s_name}: {exc}")
            err_msg = str(exc)
            scan_errors.append({"source": s_name, "error": err_msg})

        s_duration = round((datetime.now(timezone.utc) - s_start).total_seconds(), 2)
        sources_stats[s_name] = {
            "status": "error" if err_msg else scraper.status,
            "jobs_count": len(jobs),
            "duration_seconds": s_duration,
            "error": err_msg or scraper.last_error,
        }

        # Evaluate jobs
        for sj in jobs:
            total_found += 1

            # 1. Strict Northern Ireland location requirement
            if not is_northern_ireland(sj.location or "", sj.title, sj.description or ""):
                logger.info(f"[{s_name}] Skipped non-Northern Ireland listing: '{sj.title}' ({sj.location})")
                continue

            canonical_url = normalize_url(sj.source_url)

            # 2. Strict Live URL verification (avoid dead/404 links)
            if not await verify_job_url(sj.source_url):
                logger.warning(f"[{s_name}] Skipped unverified or dead URL: {sj.source_url}")
                continue

            c_hash = compute_content_hash(
                title=sj.title,
                company=sj.company,
                location=sj.location,
                description=sj.description,
            )

            match_res = matching_engine.evaluate(
                title=sj.title,
                company=sj.company,
                location=sj.location,
                description=sj.description,
            )

            # Drop third-party noise and non-relevant items
            if match_res.score < 50.0 or match_res.category == "not_relevant":
                continue

            parsed_sal = parse_salary(sj.salary)
            now_iso = datetime.now(timezone.utc).isoformat()

            # Find existing
            existing = jobs_by_url.get(canonical_url) or jobs_by_hash.get(c_hash)
            if existing:
                existing["last_seen_at"] = now_iso
                if existing.get("status") == "expired":
                    existing["status"] = "active"

                # Detect changes
                if existing.get("title") != sj.title or existing.get("salary") != sj.salary:
                    total_updated += 1
                    existing["status"] = "updated"
                    existing["title"] = sj.title
                    existing["company"] = sj.company
                    existing["location"] = sj.location
                    existing["salary"] = sj.salary
                    existing["salary_min"] = parsed_sal.salary_min
                    existing["salary_max"] = parsed_sal.salary_max
                    existing["salary_period"] = parsed_sal.salary_period
                    existing["description"] = sj.description
                    existing["relevance_score"] = match_res.score
                    existing["match_reasons"] = match_res.reasons
                    existing["content_hash"] = c_hash
            else:
                total_new += 1
                new_id = len(existing_jobs) + 1
                job_dict = {
                    "id": new_id,
                    "external_id": sj.external_id,
                    "source": s_name,
                    "source_url": canonical_url or sj.source_url,
                    "title": sj.title,
                    "company": sj.company,
                    "location": sj.location or "Belfast, Northern Ireland",
                    "salary": sj.salary or "Not stated",
                    "salary_min": parsed_sal.salary_min,
                    "salary_max": parsed_sal.salary_max,
                    "salary_period": parsed_sal.salary_period,
                    "job_type": sj.job_type or "Full-time",
                    "description": sj.description,
                    "published_at": sj.published_at.isoformat() if sj.published_at else now_iso,
                    "first_seen_at": now_iso,
                    "last_seen_at": now_iso,
                    "status": "new",
                    "relevance_score": match_res.score,
                    "match_category": match_res.category,
                    "match_reasons": match_res.reasons,
                    "content_hash": c_hash,
                }
                existing_jobs.append(job_dict)
                jobs_by_url[job_dict["source_url"]] = job_dict
                jobs_by_hash[c_hash] = job_dict

    finished_at = datetime.now(timezone.utc)
    finished_iso = finished_at.isoformat()
    duration_total = round((finished_at - started_at).total_seconds(), 2)

    run_entry = {
        "id": len(existing_runs) + 1,
        "started_at": started_iso,
        "finished_at": finished_iso,
        "duration_seconds": duration_total,
        "status": "partial" if scan_errors else "success",
        "sources_scanned": sources_stats,
        "listings_found": total_found,
        "new_listings": total_new,
        "updated_listings": total_updated,
        "errors": scan_errors,
    }
    existing_runs.insert(0, run_entry)  # Newest first
    existing_runs = existing_runs[:50]   # Keep last 50 runs

    # Summary statistics
    active_jobs = [j for j in existing_jobs if j.get("status") in ("new", "active", "updated")]
    strong_jobs = [j for j in active_jobs if j.get("relevance_score", 0) >= 85]
    medium_jobs = [j for j in active_jobs if 60 <= j.get("relevance_score", 0) < 85]

    stats = {
        "last_scan_utc": finished_iso,
        "total_active_jobs": len(active_jobs),
        "strong_matches": len(strong_jobs),
        "medium_matches": len(medium_jobs),
        "sources_monitored": len(ALL_SCRAPERS),
        "last_run_status": run_entry["status"],
        "last_run_duration": duration_total,
        "scan_frequency": "Every 1 Hour (Automated via GitHub Actions)",
    }

    # Save to disk
    save_json(JOBS_FILE, existing_jobs)
    save_json(RUNS_FILE, existing_runs)
    save_json(STATS_FILE, stats)

    logger.info(
        f"=== Scan Completed in {duration_total}s ===\n"
        f"Status: {run_entry['status']} | Active Jobs: {len(active_jobs)} | "
        f"New: {total_new} | Updated: {total_updated}"
    )
    return stats


if __name__ == "__main__":
    asyncio.run(run_scan())
