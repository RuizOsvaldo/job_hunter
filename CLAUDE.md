# CLAUDE.md -- Job Hunter

This file is the single source of truth for Claude Code sessions on this project.
Read it fully before writing any code, creating any file, or making any plan.

---

## What This App Does

A fully automated job hunting tool built and owned by Osvaldo. It scrapes job postings
from multiple job boards and government portals, scores each one against his profile using
the Claude API, generates tailored resumes and cover letters for strong matches, auto-applies
via Playwright, and sends email notifications via Gmail. Runs on an APScheduler weekday
schedule at 8am.

---

## Owner Profile

**Name:** Osvaldo
**Location:** San Diego, CA
**Target roles:** Data Analyst, Business Analyst (also: Program Analyst, Operations Analyst,
Data Coordinator, Reporting Analyst, BI Analyst)
**Target locations:** San Diego on-site or hybrid, fully remote nationwide
**Minimum salary:** $80,000/year

**Technical stack (do not suggest tools outside this unless asked):**
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
- Cron / APScheduler

**Background:**
- Program Manager at The LEAGUE of Amazing Programmers (coding education nonprofit)
- Programs Coordinator at Border Angels (humanitarian nonprofit)
- Information Systems background, B.S. from Arizona State University (December 2024)

---

## Stack

| Layer | Tool |
|---|---|
| UI | Streamlit (4 tabs) |
| Language | Python 3.10+ |
| Primary scraper | python-jobspy (Indeed, LinkedIn, Glassdoor, ZipRecruiter, Google) |
| Government scrapers | Custom per-source (see below) |
| LLM routing | `src/llm.py` -- Claude or Groq, configured via `LLM_PROVIDER` in `.env` |
| Scoring + generation | Claude API / Groq via `prompts/job_hunter_system.md` |
| Auto-apply | Playwright (Indeed, LinkedIn, Greenhouse, Lever) |
| Notifications | Gmail SMTP via `src/notifier.py` |
| Database | SQLite at `data/jobs.db` |
| Scheduler | APScheduler (weekdays 8am) |
| Secrets | python-dotenv + `.env` (never committed) |

**Notification system is Gmail only. Do not introduce ntfy.sh or any other push
notification tool unless explicitly asked.**

---

## Directory Map

```
job-hunter/
├── CLAUDE.md                     -- This file. Read every session.
├── prompts/
│   └── job_hunter_system.md      -- Claude API system prompt (scoring + generation)
│                                    Read by Python at runtime, not by Claude Code.
├── src/
│   ├── __init__.py
│   ├── llm.py                    -- Unified LLM client (Claude or Groq)
│   ├── database.py               -- SQLite operations (upsert, score, status, stats)
│   ├── scraper.py                -- python-jobspy (Indeed, LinkedIn, Glassdoor, etc.)
│   ├── scorer.py                 -- Scores jobs via LLM using system prompt
│   ├── resume_builder.py         -- Tailored 1-page PDF resume via ReportLab + LLM
│   ├── cover_letter.py           -- Tailored cover letter PDF via ReportLab + LLM
│   ├── applicator.py             -- Playwright auto-apply (Indeed, LinkedIn, Greenhouse, Lever)
│   ├── notifier.py               -- Gmail SMTP (pending review, applied, failed, summary)
│   └── scheduler.py              -- APScheduler weekday 8am trigger
├── scrapers/                     -- Government / specialty job scrapers (custom built)
│   ├── usajobs.py                -- USAJobs REST API (api.usajobs.gov)
│   ├── county_san_diego.py       -- governmentjobs.com/careers/sdcounty
│   ├── city_san_diego.py         -- governmentjobs.com/careers/sandiego
│   └── calcareers.py             -- calcareers.ca.gov (Analyst II, San Diego only)
├── scripts/
│   └── save_cookies.py           -- One-time manual login to save Playwright cookies
├── app.py                        -- Streamlit entrypoint (4 tabs)
├── config.py                     -- Central config (search terms, thresholds, paths)
├── run.py                        -- Entry point for scheduler + UI
├── data/
│   ├── jobs.db                   -- SQLite (gitignored)
│   ├── resumes/                  -- Generated PDFs (gitignored)
│   ├── cover_letters/            -- Generated PDFs (gitignored)
│   ├── indeed_cookies.json       -- Playwright session (gitignored)
│   └── linkedin_cookies.json     -- Playwright session (gitignored)
├── assets/
│   └── base_resume.json          -- Resume source data, PII (gitignored)
├── logs/                         -- Run logs (gitignored)
├── requirements.txt
└── .env                          -- All secrets (never committed)
```

