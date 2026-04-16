# Sprint 04 — Search Expansion & Tech-Only Industry Filter

## Goal
Expand the job search to cover Program Manager and Project Manager roles in
addition to analyst roles, and restrict scoring to jobs at tech-industry
companies so the pipeline only surfaces roles in the user's target sector.

## Context
- User wants Program Manager and Technical Program Manager roles added to the
  search, plus "Project Manager" (explicitly allowed despite the standing
  anti-pattern against it elsewhere).
- User does NOT want "Program Manager Tech" as a search term — drop it if it
  was ever considered.
- Only jobs in the **tech** industry should reach the Review Queue. Everything
  else (healthcare, retail, government, finance-not-tech, etc.) should be
  dropped at scoring time, not at scrape time — the scraper can't cheaply tell
  what industry a company is in.
- User is OK with the existing `AUTO_APPLY_THRESHOLD = 7` score bar — no new
  stricter threshold for batch apply.
- Title-level filters (`_TITLE_KEYWORDS`, `_TITLE_BLOCKLIST`) in
  `src/scorer.py` currently block PM roles because "program manager" /
  "project manager" are not in the allowlist. Those filters must be updated
  so PM/TPM titles pass through to the LLM scoring step.

## Architecture Notes
- **Search term expansion** lives in `config.SEARCH_TERMS`. Add three new
  strings: `"Program Manager"`, `"Technical Program Manager"`, `"Project
  Manager"`. No other changes to scraper logic.
- **Industry classification** happens inside the existing LLM scoring call,
  not as a second LLM pass. The system prompt and the `score_job` user
  message will be updated so the LLM returns an additional field:
  `industry: "tech" | "non-tech"`. This is free — no extra LLM call per job.
- **Drop non-tech jobs** in `set_score`: if `industry == "non-tech"`, the job
  is marked `skipped` with a reason `"Non-tech industry"` and never reaches
  the Review Queue. Tech-classified jobs follow the existing
  `pending_review`/`scored` branch.
- **Title filter update:** `_TITLE_KEYWORDS` gains `program manager`,
  `project manager`, `technical program manager`, `tpm`. `_TITLE_BLOCKLIST`
  is unchanged — nothing in it conflicts.
- **Alternative considered:** a second LLM call dedicated to industry
  classification. Rejected — wastes quota, slows the scoring loop, and the
  scoring LLM already has the full job description loaded.
- **Alternative considered:** industry allow-list based on a hardcoded list
  of tech companies. Rejected — fragile, requires constant maintenance, and
  misses most long-tail employers.
- **Alternative considered:** filtering at scrape time. Rejected — scrapers
  don't have enough context; the LLM does a much better job after reading
  the description.

## Tickets

### Ticket 04-01: Add PM search terms to `config.SEARCH_TERMS`
**Type:** Chore
**Files in scope:** `config.py`
**Description:** Append three new search terms: `"Program Manager"`,
`"Technical Program Manager"`, `"Project Manager"`. Leave the existing
analyst terms unchanged.
**Acceptance Criteria:**
- [ ] `config.SEARCH_TERMS` contains the three new strings
- [ ] Existing analyst terms unchanged
- [ ] `"Program Manager Tech"` is NOT added
**Edge Cases:**
- None — pure config change.

### Ticket 04-02: Allow PM titles through the scorer's title filter
**Type:** Feature
**Files in scope:** `src/scorer.py`
**Description:** Add `"program manager"`, `"project manager"`, `"technical
program manager"`, `"tpm"` to `_TITLE_KEYWORDS` so those titles are not
silently dropped before reaching the LLM. Blocklist is unchanged.
**Acceptance Criteria:**
- [ ] Title "Program Manager" passes `_title_passes_filter`
- [ ] Title "Technical Program Manager" passes
- [ ] Title "Project Manager" passes
- [ ] Title "TPM III" passes
- [ ] Title "Data Entry Specialist" still blocked (no regression)
- [ ] Unit test `tests/test_title_filter.py` covers the four new titles and
  at least one regression case
