# Job Hunter — App Specs & Overview

A fully automated job hunting tool that scrapes postings, scores them against Osvaldo's
profile using the Claude API, generates tailored resumes and cover letters, auto-applies
via Playwright, and sends push notifications.

---

## How It Works (End-to-End Flow)

```
[Cron: 8am weekdays]
        │
        ▼
[Scraper] ──── searches Indeed + LinkedIn for all SEARCH_TERMS × SEARCH_LOCATIONS
        │       returns list of job dicts, deduplicates by URL, inserts into SQLite
        ▼
[Scorer] ──── calls Claude API (system: prompts/job_hunter_system.md)
        │      scores each unscored job 1–10, saves score + reasons
        │      jobs scoring ≥ 7 → status: pending_review
        │      jobs scoring < 7 → status: scored (kept but skipped)
        ▼
[Notifier] ── sends Gmail notification for each pending_review job
        │      sends daily summary email (total found, scored, pending)
        ▼
[Streamlit UI] — user opens Review Queue, previews documents, approves or rejects
        │
        ▼ (on Approve)
[Document Generator]
        ├── resume_builder.py  → tailored 1-page PDF via ReportLab + Claude
        └── cover_letter.py   → tailored cover letter PDF via ReportLab + Claude
        │      both use prompts/job_hunter_system.md as Claude system prompt
        ▼
[Applicator] ── Playwright logs into Indeed, submits Easy Apply
        │        marks job as "applied" or "apply_failed"
        ▼
[Notifier] ── sends success/failure push notification
```

---

## Module Reference

| File | Purpose |
|------|---------|
| `app.py` | Streamlit UI — 4 tabs: Dashboard, Review Queue, All Jobs, Applied |
| `run.py` | Entry point for background scheduler (APScheduler) |
| `config.py` | Central config — API keys, search terms, thresholds, paths |
| `prompts/job_hunter_system.md` | Claude system prompt — candidate profile, scoring rubric, output format |
| `src/database.py` | SQLite at `data/jobs.db` — all job state lives here |
| `src/scraper.py` | python-jobspy — scrapes Indeed + LinkedIn simultaneously |
| `src/scorer.py` | Claude API scoring — loads system prompt, returns (score, reasons) |
| `src/resume_builder.py` | ReportLab PDF resume — tailors bullets via Claude per job |
| `src/cover_letter.py` | ReportLab PDF cover letter — generated via Claude per job |
| `src/applicator.py` | Playwright — Indeed Easy Apply automation |
| `src/notifier.py` | Gmail SMTP — pending review, applied, failed, daily summary |
| `src/scheduler.py` | APScheduler — weekday 8am cron trigger |
| `assets/base_resume.json` | Source of truth for resume content (gitignored — contains PII) |

---

## Database Schema (`data/jobs.db` → `jobs` table)

| Column | Type | Notes |
|--------|------|-------|
| `job_id` | TEXT PK | MD5 of title+company+url |
| `title` | TEXT | As scraped |
| `company` | TEXT | As scraped |
| `location` | TEXT | As scraped |
| `job_type` | TEXT | full-time / contract / etc. |
| `salary_min` | INTEGER | Annual; parsed from posting |
| `salary_max` | INTEGER | Annual; parsed from posting |
| `description` | TEXT | Up to 8000 chars |
| `apply_url` | TEXT | Direct link |
| `source` | TEXT | indeed / linkedin |
| `date_posted` | TEXT | As reported by source |
| `date_found` | TEXT | ISO timestamp when scraped |
| `status` | TEXT | See status flow below |
| `score` | REAL | 1.0–10.0 from Claude |
| `score_reasons` | TEXT | JSON array of 3 reason strings |
| `resume_path` | TEXT | Path to generated PDF |
| `cover_letter_path` | TEXT | Path to generated PDF |
| `applied_at` | TEXT | ISO timestamp of apply attempt |
| `error_message` | TEXT | Populated on apply_failed |

**Status flow:**
```
found → scored (< 7) — kept, not applied
found → pending_review (≥ 7) → approved → applied
                                          → apply_failed
                             → rejected
```

---

## Configuration (`config.py`)