---

## Scraper Architecture -- Two Tiers

**Tier 1 -- python-jobspy (already built, `src/scraper.py`):**
Handles Indeed, LinkedIn, Glassdoor, ZipRecruiter, and Google Jobs in a single unified
call. Do not touch this unless there is a bug. Do not replace it with individual scrapers.

**Tier 2 -- Custom government scrapers (`scrapers/` folder):**
These four sources cannot be handled by python-jobspy. Each gets its own file.
All four must return the same dict format as `src/scraper.py` so they plug into the
existing pipeline without changes to `src/database.py` or `src/scorer.py`.

**Required return format from every scraper (government and jobspy alike):**

```python
{
    "job_id":      str,   # MD5 hash of title+company+url (use _make_job_id from scraper.py)
    "title":       str,
    "company":     str,
    "location":    str,   # raw location string
    "city":        str,
    "state":       str,   # 2-letter abbreviation
    "work_type":   str,   # "Remote" | "Hybrid" | "On-site"
    "job_type":    str,
    "salary_min":  int | None,
    "salary_max":  int | None,
    "description": str,   # capped at 8000 chars
    "apply_url":   str,
    "source":      str,   # "usajobs" | "county_sd" | "city_sd" | "calcareers"
    "date_posted": str,
    "date_found":  str,   # datetime.now().isoformat()
}
```

**Government scraper conventions:**
- County of San Diego: `https://www.governmentjobs.com/careers/sdcounty`
  Use URL query params for filtering -- do not use Playwright if the API supports it.
  The governmentjobs.com platform supports keyword and category filtering via query params.
- City of San Diego: `https://www.governmentjobs.com/careers/sandiego`
  Same platform as county -- same approach.
- CalCareers: `https://calcareers.ca.gov`
  Filter strictly to keyword "Analyst II" and location "San Diego" only.
  Do not expand to other titles or locations.
- USAJobs: `https://api.usajobs.gov`
  Has a documented REST API. Use it. Do not scrape the UI.
  Filter to San Diego and remote roles matching Osvaldo's target titles.

---

## Scoring System

All LLM calls use `prompts/job_hunter_system.md` as the system prompt.
This file is the source of truth for Osvaldo's candidate profile, scoring rubric,
and output format instructions. Never hardcode profile data in Python files.

**Score threshold:** Jobs scoring 7 or above go to `pending_review` status.
Jobs below 7 are stored as `scored` and skipped for application.

**How to load the system prompt:**

```python
with open("prompts/job_hunter_system.md", "r") as f:
    system_prompt = f.read()
```

All Claude and Groq calls go through `src/llm.py` -- never call the APIs directly
from scorer, resume builder, or cover letter modules.

---

## Database Status Flow

```
found
  --> scored (score < 7, no action)
  --> pending_review (score >= 7, user review needed)
        --> approved --> applied
                     --> apply_failed
        --> rejected
```

---

## LLM Provider

Configured via `LLM_PROVIDER` in `.env`:
- `claude` -- Anthropic Claude (higher quality, costs money), model: `claude-sonnet-4-6`
- `groq` -- Groq Llama 3.3 70B (free tier, 6,000 req/day)

All calls route through `src/llm.py`. Do not call either SDK directly from other modules.

---

## Auto-Apply ATS Support

`src/applicator.py` detects the ATS from the job URL and routes accordingly:
- `indeed` -- Indeed Easy Apply via Playwright + saved cookies
- `linkedin` -- LinkedIn Easy Apply via Playwright + saved cookies
- `greenhouse` -- boards.greenhouse.io form automation
- `lever` -- jobs.lever.co form automation
- `external` -- flagged for manual apply, notified via Gmail

Cookies for Indeed and LinkedIn are saved once via `scripts/save_cookies.py`.
Cookie paths: `data/indeed_cookies.json`, `data/linkedin_cookies.json`.

---

## Code Conventions

- All environment variables via `os.getenv()` and `load_dotenv()`. Never hardcode.
- All LLM calls go through `src/llm.py`. Never call Anthropic or Groq SDKs directly.
- All database operations go through `src/database.py`. Never query SQLite directly
  from other modules.
- All Gmail notifications go through `src/notifier.py`.
- Playwright runs headless by default. Headed mode is for debugging only.
- Every scraper (both tiers) uses the same return dict format.
- Deduplication is by `job_id` (MD5 hash of title + company + url) -- handled by
  `upsert_job()` in `src/database.py` via `INSERT OR IGNORE`.
- Log to `logs/` with timestamps. Do not use print-only logging in production code.
- Error handling: catch, log, and continue. One failed scraper must not kill the run.
- Tests go in `tests/`. Add or update tests when changing any scoring or scraping logic.