**Edge Cases:**
- "Construction Project Manager" — passes title filter, gets dropped later
  at industry classification step (non-tech)
- "Senior Analyst / Project Manager" — passes on analyst keyword

### Ticket 04-03: Add `industry` field to scoring LLM output + drop non-tech
**Type:** Feature
**Files in scope:** `src/scorer.py`, `prompts/job_hunter_system.md`,
`src/database.py`
**Description:** Update the scoring user message to ask the LLM for a third
field: `industry`. Valid values are `"tech"` and `"non-tech"`. Update
`score_job` to parse it and return `(score, reasons, industry)`. In
`score_unscored_jobs`, if `industry == "non-tech"`, call
`set_status(job_id, "skipped", "Non-tech industry")` and do NOT call
`set_score`. Tech jobs go through the existing path.
Update `prompts/job_hunter_system.md` with a new "Industry Classification"
rule section explaining what counts as tech: software, SaaS, cloud, AI/ML,
fintech, edtech, healthtech, consumer internet, developer tools, hardware
tech (semiconductors, devices), cybersecurity, data platforms. Non-tech
includes: healthcare providers, retail, hospitality, construction,
traditional finance (banks, insurance without a tech product), government
agencies, manufacturing (non-tech), logistics (non-tech), education
institutions.
**Acceptance Criteria:**
- [ ] Scoring JSON now includes `"industry": "tech"` or `"non-tech"`
- [ ] `score_job` returns a 3-tuple `(score, reasons, industry)`
- [ ] Non-tech jobs marked `skipped` with error_message `"Non-tech industry"`
- [ ] Tech jobs still flow into `pending_review` / `scored` as before
- [ ] System prompt contains the new Industry Classification section
- [ ] Existing `set_score` signature unchanged (still takes score + reasons)
**Edge Cases:**
- LLM returns an unknown industry value → raise ValueError, do not silently
  accept (fail fast per repo standards)
- LLM omits the field → raise ValueError
- Healthcare-adjacent tech company (e.g. Epic, Cerner) → classified as tech
  because the product is software
- Government tech contractor (e.g. Palantir, Anduril) → classified as tech

### Ticket 04-04: Display industry on Review Queue cards
**Type:** Feature
**Files in scope:** `app.py`
**Description:** In the Review Queue tab expander header, append the
industry tag alongside the existing score/location/status labels, pulled
from the jobs row. Since non-tech jobs are skipped before they reach the
Review Queue, this will effectively always read "tech" — but displaying it
confirms the filter is active.
**Acceptance Criteria:**
- [ ] Every Review Queue row shows "Tech" after the status badge
- [ ] Rows without an industry value (legacy) show "Tech" by default
- [ ] All Jobs tab gains an `Industry` column between `Status` and `Source`
**Edge Cases:**
- Legacy jobs scored before this sprint have no `industry` column value —
  treat as tech for display purposes

### Ticket 04-05: Add `industry` column to jobs table
**Type:** Chore
**Files in scope:** `src/database.py`
**Description:** Add an `industry TEXT` column to the jobs schema via the
same `ALTER TABLE` migration pattern used for `role_type`. `set_score` gains
a new optional `industry` parameter; when provided it writes to the column.
**Acceptance Criteria:**
- [ ] Column added via ALTER TABLE on `init_db()`, backfill unnecessary
- [ ] `set_score(job_id, score, reasons, industry=None)` backward-compatible
- [ ] Scorer passes `industry` through to `set_score`
**Edge Cases:**
- Existing rows have NULL industry → treated as "tech" on display

## Out of Scope (future sprints)
- Sprint 05: Batch auto-apply checkbox UI in Review Queue
- Sprint 06: Daily 8am email + Fly.io remote-trigger endpoint
