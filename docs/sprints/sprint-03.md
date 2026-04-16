# Sprint 03 — Reference-Driven Resume & Cover Letter Generation

## Goal
Make every generated resume and cover letter faithfully match the format and content
of the reference documents in `assets/`, route the correct master by role type
(Analyst vs Program Manager), and show a "your original resume already matches" banner
when tailoring is unnecessary.

## Context
- User maintains four hand-crafted reference docs in `assets/`:
  - `Osvaldo Ruiz Resume Analyst.docx` / `.pdf`
  - `Osvaldo Ruiz Resume Program Manager.docx` / `.pdf`
  - `Osvaldo Ruiz Cover Letter Analyst.docx` / `.pdf`
  - `Osvaldo Ruiz Program Manager Cover Letter.docx` / `.pdf`
- The current single `base_resume.json` did not preserve the original format —
  specifically title/date alignment on role and project headers.
- User wants bullet rewriting in place (same sections, same projects), but the LLM
  may add **new** bullets as long as they follow the existing resume rules.
- Cover letters can be rewritten more freely; goal is tone/format fidelity,
  not strict paragraph-count preservation.
- Role routing is simple regex on title, with **Analyst prioritized over PM**
  when a title is ambiguous.
- "Original would suffice" banner fires at ≥ 80% match score. Shown both before
  generation and when re-opening an already-generated job.

## Architecture Notes
- **Two masters instead of one.** Parse each reference `.docx` with `python-docx`
  into a JSON file that preserves section order, role headers (company, title,
  date), bullets, projects, and skills. Output: `assets/base_resume_analyst.json`
  and `assets/base_resume_pm.json`. The old `assets/base_resume.json` is removed.
- **Role routing at scrape time.** Add a `role_type` column (`analyst` | `pm`)
  to the jobs table, populated by `detect_role_type(title)` when a job is inserted.
  Priority rule: if title contains any analyst keyword → `analyst`, else if it
  contains a PM keyword → `pm`, else default to `analyst`.
- **Renderer fix.** `_job_header` and `_proj_header` in `src/resume_builder.py`
  already use a two-column Table for title/date, but the user reports alignment
  drift. Sprint 03 verifies zero LEFTPADDING/RIGHTPADDING on the outer Table,
  `leftIndent=0` on the title paragraph, and `alignment=TA_RIGHT` with
  `rightIndent=0` on the date paragraph, against a pixel-compare to the reference
  PDF.
- **"Do not skim" rule in the system prompt.** New rule added:
  *"When rewriting bullets for a specific job, keep every bullet from the
  reference master. You may adjust wording for ATS keywords and you may add new
  bullets if the job clearly calls for them, but you may not drop or summarize
  existing bullets."*
- **Banner logic.** `_needs_tailoring(job)` already returns `(tailoring_needed,
  match_score, gaps)`. When `match_score >= 80`, the Review Queue shows a
  dismissable banner above the Generate/Regenerate controls with a "Generate
  anyway" override button.
- **Alternative considered:** re-parsing `.docx` at every generation instead of
  caching JSON masters. Rejected — `.docx` parsing is a one-time structural
  operation and the JSON form is easier to diff, test, and hand-edit.
- **Alternative considered:** running the role-type classifier via LLM.
  Rejected — title regex is deterministic, free, and user confirmed analyst
  priority is a simple rule.

## Tickets

### Ticket 03-01: Parse reference `.docx` files into two JSON masters
**Type:** Feature
**Files in scope:** `scripts/build_masters.py` (new), `assets/base_resume_analyst.json` (new), `assets/base_resume_pm.json` (new), `assets/base_resume.json` (remove)
**Description:** Write a one-shot script that uses `python-docx` to read each
reference resume `.docx` and emit a JSON master with this schema:
```json
{
  "role_type": "analyst" | "pm",
  "contact": { "name", "email", "phone", "linkedin", "location" },
  "summary": "…",
  "skills": [ { "category": "…", "items": ["…", "…"] } ],
  "experience": [
    { "company", "title", "location", "start_date", "end_date", "bullets": ["…"] }
  ],
  "projects": [
    { "name", "date", "bullets": ["…"] }
  ],
  "education": [ { "school", "degree", "graduation_date" } ]
}
```
Run the script once, commit the two JSON files, delete old `base_resume.json`.
**Acceptance Criteria:**
- [ ] `python-docx` added to `requirements.txt`
- [ ] Both JSON files exist under `assets/` and match the reference `.docx`
  section-for-section and bullet-for-bullet
- [ ] Old `base_resume.json` removed and no code references it
- [ ] Script is idempotent — re-running produces identical JSON
**Edge Cases:**
- Bullet contains a bullet glyph (•, ○) → strip the glyph, keep the text
- Date like "Jan 2023 – Present" preserved verbatim, no parsing into datetime
- Nested sub-bullets (if any) flattened into the parent bullet list

### Ticket 03-02: Add `role_type` column + detection at scrape time
**Type:** Feature
**Files in scope:** `src/database.py`, `src/scraper.py`, `scrapers/` (if the gov scrapers insert jobs independently)
**Description:** Add a `role_type TEXT NOT NULL DEFAULT 'analyst'` column to
the jobs table via a lightweight migration. Add
`detect_role_type(title: str) -> str` in `src/database.py` with this rule:
```
ANALYST_KW = {"analyst", "analytics", "bi", "business intelligence", "data", "reporting"}
PM_KW      = {"program manager", "project manager", "technical program manager", "tpm"}

title_lower = title.lower()
if any(kw in title_lower for kw in ANALYST_KW):  return "analyst"
if any(kw in title_lower for kw in PM_KW):       return "pm"
return "analyst"
```
Call it on every insert path (main scraper + gov scrapers).
**Acceptance Criteria:**
- [ ] SQLite schema migrated on `init_db()` for existing DB (ALTER TABLE if
  column is missing, no destructive drop)