---

## Build Status

**Built and working -- do not rewrite unless there is a confirmed bug:**

- [x] Streamlit UI (4 tabs: Dashboard, Review Queue, All Jobs, Applied)
- [x] SQLite database (`src/database.py`)
- [x] python-jobspy scraper -- Indeed, LinkedIn, Glassdoor, ZipRecruiter, Google (`src/scraper.py`)
- [x] LLM router -- Claude and Groq (`src/llm.py`)
- [x] Scorer via Claude/Groq API (`src/scorer.py`)
- [x] Resume PDF builder via ReportLab + LLM (`src/resume_builder.py`)
- [x] Cover letter PDF builder via ReportLab + LLM (`src/cover_letter.py`)
- [x] Gmail notifier -- pending review, applied, failed, daily summary (`src/notifier.py`)
- [x] APScheduler weekday 8am trigger (`src/scheduler.py`)
- [x] Playwright auto-apply -- Indeed, LinkedIn, Greenhouse, Lever (`src/applicator.py`)
- [x] Cookie saver script (`scripts/save_cookies.py`)

**Not built yet -- next work:**

- [ ] USAJobs scraper (`scrapers/usajobs.py`)
- [ ] County of San Diego scraper (`scrapers/county_san_diego.py`)
- [ ] City of San Diego scraper (`scrapers/city_san_diego.py`)
- [ ] CalCareers scraper -- Analyst II, San Diego only (`scrapers/calcareers.py`)
- [ ] Pipeline integration -- wire government scrapers into `run_pipeline()` in `src/scheduler.py`
- [ ] Google Sheets logger
- [ ] Weekly summary report

---

## Engineering Process -- Four Phases

Every coding task in this repo follows this process. No exceptions.

---

### Phase 1: Requirements Gathering

Before writing any code or plan, ask ALL questions below in one batch.
Do not proceed to Phase 2 until all are answered.

**For any task:**
1. What is the exact behavior being added, changed, or fixed?
2. Which files are in scope?
3. What is the expected input and output?
4. What does "done" look like? What are the acceptance criteria?
5. Are there any constraints? (API rate limits, auth requirements, pagination, etc.)
6. Are there any known edge cases or failure scenarios?

**For bug fixes, also ask:**
- What exact behavior are you seeing?
- What behavior did you expect?
- When did it start? Did anything change before it broke?
- Can you share the full error message or log output?

**For new scrapers, also ask:**
- Does the source have a public API or must we scrape the UI?
- Are there pagination limits or rate limits to respect?
- What filters need to be applied (location, title, salary)?
- What happens when the source is unavailable?

---

### Phase 2: Sprint Planning

Once all questions are answered, produce a sprint file before writing any code.

**Sprint file location:** `docs/sprints/sprint-NN.md` (create `docs/sprints/` if it
does not exist)

**Sprint file format:**
```
# Sprint NN -- [Short Title]

## Goal
One sentence describing what this sprint delivers.

## Context
Brief summary of requirements gathered in Phase 1.

## Architecture Notes
Key technical decisions and why they were made.
Include at least one alternative considered and ruled out, with the reason.

## Tickets

### Ticket NN-01: [Title]
**Type:** Feature | Bug | Refactor | Chore
**Files in scope:** list the files
**Description:** What needs to be done and why.
**Acceptance Criteria:**
- [ ] Specific, verifiable condition 1
- [ ] Specific, verifiable condition 2
**Edge Cases:**
- What happens if X
- What happens if Y
```

Show the sprint plan to the user and confirm before executing.

---

### Phase 3: Execution

Execute tickets in order. Do not skip. Do not combine.

For each ticket:
1. State which ticket you are starting.
2. Write code for that ticket only.
3. Run Phase 4 verification before moving to the next.

**File placement rules:**
- New government scrapers go in `scrapers/`
- New shared utilities go in `src/`
- Tests go in `tests/`
- Sprint docs go in `docs/sprints/`

---

### Phase 4: Verification

Run this before declaring any ticket done.

**Logic audit:**
- [ ] Does the code meet every acceptance criterion in the ticket?
- [ ] Does the code handle every listed edge case?
- [ ] Are there any new edge cases that emerged during implementation?

**Code quality audit:**
- [ ] Does each function have a single responsibility?
- [ ] Are errors caught, logged, and non-fatal to the overall run?
- [ ] Are all secrets loaded from `.env` via `os.getenv()`?
- [ ] Do all LLM calls go through `src/llm.py`?
- [ ] Do all database writes go through `src/database.py`?
- [ ] Does the scraper return the correct dict format?

