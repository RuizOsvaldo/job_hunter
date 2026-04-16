"""CalCareers scraper — calcareers.ca.gov, Analyst II in San Diego only."""
import hashlib
import logging
import re
import time
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://calcareers.ca.gov/CalHRPublic/Search/JobSearchResults.aspx"
_BASE_URL = "https://calcareers.ca.gov"
_DAYS_BACK = 5
_KEYWORD = "Analyst II"
_LOCATION = "San Diego"


def _make_job_id(title: str, company: str, url: str) -> str:
    raw = f"{title}|{company}|{url}".lower()
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _parse_salary(text: str) -> tuple[int | None, int | None]:
    if not text:
        return None, None
    numbers = re.findall(r"\$?([\d,]+\.?\d*)", text)
    amounts = []
    for n in numbers:
        try:
            val = float(n.replace(",", ""))
            if val > 100:  # filter out noise like "2" from ranges
                amounts.append(val)
        except ValueError:
            pass
    if len(amounts) >= 2:
        return int(amounts[0]), int(amounts[1])
    if len(amounts) == 1:
        return int(amounts[0]), None
    return None, None


def _parse_date(text: str) -> str:
    """Parse various date formats to YYYY-MM-DD."""
    if not text:
        return ""
    text = text.strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return text[:10]


def _fetch_search_results() -> list[dict]:
    """Fetch CalCareers search results for Analyst II in San Diego."""
    params = {
        "Keywords": _KEYWORD,
        "Location": _LOCATION,
        "JobCategoryId": "",
        "PageSize": 50,
        "CurrentPage": 1,
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; JobHunterBot/1.0)",
        "Accept": "text/html,application/xhtml+xml",
    }

    try:
        resp = requests.get(_SEARCH_URL, params=params, headers=headers, timeout=20)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("[calcareers] Search request failed: %s", exc)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    # CalCareers renders a table of job listings
    job_rows = soup.select("table.job-search-results tr") or soup.select("div.job-result")

    if not job_rows:
        # Fallback: try to find any links that look like job postings
        job_rows = soup.find_all("a", href=re.compile(r"JobControl\.aspx|BulletinPreview"))

    for row in job_rows:
        try:
            if hasattr(row, "find"):
                title_el = row.find("a", href=re.compile(r"JobControl|BulletinPreview"))
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = title_el.get("href", "")
            else:
                title = row.get_text(strip=True)
                href = row.get("href", "")

            if not title or "analyst ii" not in title.lower():
                continue

            job_url = href if href.startswith("http") else _BASE_URL + "/" + href.lstrip("/")

            # Extract salary and date from surrounding cells
            cells = row.find_all("td") if hasattr(row, "find_all") else []
            salary_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            date_text = cells[3].get_text(strip=True) if len(cells) > 3 else ""

            results.append({
                "title": title,
                "url": job_url,
                "salary_text": salary_text,
                "date_text": date_text,
            })
        except Exception:
            continue

    return results


def scrape_calcareers() -> list[dict]:
    """Scrape CalCareers for Analyst II roles in San Diego (last 5 days)."""
    cutoff = datetime.now() - timedelta(days=_DAYS_BACK)
    jobs: dict[str, dict] = {}

    raw_results = _fetch_search_results()
    if not raw_results:
        logger.info("[calcareers] No results returned from search.")
        return []

    for item in raw_results:
        title = item["title"]
        job_url = item["url"]
        date_posted = _parse_date(item.get("date_text", ""))

        # Skip if outside date window
        if date_posted:
            try:
                if datetime.strptime(date_posted, "%Y-%m-%d") < cutoff:
                    continue
            except ValueError:
                pass

        company = "State of California"
        job_id = _make_job_id(title, company, job_url)
        salary_min, salary_max = _parse_salary(item.get("salary_text", ""))

        jobs[job_id] = {
            "job_id":      job_id,
            "title":       title,
            "company":     company,
            "location":    f"{_LOCATION}, CA",
            "city":        _LOCATION,
            "state":       "CA",
            "work_type":   "On-site",
            "job_type":    "Full-time",
            "salary_min":  salary_min,
            "salary_max":  salary_max,
            "description": "",  # detail page fetch skipped to stay lightweight
            "apply_url":   job_url,
            "source":      "calcareers",
            "date_posted": date_posted,
            "date_found":  datetime.now().isoformat(),
        }
        time.sleep(0.5)

    logger.info("[calcareers] %d Analyst II jobs found in San Diego", len(jobs))
    return list(jobs.values())
