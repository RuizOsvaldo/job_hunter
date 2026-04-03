# CLAUDE.md -- Job Hunter App

This file gives you full context on this project. Read it at the start of every session.
Do not skip any section.

---

## What This App Does

This is a job hunting automation tool built and owned by Osvaldo. It scrapes job postings
from multiple job boards and government job portals, scores each one against Osvaldo's
profile using the Claude API, generates tailored resumes and cover letters for strong
matches, auto-applies via Playwright, logs every action to Google Sheets, and sends push
notifications via ntfy.sh. It runs on a cron schedule weekdays at 8am.

---

## Owner Profile

**Name:** Osvaldo  
**Location:** San Diego, CA  
**Target roles:** Data Analyst, Business Analyst (also: Program Analyst, Operations Analyst,
Data Coordinator)  
**Target locations:** San Diego on-site or hybrid, fully remote nationwide  

**Technical stack (what he actually knows -- do not suggest tools outside this unless asked):**
- Python (primary language)
- SQL
- Google Apps Script (JavaScript)
- Google Cloud Platform (BigQuery, Cloud Storage, Cloud Functions)
- AWS (in progress -- Solutions Architect Associate cert underway)
- Docker, Ansible
- Google Sheets (advanced), Looker Studio
- Git / GitHub
- Playwright (browser automation)
- Web scraping
- ntfy.sh (push notifications)
- Cron scheduling

**Background:**
- Program Manager at The LEAGUE of Amazing Programmers (coding education nonprofit)
- Programs Coordinator at Border Angels (humanitarian nonprofit)
- Information Systems background
- DevOps cert in progress (COMP 643 -- Debian, SSH, DNS, Docker, Ansible)

---

## App Architecture -- 15 Steps

The app is scoped across 15 steps. Reference this when adding features or debugging so
nothing is built out of sequence.

```
Step 1  -- Cron trigger (weekdays 8am)
Step 2  -- Scrape Indeed
Step 3  -- Scrape LinkedIn
Step 4  -- Scrape Glassdoor
Step 5  -- Scrape USAJobs
Step 6  -- Scrape County of San Diego (https://www.governmentjobs.com/careers/sdcounty)
Step 7  -- Scrape City of San Diego (https://www.governmentjobs.com/careers/sandiego)
Step 8  -- Scrape CalCareers -- Analyst II roles in San Diego only (https://calcareers.ca.gov)
Step 9  -- Deduplicate listings across all sources
Step 10 -- Score each job via Claude API (see scoring system below)
Step 11 -- Filter -- keep only jobs scoring 7 or above
Step 12 -- Generate tailored resume bullets via Claude API
Step 13 -- Generate tailored cover letter via Claude API
Step 14 -- Auto-apply via Playwright
Step 15 -- Log results to Google Sheets (job title, company, score, source, status, date)
Step 16 -- Send push notification via ntfy.sh on apply or failure
Step 17 -- Error handling and retry logic
Step 18 -- Weekly summary report (optional / stretch goal)
```

---

## Scoring System

Job scoring uses the Claude API with the system prompt located at:

```
prompts/job_hunter_system.md
```

This file contains the full candidate profile, a 1-10 scoring rubric, weighted scoring
factors, and output format instructions. It is the source of truth for all scoring and
generation logic. Do not hardcode scoring criteria in Python -- always load this file and
pass it as the system prompt.

**How to load it:**

```python
with open("prompts/job_hunter_system.md", "r") as f:
    system_prompt = f.read()

response = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=2000,
    system=system_prompt,
    messages=[
        {"role": "user", "content": f"Evaluate this job posting:\n\n{job_description}"}
    ]
)
```

**Score threshold:** Only proceed to resume/cover letter generation and auto-apply for jobs
scoring 7 or above. Log and skip anything below 7.

---

## Project Structure