**Integration audit:**
- [ ] If a new scraper was added, is it wired into `run_pipeline()` in `src/scheduler.py`?
- [ ] If a new scraper was added, does `upsert_job()` handle its output without modification?
- [ ] If a database schema changed, are the migration `ALTER TABLE` statements in `init_db()`?

Only after every item passes: state "Ticket NN-XX is complete."

---

### Mid-Task Interruption Protocol

If a new requirement emerges during execution:
1. Stop immediately.
2. State: "A new requirement has emerged: [describe it]."
3. Ask the user to clarify it.
4. If in scope for current sprint, add a ticket and continue.
5. If out of scope, document as a future sprint item and continue.

---

## Anti-Patterns -- Never Do These

| Anti-Pattern | Why It Fails |
|---|---|
| Calling Anthropic or Groq SDKs directly from scorer/builder | Breaks LLM provider switching |
| Calling SQLite directly from scraper, scorer, or UI | Breaks the database abstraction |
| Returning a different dict shape from a new scraper | Breaks `upsert_job()` silently |
| Letting one scraper exception kill the whole run | One bad source stops all others |
| Adding a scraper without wiring it into `run_pipeline()` | Scraper exists but never runs |
| Hardcoding Osvaldo's profile data in Python files | Duplicates the system prompt, gets stale |
| Expanding CalCareers beyond "Analyst II" + San Diego | Wrong scope for this candidate |

---

## Resume & Cover Letter Generation Rules

These rules govern how resumes and cover letters are generated by the LLM at runtime.
They are enforced in two places: here (Claude Code guidance) and in `prompts/job_hunter_system.md`
(runtime LLM instructions). Keep both in sync if either is updated.

---

### Verified Facts -- Use Only These Numbers

These are the only approved metrics. Never invent or inflate alternatives.

**The LEAGUE of Amazing Programmers:**
- 7 staff members, 20+ volunteers
- 1,000+ students served cumulatively. Use "served," not "serving." Do not imply concurrent enrollment.
- 18% retention improvement (from restructuring curriculum + adding TAs at data structures unit)
- Osvaldo started September 2021. He was NOT at The LEAGUE during COVID. Never create timelines placing him there earlier.
- Volunteer tracking saves $1,380/month in labor (8 volunteers onboarded in January, 2 leading classes)
- Pike13 API pipeline fix: resolved duplicate instructor records inflating student counts
- Instructor review app: instructors log in monthly, email parents, tracks completion, notifies admin

**Border Angels:**
- 732 people served. Never use 2,100+ or any other figure.
- 150+ annual volunteers
- 14 shelter partners in Tijuana
- $10,000 grant secured under 48-hour deadline (14 intake forms, demographic breakdowns)
- Teradata presentation: 200+ attendees, collected 200+ pounds of food and $527 in donations
- Automated board report: 3% weekly donation increase in January; volunteer management saves $890/month
- Python ETL pipeline + BigQuery to Google Sheets for monthly board report

**Starbucks:**
- Store Manager at a $2.5M annual revenue location, 30+ employees
- Store Manager dates: November 2017 -- March 2021 (not November 2013)
- Full role progression: Barista (2013--2015), Supervisor (2015--2017), Store Manager (November 2017--March 2021)
- 230% customer satisfaction improvement (score went from 27 to 62 out of 100)
- 14% profit increase
- Manager of the Quarter (FY20/Q1), San Diego Barista Champion (2017), Coffee Master
- Analyzed P&L and weekly reports. Used internal Starbucks software -- did NOT build or develop systems.
- Advanced Development Program participant. Trained ASMs and Shift Supervisors.

**Portfolio Projects (use only these, with these exact metrics):**
- IBM HR Attrition Dashboard (Tableau): 1,470 employees; overtime workers leave at 3x rate; 40% attrition among Sales Reps; 35% turnover in first-year employees
- Economic Indicators Dashboard (Python + PostgreSQL): 13 FRED indicators, 10+ years historical data, window functions for YoY/rolling averages, yield curve recession detection
- Google Analytics E-Commerce Dashboard (BigQuery + Google Sheets): 903,653 sessions, $1.54M revenue, 4 pivot tables, 5 slicers, desktop users generate 95.6% of revenue

---

### Resume Rules

