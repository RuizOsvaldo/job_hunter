# Sprint 01 — Government Scrapers, Pipeline Integration, Weekly Summary, Resume Tailoring

## Goal
Add four government job scrapers, wire them into the pipeline, add a Sunday weekly summary email, and extend resume generation to tailor the summary and skills sections (not just bullets) while preserving the exact 1-page layout.

## Context
- Requirements gathered 2026-04-07
- Google Sheets logger dropped as redundant (Streamlit UI covers the need)
- Government scrapers fetch last 5 days of postings (not 24h like jobspy)
- USAJobs: San Diego + remote; County/City SD: keyword "analyst"; CalCareers: "Analyst II" + San Diego only
- Rate limit strategy: small result sets, 1-second delays between requests
- Unavailable source → skip + log warning, never kill the run
- Weekly summary: Sundays 10am, Gmail + visible in app, includes counts + top applied matches
- Resume tailoring: tailor summary paragraph and skills emphasis in addition to existing bullet tailoring; no layout, font, or margin changes

## Architecture Notes
- All four government scrapers return the same dict format as `src/scraper.py`
- County SD and City SD both use the governmentjobs.com REST-style query params API (no Playwright needed)
- USAJobs uses the documented REST API at api.usajobs.gov with `USAJOBS_API_KEY` from `.env`
- CalCareers uses keyword search on calcareers.ca.gov — the site has a JSON search endpoint
- Weekly summary added as `notify_weekly_summary()` in `src/notifier.py`; scheduler gets a Sunday 10am cron job
- Resume tailoring: add `_tailor_summary()` and `_tailor_skills()` helpers alongside existing `_tailor_bullets()`; single LLM call for summary, skills section gets keyword emphasis only — no layout changes

**Alternative considered:** Single combined LLM call to tailor summary + bullets + skills together.
**Ruled out:** Increases token usage, harder to recover from partial failures, and makes the prompt too long to reliably return structured JSON for three different sections.

## Tickets

### Ticket 01-01: USAJobs Scraper
**Type:** Feature
**Files in scope:** `scrapers/usajobs.py`, `scrapers/__init__.py`
**Description:** Call api.usajobs.gov with keyword terms matching Osvaldo's target titles, filtered to San Diego + remote, last 5 days. Return standard job dict list.
**Acceptance Criteria:**
- [ ] Uses `USAJOBS_API_KEY` from `.env` via `os.getenv()`
- [ ] Fetches jobs for all target title keywords from `config.SEARCH_TERMS`
- [ ] Filters to San Diego and remote locations
- [ ] Returns last 5 days of postings
- [ ] Returns list of dicts matching the standard scraper format
- [ ] Deduplicates by job_id before returning
- [ ] Source field is `"usajobs"`
- [ ] Errors are caught, logged, and return empty list (non-fatal)
**Edge Cases:**
- API key missing → log warning, return []
- API returns 0 results → return []
- Pagination: fetch up to 100 results per keyword (API max per page)
- Duplicate listings across keyword searches → deduplicated by job_id

---

### Ticket 01-02: County of San Diego Scraper
**Type:** Feature
**Files in scope:** `scrapers/county_san_diego.py`
**Description:** Query governmentjobs.com/careers/sdcounty using keyword "analyst" via query params. Return standard job dict list.
**Acceptance Criteria:**
- [ ] Uses `https://www.governmentjobs.com/careers/sdcounty` with keyword query param
- [ ] Keyword filter: "analyst"
- [ ] Returns last 5 days of postings
- [ ] Returns list of dicts matching the standard scraper format
- [ ] Source field is `"county_sd"`
- [ ] Errors caught, logged, return [] (non-fatal)
**Edge Cases:**
- Site unavailable → log warning, return []
- No results → return []
- Pagination: respect page size, don't fetch more than needed

---

### Ticket 01-03: City of San Diego Scraper
**Type:** Feature
**Files in scope:** `scrapers/city_san_diego.py`
**Description:** Same platform as county (governmentjobs.com/careers/sandiego), same approach.
**Acceptance Criteria:**
- [ ] Uses `https://www.governmentjobs.com/careers/sandiego` with keyword query param
- [ ] Keyword filter: "analyst"
- [ ] Returns last 5 days of postings
- [ ] Returns list of dicts matching the standard scraper format
- [ ] Source field is `"city_sd"`
- [ ] Errors caught, logged, return [] (non-fatal)
**Edge Cases:**
- Same as 01-02

---

### Ticket 01-04: CalCareers Scraper
**Type:** Feature
**Files in scope:** `scrapers/calcareers.py`
**Description:** Search calcareers.ca.gov for "Analyst II" in San Diego only. Strict scope — no other titles or locations.
**Acceptance Criteria:**
- [ ] Keyword: "Analyst II" only
- [ ] Location filter: San Diego only
- [ ] Returns last 5 days of postings
- [ ] Returns list of dicts matching the standard scraper format
- [ ] Source field is `"calcareers"`
- [ ] Errors caught, logged, return [] (non-fatal)
**Edge Cases:**
- Site unavailable → log warning, return []
- No results → return []

---

### Ticket 01-05: Pipeline Integration
**Type:** Feature
**Files in scope:** `src/scheduler.py`
**Description:** Wire all four government scrapers into `run_pipeline()` so they run alongside the existing jobspy scraper.
**Acceptance Criteria:**
- [ ] All four scrapers called in `run_pipeline()`
- [ ] Each scraper wrapped in try/except — failure of one does not stop others
- [ ] Results passed to `upsert_job()` same as jobspy results
- [ ] Total new job count includes government scraper results
**Edge Cases:**
- One scraper raises an unhandled exception → catch, log, continue

---

### Ticket 01-06: Weekly Summary Report
**Type:** Feature
**Files in scope:** `src/notifier.py`, `src/scheduler.py`, `src/database.py`
**Description:** Add `notify_weekly_summary()` to notifier, a `get_weekly_stats()` query to database, and a Sunday 10am cron job in scheduler.
**Acceptance Criteria:**
- [ ] `notify_weekly_summary()` sends Gmail with: jobs found, scored, applied, rejected counts + top applied matches (title, company, score, apply URL)
- [ ] `get_weekly_stats()` queries the last 7 days
- [ ] Scheduler runs the weekly summary every Sunday at 10am
- [ ] Weekly summary is separate from the daily summary — does not replace it
**Edge Cases:**
- No applied jobs this week → show "No applications this week" in top matches section
- Gmail send failure → log, do not crash scheduler

---

### Ticket 01-07: Resume Full Tailoring
**Type:** Feature
**Files in scope:** `src/resume_builder.py`
**Description:** Add `_tailor_summary()` to rewrite the summary paragraph for the job, and update `_tailor_skills()` to reorder/emphasize skills relevant to the job. Layout, fonts, margins, and page count must not change.
**Acceptance Criteria:**
- [ ] Summary paragraph is rewritten per job via LLM — same length, same style
- [ ] Skills row order/emphasis adjusted to front-load relevant skills
- [ ] No font size, margin, or layout changes
- [ ] Resume stays 1 page
- [ ] LLM calls go through `src/llm.py`
- [ ] Fallback to original summary/skills if LLM call fails
**Edge Cases:**
- LLM returns text that's too long → truncate to 280 characters before rendering
- LLM call fails → use original hardcoded summary and skills (already handled by try/except pattern)
