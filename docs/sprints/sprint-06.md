# Sprint 06 — Local 8am Morning Digest Email

## Goal
Send a Pacific-time 8am email with the top 10 newly scraped, tech-industry,
≥ 7/10 jobs from the morning pipeline run. Runs on the existing local
APScheduler — no deployment, no remote trigger, no Apply button in the
email. The user reviews and batch-applies from the local dashboard.

## Context
- "Top 10" = score ≥ 7, `industry == 'tech'`, scored during today's pipeline
  run, ordered by score desc, limit 10.
- Email rows must include title, company, score, match %, salary, location,
  1–3 score reasons, and a "View Posting" link. **No Apply button** — the
  user batch-applies from the dashboard via the Sprint 05 "Auto-Apply
  Selected" flow.
- Runs from the existing APScheduler in `src/scheduler.py`. Requires the
  user's laptop to be on at 8am (acceptable trade-off — keeps this free).
- Gmail SMTP is already wired up in `src/notifier.py` via `_send()`. Reuse it.
- Pacific timezone for scheduling (San Diego / America/Los_Angeles).
- No Fly.io. No Docker changes. No new env vars beyond a `DIGEST_ENABLED`
  on/off flag.

## Architecture Notes

### New-today query
- Uses `scored_at` (set whenever `set_score` is called) to filter jobs that
  were scored during the current Pacific calendar day. Confirm the column
  exists; add it via `ALTER TABLE` in `init_db()` if missing.
- Filters: `industry = 'tech'` AND `score >= 7` AND `scored_at >= start_of_day_pt`.
  Sort by `score DESC, scored_at DESC`. Limit 10.
- Rejected alternative: pulling the full pending_review queue. User
  explicitly wants *newly scraped today*, so the user can see what's fresh
  without scrolling through backlog.

### Digest hook placement
- `run_pipeline()` in `src/scheduler.py` already has a natural "after
  scoring, before daily summary" slot. The digest goes there, guarded by
  `config.DIGEST_ENABLED`. Rejected alternative: a separate 08:05 cron job
  — adds a second scheduled run and a race window with the 08:00 pipeline.

### Timezone
- Current `BackgroundScheduler()` uses system local time. On the user's
  macOS laptop that is already Pacific, so behavior doesn't change. We'll
  still pass `timezone='America/Los_Angeles'` explicitly so the schedule
  stays correct if the system TZ ever changes (e.g. travel).

### Existing schedule
- `config.SCHEDULE_HOURS` currently drives pipeline runs. We'll add 8 to
  the list (if not already present) so the 8am run is a normal pipeline
  run, not a separate job. No new cron entries needed — the digest is
  appended to the existing pipeline flow.

## Tickets

### Ticket 06-01: `notify_morning_digest(jobs)` in notifier
**Type:** Feature
**Files in scope:** `src/notifier.py`
**Description:** New function that renders up to 10 job cards in one email.
Each card shows title, company, score, match %, salary, location, 1–3 score
reasons, and a **"View Posting"** link. No Apply button. Header and footer
mirror the tone of `notify_daily_summary`.
**Acceptance Criteria:**
- [ ] Function signature: `notify_morning_digest(jobs: list[dict]) -> None`
- [ ] Renders one row per job up to 10 (fewer if the list is shorter)
- [ ] Each row shows title, company, score, match %, salary, location,
  reasons (bulleted), and a View Posting link
- [ ] Salary formats as `$X – $Y`, `$X+`, or `Not listed` (same helper
  shape used in `notify_pending_review`)
- [ ] Subject line: `[Job Hunter] Top {N} matches today`
**Edge Cases:**
- Zero jobs passed → send a "No new matches today" email rather than
  crashing or skipping silently
- Match score computation raises → show "—" in that row, do not drop the
  row or the whole email

### Ticket 06-02: `get_todays_top_matches(limit=10)` in database
**Type:** Feature
**Files in scope:** `src/database.py`
**Description:** New helper returning jobs where `score >= 7`,
`industry = 'tech'`, and `scored_at` falls within today's Pacific
calendar day. Sorted by score desc, scored_at desc. Limit configurable,
default 10. If the `scored_at` column doesn't exist, add it via
`ALTER TABLE` inside `init_db()` and have `set_score` populate it.
**Acceptance Criteria:**
- [ ] `get_todays_top_matches()` returns ≤ 10 jobs meeting all three filters
- [ ] Jobs scored yesterday are excluded even if `scored_at` is within the
  last 24 hours
- [ ] `scored_at` column exists after `init_db()` (new column on first run,
  no-op on subsequent runs)
- [ ] Jobs where `industry` is NULL are excluded (strict tech filter, not
  a default-to-tech fallback)
**Edge Cases:**
- Zero matching jobs today → return empty list (not None)
- Pacific midnight rollover mid-run → uses `datetime.now(ZoneInfo("America/Los_Angeles"))`
  once at the start of the query, not per-row

### Ticket 06-03: Wire digest into `run_pipeline` + explicit Pacific TZ
**Type:** Feature
**Files in scope:** `src/scheduler.py`, `config.py`, `.env.example`
**Description:** Extend `run_pipeline()` to call
`notify_morning_digest(get_todays_top_matches())` after the existing
per-job notify loop, guarded by `config.DIGEST_ENABLED` (default `True`).
Add `DIGEST_ENABLED = os.getenv("DIGEST_ENABLED", "true").lower() == "true"`
to `config.py`. Pass `timezone='America/Los_Angeles'` to
`BackgroundScheduler(...)`. Ensure `8` is in `config.SCHEDULE_HOURS` so the
8am Mon–Fri run exists.
**Acceptance Criteria:**
- [ ] `run_pipeline` sends the digest after per-job notifications and
  before `notify_daily_summary`
- [ ] `DIGEST_ENABLED=false` → digest is skipped, daily summary still sent
- [ ] APScheduler instance is created with `timezone='America/Los_Angeles'`
- [ ] 8am is in `SCHEDULE_HOURS` (add if missing; do not remove existing
  times)
- [ ] `.env.example` documents `DIGEST_ENABLED`
**Edge Cases:**
- Digest call raises (e.g. SMTP down) → caught, logged, does NOT abort the
  pipeline run
- `SCHEDULE_HOURS` already contains 8 → no duplicate cron entry

## Out of Scope (future sprints)
- Remote apply button in email (requires hosted backend — deferred)
- Fly.io deployment (deferred — user wants $0 cost and manual app runs)
- Automated local scheduler startup at login (macOS launchd agent)