- [ ] Every new job row has a populated `role_type`
- [ ] Existing rows backfilled once via `UPDATE jobs SET role_type = …` based
  on their title
- [ ] Unit test in `tests/test_role_type.py` covers:
  analyst-only, pm-only, both-kw (→ analyst), neither (→ analyst)
**Edge Cases:**
- Title is empty string → defaults to `analyst`
- "Senior Data Program Manager" → `analyst` (analyst kw wins)
- "Project Coordinator" → `analyst` (no kw matches)

### Ticket 03-03: Fix resume renderer title/date alignment
**Type:** Bug
**Files in scope:** `src/resume_builder.py`
**Description:** Job and project headers must render with the title flush to
the left page margin and the date flush to the right page margin, matching
the reference PDFs exactly. Audit and fix:
- Outer Table: `LEFTPADDING=0`, `RIGHTPADDING=0`, `TOPPADDING=0`, `BOTTOMPADDING=2`
- `job_title` / `proj_title` ParagraphStyle: `leftIndent=0`, `firstLineIndent=0`
- `date_right` ParagraphStyle: `alignment=TA_RIGHT`, `rightIndent=0`
- `colWidths` sum equals `AVAIL_W` exactly (no rounding gap)
**Acceptance Criteria:**
- [ ] Rendering a test resume produces a PDF where the first character of each
  role/project title sits at x = `LEFT_MARGIN`
- [ ] The last character of each date sits at x = `PAGE_W - RIGHT_MARGIN`
- [ ] Verified by opening the rendered PDF against the reference analyst PDF
  and comparing header positions by eye — the user will spot-check
**Edge Cases:**
- Title longer than 68% of `AVAIL_W` wraps cleanly inside the left cell
- Date with en-dash "Jan 2023 – Present" not split across lines

### Ticket 03-04: Load role-specific master in `build_resume` + "do not skim" bullet rewriting
**Type:** Feature
**Files in scope:** `src/resume_builder.py`
**Description:** Replace the single-master load with
`_load_master(role_type: str) -> dict` that reads the right JSON based on
`job["role_type"]`. Update `_tailor_bullets` so the LLM is instructed to:
1. Keep every original bullet — rewrite in place for ATS keywords, do not drop
2. Preserve bullet count at minimum; may return MORE bullets if it adds new
   ones that follow the existing resume rules
3. Never summarize, merge, or shorten the original list
Update the prompt to pass the reference bullets verbatim and the job description.
**Acceptance Criteria:**
- [ ] `build_resume(job)` loads the correct master for `job["role_type"]`
- [ ] Generated resume has at least as many bullets per section as the master
- [ ] Unit test `tests/test_resume_builder.py` stubs the LLM, passes a master
  with N bullets, and asserts the output has >= N bullets
- [ ] If LLM returns fewer bullets than the master, `build_resume` raises
  `ValueError("LLM dropped bullets")` — fail fast, do not silently accept
**Edge Cases:**
- LLM returns exactly N bullets → accept
- LLM returns N+2 bullets → accept
- LLM returns N-1 bullets → raise
- Empty feedback string → unchanged behavior

### Ticket 03-05: Update `prompts/job_hunter_system.md` with reference + format rules
**Type:** Chore
**Files in scope:** `prompts/job_hunter_system.md`
**Description:** Add three new rule sections to the system prompt:
1. **Reference fidelity rule:** "Your master resume is provided as JSON. You
   must rewrite bullets in place for ATS keywords. You may not drop, summarize,
   or merge bullets. You may add new bullets if the job clearly calls for them
   and they follow the resume rules below."
2. **Format rule:** "Role and project headers render with the title flush to
   the left margin and the date flush to the right margin. Do not add padding,
   tabs, or spaces to align them — the renderer handles it."
3. **Cover letter rule:** "Match the tone, length, and structure of the
   reference cover letter for the role type. You may rewrite more freely than
   resumes, but every cover letter must name the target company at least twice
   and reference one specific detail from the job description."
**Acceptance Criteria:**
- [ ] All three rules present in `prompts/job_hunter_system.md`
- [ ] Existing rules untouched
- [ ] File loads without error via `_load_system_prompt()`
**Edge Cases:**
- None (plain text edit)

### Ticket 03-06: "Original resume suffices" banner in Review Queue
**Type:** Feature
**Files in scope:** `app.py`, `src/resume_builder.py`
**Description:** Expose `_needs_tailoring(job)` as a public helper
`resume_match_score(job) -> int`. In the Review Queue tab, before the
Generate/Regenerate controls for any non-applied job, compute the match score
against the correct role-type master. If `match_score >= 80`, render a blue
`st.info` banner: *"Your original {role_type} resume already matches this job
at {score}% — tailoring may not be needed. You can still generate a tailored
version below."* Below the banner, keep the existing buttons so the user can
override.
**Acceptance Criteria:**
- [ ] Banner shows for jobs with match ≥ 80%
- [ ] Banner hidden for jobs with match < 80%
- [ ] Banner shows both pre-generation (no docs yet) and post-generation
  (already generated docs)
- [ ] Banner hidden for `applied` jobs
- [ ] Banner copy includes the actual numeric score and correct role type
**Edge Cases:**
- Match score exactly 80 → banner shows (`>=`)
- Master file missing → raise explicit error, do not silently skip banner
- `role_type` is null on legacy rows → fallback to `analyst` master for display

## Out of Scope (future sprints)
- Sprint 04: Add PM search terms, tech-only filter in scorer
- Sprint 05: Batch auto-apply checkbox UI in Review Queue
- Sprint 06: Daily 8am email + Fly.io remote-trigger endpoint