| Variable | Value | Notes |
|----------|-------|-------|
| `SEARCH_TERMS` | 8 terms | Data Analyst, Business Analyst, Operations Analyst, Program Analyst, Data Coordinator, BI Analyst, Reporting Analyst, Data Analyst Python |
| `SEARCH_LOCATIONS` | San Diego CA, remote | |
| `HOURS_OLD` | 24 | Only postings from last 24h |
| `RESULTS_PER_SEARCH` | 15 | Per term × location combo |
| `AUTO_APPLY_THRESHOLD` | 7 | Score ≥ 7 → pending review |
| `MIN_SALARY` | $80,000 | Annual; used in scoring context |
| `SCHEDULE_HOURS` | [8] | 8:00 AM weekdays |
| `DB_PATH` | `data/jobs.db` | |
| `RESUMES_DIR` | `data/resumes/` | Gitignored |
| `COVER_LETTERS_DIR` | `data/cover_letters/` | Gitignored |
| `BASE_RESUME_PATH` | `assets/base_resume.json` | Gitignored — PII |

---

## Environment Variables (`.env` — never commit)

```
ANTHROPIC_API_KEY=
GMAIL_ADDRESS=
GMAIL_APP_PASSWORD=
NOTIFY_EMAIL=
INDEED_EMAIL=
INDEED_PASSWORD=
```

---

## Claude API Usage

All three Claude calls use `prompts/job_hunter_system.md` as the `system=` parameter.
This file is the single source of truth for Osvaldo's candidate profile, scoring rubric,
and output format. Never hardcode profile data in Python files.

| Call site | Purpose | Model | max_tokens |
|-----------|---------|-------|-----------|
| `src/scorer.py` | Score job 1–10, return JSON | claude-sonnet-4-6 | 512 |
| `src/resume_builder.py` | Tailor resume bullets per job | claude-sonnet-4-6 | 600 |
| `src/cover_letter.py` | Generate cover letter body | claude-sonnet-4-6 | 600 |

---

## Resume Source File (`assets/base_resume.json`)

This file is gitignored and lives only on Osvaldo's machine. It provides the raw
resume content that `resume_builder.py` uses to populate the PDF. Structured as:

```json
{
  "contact": {
    "name": "Osvaldo Ruiz",
    "phone": "619-213-9405",
    "email": "oruiz.code@gmail.com",
    "linkedin": "linkedin.com/in/OsvaldoRuiz",
    "github": "github.com/ruizOsvaldo",
    "website": "ruizosvaldo.github.io"
  },
  "summary": "...",
  "experience": [
    {
      "title": "Program Manager",
      "company": "The LEAGUE of Amazing Programmers",
      "location": "San Diego, CA",
      "dates": "September 2021 – Present",
      "bullets": ["...", "..."]
    }
  ],
  "projects": [
    {
      "name": "...",
      "date": "...",
      "bullets": ["...", "..."]
    }
  ],
  "education": {
    "degree": "B.S. Information Technology, Concentration on Information Systems",
    "school": "Arizona State University",
    "date": "December 2024",
    "honors": "Dean's List, Fall 2023"
  }
}
```

---

## Build Status

| Module | Status |
|--------|--------|
| Streamlit UI (4 tabs) | Done |
| SQLite database | Done |
| Indeed + LinkedIn scraper | Done |
| Claude scorer | Done |
| Resume PDF builder | Done |
| Cover letter PDF builder | Done |
| Gmail notifier | Done |
| APScheduler (weekdays 8am) | Done |
| Playwright auto-apply | Done |
| USAJobs scraper | Not built |
| County of San Diego scraper | Not built |
| City of San Diego scraper | Not built |
| CalCareers scraper (Analyst II, SD only) | Not built |
| Google Sheets logger | Not built |
| ntfy.sh notifications | Not built |
| Weekly summary report | Not built |

---

## Running the App

```bash
# Install deps
pip install -r requirements.txt
playwright install chromium

# Run Streamlit UI only
streamlit run app.py

# Run background scheduler + UI together
python run.py
```

Requires `.env` with all keys set. Requires `assets/base_resume.json` for resume generation.