**Format:**
- One page maximum. Enforced via `KeepInFrame(mode='shrink')` in `resume_builder.py`.
- Single-column layout. ATS-friendly: standard fonts, no graphics, no text boxes.
- Section order: Contact Info, Summary, Technical Skills, Professional Experience, Relevant Projects (data analyst roles only), Education.
- No overlapping text anywhere in the document. Every `ParagraphStyle` must set `leading` explicitly to at least `fontSize + 2`. Do not rely on ReportLab's default leading.
- Name header: `fontSize=14`, `leading=17`, `spaceAfter=3`. Do not increase the name font size -- it previously caused the name to overlap the contact line below it.
- Do not change any body font sizes (bullets=8, section headers=9, job_title=9, summary=8.5). Use `KeepInFrame(mode='shrink')` for overflow, not font size reduction.

**Summary:**
- "9+ years" attaches to leadership and program management -- not to Python/SQL/tools.
- Python, SQL, and data visualization are complementary strengths, not the primary 9-year focus.
- Tailor to role type (see below).

**Bullets:**
- Lead with result or impact, then describe the action and tools.
- Every bullet must be defensible in an interview -- if Osvaldo cannot speak to it, do not include it.
- No repeated numbers or examples within the same document.
- No consecutive bullets starting with the same verb.
- Structure: `[Action verb] + [what was done] + [tool or method] + [measurable result]`
- Under 120 characters each.
- Do not use em dashes.

**Tailoring by role type:**

*Data Analyst / State Analyst:*
- Technical Skills leads with data tools (Python, SQL, Excel, Tableau, BigQuery).
- Include Relevant Projects section.
- LEAGUE bullets: data pipelines, retention analysis, reporting automation.
- Border Angels bullets: ETL pipeline, automated dashboards, KPI tracking.
- Starbucks bullets: analyzing business reports, using P&L data, driving decisions from reporting.

*Program Manager:*
- Summary leads with program lifecycle management, stakeholder communication, execution.
- Technical Skills leads with PM-relevant tools; data/programming tools in supporting row.
- Drop Relevant Projects section entirely. Use that space for stronger work experience bullets.
- LEAGUE bullets: managing operations for 1,000+ students, overseeing staff and volunteers, curriculum oversight.
- Border Angels bullets: program development, metrics collection, board-level reporting, grant management.
- Starbucks bullets: Advanced Development Program, P&L ownership, training ASMs and supervisors.

*State Government (CalCareers):*
- Blend of both framings. Program operations is a strength, not a weakness.
- Emphasize compliance, eligibility tracking, reporting to funders, cross-functional coordination.
- Match keywords from the specific duty statement.

---

### Cover Letter Rules

**Format:**
- One page maximum. Include: name, phone, email, date, recipient, Re: line with position title.
- 3--4 body paragraphs. Conversational but professional tone. Close with "Sincerely," and full name.
- Do not use em dashes.

**Structure:**
- Para 1: Why this role, why this organization. Specific to the JD, not generic.
- Para 2: Strongest experience match with specific metrics from verified examples.
- Para 3: Second angle of fit (technical skills, cross-sector experience, or complementary strength).
- Para 4: Brief close. No filler.

**Tone:**
- Conversational and direct. Not overly formal, not casual.
- Do not use: "I am confident that," "I believe I would be a great fit," "I am excited to apply."
- Show, don't tell. Trim aggressively -- if a sentence adds no new information, cut it.
- Mirror 2--3 keywords or phrases from the JD naturally.

---

### Generation Anti-Patterns

- Never inflate Border Angels numbers beyond 732.
- Never place Osvaldo at The LEAGUE before September 2021.
- Never attribute system-building or development work to Starbucks -- analysis and tool usage only.
- Never use the Store Manager start date as November 2013 -- it is November 2017.
- Never repeat the same metric or example twice within a single document.
- Never use em dashes in any document.
- Never include a claim Osvaldo cannot defend in an interview.
- Never use a one-size-fits-all resume -- always tailor to role type.
- Never pad cover letters with generic enthusiasm.


---

## Environment Setup

```bash
# Install deps
pip install -r requirements.txt
playwright install chromium

# Save cookies (one time per platform)
python scripts/save_cookies.py indeed
python scripts/save_cookies.py linkedin

# Run UI only
streamlit run app.py

# Run scheduler + UI
python run.py

# Test pipeline immediately
python run.py --now
```

**Required `.env` keys:**
```
ANTHROPIC_API_KEY=
LLM_PROVIDER=claude          # or groq
GROQ_API_KEY=                # if using groq
GMAIL_ADDRESS=
GMAIL_APP_PASSWORD=
NOTIFY_EMAIL=
INDEED_EMAIL=
INDEED_PASSWORD=
LINKEDIN_EMAIL=
LINKEDIN_PASSWORD=
USAJOBS_API_KEY=             # register at developer.usajobs.gov (free)
```