```
job-hunter/
├── CLAUDE.md                  -- This file. Read every session.
├── prompts/
│   └── job_hunter_system.md   -- Claude API system prompt (scoring + generation logic)
├── scrapers/
│   ├── indeed.py
│   ├── linkedin.py
│   ├── glassdoor.py
│   ├── usajobs.py
│   ├── county_san_diego.py    -- governmentjobs.com/careers/sdcounty
│   ├── city_san_diego.py      -- governmentjobs.com/careers/sandiego
│   └── calcareers.py          -- calcareers.ca.gov, Analyst II, San Diego only
├── pipeline/
│   ├── deduplicator.py
│   ├── scorer.py              -- Calls Claude API with system prompt
│   ├── generator.py           -- Resume bullets + cover letter generation
│   └── applicator.py         -- Playwright auto-apply logic
├── integrations/
│   ├── sheets.py              -- Google Sheets logging
│   └── notifications.py      -- ntfy.sh push notifications
├── cron/
│   └── schedule.py            -- Weekday 8am trigger
├── logs/
├── tests/
├── requirements.txt
└── .env                       -- API keys, sheet IDs, ntfy topic (never commit this)
```

If files or folders do not exist yet, create them in this structure. Do not reorganize
without asking.

---

## Google Sheets Logging

Each job application attempt should log a row with these columns:

| Column | Value |
|--------|-------|
| Date | Timestamp of the run |
| Job Title | As scraped |
| Company | As scraped |
| Source | indeed / linkedin / glassdoor / usajobs / county_sd / city_sd / calcareers |
| Score | Claude API score (1-10) |
| Status | applied / skipped / failed |
| Job URL | Direct link |
| Notes | Error message or skip reason if applicable |

---

## ntfy.sh Notifications

Send a push notification for every apply attempt (success or failure) and for any
scraper errors. Topic name and server are stored in `.env`. Never hardcode them.

---

## Code Conventions

- Python 3.10 or higher
- Use `python-dotenv` for all environment variables -- never hardcode credentials
- All Claude API calls must use the system prompt from `prompts/job_hunter_system.md`
- Playwright runs headless by default -- add a flag to run headed for debugging
- Keep scrapers modular -- one file per source, same return format from all of them
- County of San Diego and City of San Diego both use the governmentjobs.com platform.
  Their job search pages support URL query parameters for filtering by keyword and
  category -- use these instead of Playwright where possible to reduce fragility.
  County: https://www.governmentjobs.com/careers/sdcounty
  City:   https://www.governmentjobs.com/careers/sandiego
- CalCareers (https://calcareers.ca.gov) is the California state jobs portal. Filter
  strictly to keyword "Analyst II" and location "San Diego" only. Do not expand the
  search to other titles or locations -- Osvaldo has prior state government experience
  (AGPA level) and these roles are a strong fit but only when location-matched.
- Every scraper returns a list of dicts with these keys at minimum:
  `title`, `company`, `location`, `description`, `url`, `source`, `date_scraped`
- Deduplication is by URL -- if the same URL appears from multiple scrapers, keep one
- Log everything to `logs/` with timestamps -- do not print-only
- All Google Sheets calls go through `integrations/sheets.py` -- do not call the Sheets
  API directly from pipeline files
- Error handling: catch and log exceptions, send ntfy notification on failure, continue
  the run -- do not let one failed scraper kill the whole job

---

## What Is Already Built (update this as modules are completed)

- [ ] Cron trigger
- [ ] Indeed scraper
- [ ] LinkedIn scraper
- [ ] Glassdoor scraper
- [ ] USAJobs scraper
- [ ] County of San Diego scraper
- [ ] City of San Diego scraper
- [ ] CalCareers scraper (Analyst II, San Diego only)
- [ ] Deduplicator
- [ ] Scorer (Claude API)
- [ ] Resume bullet generator
- [ ] Cover letter generator
- [ ] Playwright auto-apply
- [ ] Google Sheets logger
- [ ] ntfy.sh notifications
- [ ] Error handling and retry
- [ ] Weekly summary report

Update the checkboxes as each module is completed.

---

## Sensitive Files -- Never Commit

```
.env
logs/
any file containing API keys, sheet IDs, or login credentials
```

Make sure `.gitignore` covers all of the above.

---

## How to Start a Session

At the start of every Claude Code session in this project:

1. Read this file (CLAUDE.md)
2. Read `prompts/job_hunter_system.md`
3. Check the checklist above to know what is built and what is not
4. Ask Osvaldo what he wants to work on if it is not already clear

Do not make assumptions about what is or is not implemented. Check the actual files first.
