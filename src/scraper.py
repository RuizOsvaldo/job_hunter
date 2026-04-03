"""Job scraping via python-jobspy."""
import re
import hashlib
from datetime import datetime
import pandas as pd
from jobspy import scrape_jobs

import config
from src.database import upsert_job

_US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC", "PR", "GU", "VI",
}

_US_STATE_NAMES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
    "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
    "missouri", "montana", "nebraska", "nevada", "new hampshire", "new jersey",
    "new mexico", "new york", "north carolina", "north dakota", "ohio",
    "oklahoma", "oregon", "pennsylvania", "rhode island", "south carolina",
    "south dakota", "tennessee", "texas", "utah", "vermont", "virginia",
    "washington", "west virginia", "wisconsin", "wyoming", "district of columbia",
}


def _make_job_id(title: str, company: str, url: str) -> str:
    raw = f"{title}|{company}|{url}".lower()
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _parse_salary(row) -> tuple[int | None, int | None]:
    """Extract annual salary from jobspy min_amount/max_amount fields."""
    interval = str(row.get("interval") or "").lower()
    lo = row.get("min_amount")
    hi = row.get("max_amount")

    if lo is None and hi is None:
        return None, None

    try:
        lo = float(lo) if lo is not None else None
        hi = float(hi) if hi is not None else None
    except (ValueError, TypeError):
        return None, None

    # Convert hourly to annual
    if interval == "hourly" or (lo and lo < 500):
        lo = lo * 2080 if lo else None
        hi = hi * 2080 if hi else None

    return (int(lo) if lo else None), (int(hi) if hi else None)


def _parse_location(location_str: str) -> tuple[str, str]:
    """
    Parse jobspy location string into (city, state).
    Handles formats: 'San Diego, CA', 'San Diego, CA, US', 'Remote', etc.
    Returns ('', '') if unparseable.
    """
    if not location_str:
        return "", ""

    loc = location_str.strip()

    # Strip trailing country code: ", US" or ", USA"
    loc = re.sub(r",?\s*(US|USA)$", "", loc, flags=re.IGNORECASE).strip()

    parts = [p.strip() for p in loc.split(",")]

    if len(parts) >= 2:
        city = parts[0]
        state = parts[1].upper().strip()
        return city, state
    elif len(parts) == 1:
        # Could be just a state name or "Remote"
        token = parts[0].upper().strip()
        if token in _US_STATES:
            return "", token
        return parts[0], ""

    return "", ""


def _resolve_work_type(row, is_remote: bool, work_from_home_type) -> str:
    """Return 'Remote', 'Hybrid', or 'On-site'."""
    wfh = str(work_from_home_type or "").lower()
    if "hybrid" in wfh:
        return "Hybrid"
    if is_remote or "remote" in wfh:
        return "Remote"
    return "On-site"


def _is_us_job(row, city: str, state: str) -> bool:
    """
    Hard filter — only pass jobs that are verifiably US-based.

    Rules (in order):
    1. Non-USD currency → reject
    2. state is a known US state abbreviation → accept
    3. Remote with no state → accept (we searched country_indeed='USA')
    4. State token is not a US state and not blank → reject
    5. city or location contains a known US state name → accept
    6. Anything else → reject (unknown foreign location)
    """
    # 1. Currency — hard reject non-USD
    currency = str(row.get("currency") or "").strip().upper()
    if currency and currency not in ("USD", "US", ""):
        return False

    location = str(row.get("location") or "").strip().lower()
    is_remote = bool(row.get("is_remote"))

    # 2. State is a known US abbreviation
    if state and state.upper() in _US_STATES:
        return True

    # 3. Explicitly remote with no state (trusted because country_indeed='USA')
    if is_remote and not state:
        return True
    if location in ("remote", "anywhere", "united states", "us", "usa", ""):
        return True

    # 4. State-like token present but not a US state → foreign
    if state and state.upper() not in _US_STATES:
        return False

    # 5. Location string contains a US state name written out
    if any(name in location for name in _US_STATE_NAMES):
        return True

    # 6. Unknown — reject rather than let foreign jobs through
    return False


def run_search() -> int:
    """Run all configured searches. Returns count of new jobs inserted."""
    new_count = 0

    for term in config.SEARCH_TERMS:
        for location in config.SEARCH_LOCATIONS:
            try:
                df = scrape_jobs(
                    site_name=["indeed", "linkedin", "glassdoor", "zip_recruiter", "google"],
                    search_term=term,
                    location=location,
                    results_wanted=config.RESULTS_PER_SEARCH,
                    hours_old=config.HOURS_OLD,
                    country_indeed="USA",
                    linkedin_fetch_description=True,
                )
            except Exception as e:
                print(f"[scraper] Error for '{term}' @ '{location}': {e}")
                continue

            if df is None or df.empty:
                continue

            for _, row in df.iterrows():
                title   = str(row.get("title",   "")).strip()
                company = str(row.get("company", "")).strip()
                apply_url = str(row.get("job_url", "")).strip()

                if not title or not company or not apply_url:
                    continue

                city, state = _parse_location(str(row.get("location") or ""))
                is_remote = bool(row.get("is_remote"))
                work_type = _resolve_work_type(row, is_remote, row.get("work_from_home_type"))

                if not _is_us_job(row, city, state):
                    print(f"[scraper] SKIP (non-US): {title} @ {company} — {row.get('location', '')} | currency={row.get('currency', '')}")
                    continue

                salary_min, salary_max = _parse_salary(row)

                if salary_max and salary_max < config.MIN_SALARY:
                    continue

                job = {
                    "job_id":       _make_job_id(title, company, apply_url),
                    "title":        title,
                    "company":      company,
                    "location":     str(row.get("location", "")).strip(),
                    "city":         city,
                    "state":        state,
                    "work_type":    work_type,
                    "job_type":     str(row.get("job_type", "")).strip(),
                    "salary_min":   salary_min,
                    "salary_max":   salary_max,
                    "description":  str(row.get("description", "")).strip()[:8000],
                    "apply_url":    apply_url,
                    "source":       str(row.get("site", "unknown")),
                    "date_posted":  str(row.get("date_posted", "")).strip(),
                    "date_found":   datetime.now().isoformat(),
                }

                if upsert_job(job):
                    new_count += 1
                    print(f"[scraper] NEW: {title} @ {company} — {work_type}, {city}, {state}")

    return new_count
