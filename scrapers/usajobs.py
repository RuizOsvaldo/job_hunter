"""USAJobs scraper — uses the api.usajobs.gov REST API."""
import hashlib
import logging
import os
import time
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

import config

load_dotenv()

logger = logging.getLogger(__name__)

_BASE_URL = "https://data.usajobs.gov/api/search"
_DAYS_BACK = 5


def _make_job_id(title: str, company: str, url: str) -> str:
    raw = f"{title}|{company}|{url}".lower()
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _parse_salary(position: dict) -> tuple[int | None, int | None]:
    remuneration = position.get("PositionRemuneration", [])
    if not remuneration:
        return None, None
    rem = remuneration[0]
    interval = rem.get("RateIntervalCode", "").upper()
    try:
        lo = float(rem.get("MinimumRange", 0) or 0)
        hi = float(rem.get("MaximumRange", 0) or 0)
    except (ValueError, TypeError):
        return None, None

    if interval == "PA":  # Per Annum
        return (int(lo) if lo else None, int(hi) if hi else None)
    if interval == "PH":  # Per Hour
        return (int(lo * 2080) if lo else None, int(hi * 2080) if hi else None)
    return None, None


def _detect_work_type(position: dict) -> str:
    telework = position.get("TeleworkEligible", "")
    position_schedule = " ".join(
        s.get("Name", "") for s in position.get("PositionSchedule", [])
    ).lower()
    location_names = " ".join(
        loc.get("LocationName", "") for loc in position.get("PositionLocation", [])
    ).lower()

    if "remote" in location_names or telework == "True":
        return "Remote"
    if "hybrid" in position_schedule or "hybrid" in location_names:
        return "Hybrid"
    return "On-site"


def _build_job(position: dict) -> dict:
    title = position.get("PositionTitle", "")
    company = position.get("OrganizationName", "US Federal Government")
    apply_url = position.get("ApplyURI", [""])[0] if position.get("ApplyURI") else ""
    job_id = _make_job_id(title, company, apply_url)

    locations = position.get("PositionLocation", [])
    location_str = locations[0].get("LocationName", "") if locations else ""
    city_state = location_str.split(",")
    city = city_state[0].strip() if city_state else ""
    state = city_state[1].strip() if len(city_state) > 1 else ""

    salary_min, salary_max = _parse_salary(position)

    description = position.get("UserArea", {}).get("Details", {}).get("MajorDuties", "")
    if not description:
        description = position.get("QualificationSummary", "")
    description = (description or "")[:8000]

    date_posted = position.get("PublicationStartDate", "")[:10] if position.get("PublicationStartDate") else ""

    work_type = _detect_work_type(position)

    return {
        "job_id":      job_id,
        "title":       title,
        "company":     company,
        "location":    location_str,
        "city":        city,
        "state":       state,
        "work_type":   work_type,
        "job_type":    "Full-time",
        "salary_min":  salary_min,
        "salary_max":  salary_max,
        "description": description,
        "apply_url":   apply_url,
        "source":      "usajobs",
        "date_posted": date_posted,
        "date_found":  datetime.now().isoformat(),
    }


def _search_keyword(keyword: str, api_key: str, email: str, cutoff: datetime) -> list[dict]:
    """Search USAJobs for one keyword across San Diego + remote."""
    jobs = {}

    for location_name in ["San Diego, CA", "Remote"]:
        params = {
            "Keyword":       keyword,
            "LocationName":  location_name,
            "ResultsPerPage": 100,
            "DatePosted":    _DAYS_BACK,
        }
        headers = {
            "Host":            "data.usajobs.gov",
            "User-Agent":      email,
            "Authorization-Key": api_key,
        }
        try:
            resp = requests.get(_BASE_URL, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("[usajobs] Request failed for keyword=%s location=%s: %s", keyword, location_name, exc)
            continue

        items = data.get("SearchResult", {}).get("SearchResultItems", [])
        for item in items:
            position = item.get("MatchedObjectDescriptor", {})
            pub_date_str = position.get("PublicationStartDate", "")[:10]
            if pub_date_str:
                try:
                    pub_date = datetime.strptime(pub_date_str, "%Y-%m-%d")
                    if pub_date < cutoff:
                        continue
                except ValueError:
                    pass

            job = _build_job(position)
            jobs[job["job_id"]] = job

        time.sleep(1)

    return list(jobs.values())


def scrape_usajobs() -> list[dict]:
    """Scrape USAJobs for analyst roles in San Diego and remote. Returns list of job dicts."""
    api_key = os.getenv("USAJOBS_API_KEY", "")
    email = os.getenv("GMAIL_ADDRESS", "")

    if not api_key:
        logger.warning("[usajobs] USAJOBS_API_KEY not set — skipping USAJobs scrape.")
        return []

    cutoff = datetime.now() - timedelta(days=_DAYS_BACK)
    all_jobs: dict[str, dict] = {}

    for keyword in config.SEARCH_TERMS:
        try:
            results = _search_keyword(keyword, api_key, email, cutoff)
            for job in results:
                all_jobs[job["job_id"]] = job
            logger.info("[usajobs] keyword=%s → %d jobs", keyword, len(results))
        except Exception as exc:
            logger.warning("[usajobs] Unhandled error for keyword=%s: %s", keyword, exc)
        time.sleep(1)

    logger.info("[usajobs] Total unique jobs: %d", len(all_jobs))
    return list(all_jobs.values())
