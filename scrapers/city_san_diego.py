"""City of San Diego scraper — governmentjobs.com/careers/sandiego."""
import logging
import re
import time
from datetime import datetime, timedelta
import hashlib

import requests

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.governmentjobs.com/careers/sandiego"
_API_URL = "https://www.governmentjobs.com/careers/sandiego/jobs"
_DAYS_BACK = 5
_KEYWORD = "analyst"


def _make_job_id(title: str, company: str, url: str) -> str:
    raw = f"{title}|{company}|{url}".lower()
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _parse_salary(item: dict) -> tuple[int | None, int | None]:
    salary_str = item.get("salary", "") or ""
    if not salary_str:
        return None, None
    numbers = re.findall(r"[\d,]+\.?\d*", salary_str)
    amounts = []
    for n in numbers:
        try:
            amounts.append(float(n.replace(",", "")))
        except ValueError:
            pass
    if len(amounts) >= 2:
        return int(amounts[0]), int(amounts[1])
    if len(amounts) == 1:
        return int(amounts[0]), None
    return None, None


def _detect_work_type(item: dict) -> str:
    combined = " ".join([
        item.get("location", ""),
        item.get("jobType", ""),
        item.get("description", "")[:300],
    ]).lower()
    if "remote" in combined:
        return "Remote"
    if "hybrid" in combined:
        return "Hybrid"
    return "On-site"


def _build_job(item: dict) -> dict:
    title = item.get("jobTitle", "")
    company = "City of San Diego"
    job_url = item.get("applyUrl") or f"{_BASE_URL}/{item.get('id', '')}"
    job_id = _make_job_id(title, company, job_url)

    location_str = item.get("location", "San Diego, CA")
    city_state = location_str.split(",")
    city = city_state[0].strip() if city_state else "San Diego"
    state = city_state[1].strip() if len(city_state) > 1 else "CA"

    salary_min, salary_max = _parse_salary(item)

    description = item.get("description", "") or item.get("jobDescription", "") or ""
    description = description[:8000]

    date_posted_raw = item.get("openDate", "") or item.get("openFillingDate", "") or ""
    date_posted = date_posted_raw[:10] if date_posted_raw else ""

    return {
        "job_id":      job_id,
        "title":       title,
        "company":     company,
        "location":    location_str,
        "city":        city,
        "state":       state,
        "work_type":   _detect_work_type(item),
        "job_type":    item.get("jobType", "Full-time"),
        "salary_min":  salary_min,
        "salary_max":  salary_max,
        "description": description,
        "apply_url":   job_url,
        "source":      "city_sd",
        "date_posted": date_posted,
        "date_found":  datetime.now().isoformat(),
    }


def scrape_city_san_diego() -> list[dict]:
    """Scrape City of San Diego jobs for analyst roles (last 5 days)."""
    cutoff = datetime.now() - timedelta(days=_DAYS_BACK)
    jobs: dict[str, dict] = {}

    params = {
        "keyword": _KEYWORD,
        "pageSize": 100,
        "page": 1,
        "sort": "datePosted",
        "sortAscending": "false",
    }
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; JobHunterBot/1.0)",
    }

    try:
        resp = requests.get(_API_URL, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("[city_sd] Request failed: %s", exc)
        return []

    items = (
        data.get("jobs")
        or data.get("JobItems")
        or data.get("value")
        or (data if isinstance(data, list) else [])
    )

    for item in items:
        date_str = (item.get("openDate") or item.get("openFillingDate") or "")[:10]
        if date_str:
            try:
                if datetime.strptime(date_str, "%Y-%m-%d") < cutoff:
                    continue
            except ValueError:
                pass

        job = _build_job(item)
        jobs[job["job_id"]] = job
        time.sleep(0.2)

    logger.info("[city_sd] %d analyst jobs found", len(jobs))
    return list(jobs.values())
