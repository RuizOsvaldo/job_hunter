# Sprint 05 — Batch Auto-Apply in Review Queue

## Goal
Let the user select multiple jobs in the Review Queue via checkboxes and run
the auto-apply pipeline on all of them in a single action, with the option to
remove selected jobs from the queue instead of applying.

## Context
- Per-job flow confirmed in Sprint 03 Q&A:
  1. Check the role-specific master match score — if ≥ 80%, use the master
     resume as-is (skip LLM tailoring).
  2. Otherwise generate a tailored resume.
  3. Always generate a fresh cover letter tailored to the company.
  4. Submit via Easy Apply.
  5. If Easy Apply fails: mark `apply_failed`, skip, continue to the next job.
- User wants a checkbox column as the first column of the Review Queue.
  Checked rows can be acted on via:
  - "✅ Auto-Apply Selected" → runs pipeline on each checked job sequentially
  - "❌ Remove Selected" → marks checked jobs as `rejected` (removed from queue)
- No feedback prompt in batch mode (confirmed in Sprint 03 Q&A).
- The existing `apply_job(job_id)` function already handles build-docs +
  submit + status updates, so batch mode is a loop around it. No new
  pipeline code needed — only a new UI surface.
- The existing per-job expander UI stays (single-job manual review path).

## Architecture Notes
- **New: compact batch table at the top of Review Queue.** Above the existing
  expanders, render a `st.data_editor` with columns:
  `Select | Score | Title | Company | Role | Match | Industry`. Match score
  is `resume_match_score(job)` — the same helper surfaced in Sprint 03.
- **Batch action buttons** live above the table: "Auto-Apply Selected",
  "Remove Selected". Both iterate checked rows, call the right function,
  and `st.rerun()` when done.
- **Progress feedback:** for Auto-Apply Selected, show a `st.status` block
  per job with the three states (`generating`, `applying`, `done|failed`),
  so the user can see the pipeline advancing across the batch.
- **Match-gated tailoring already lives inside `build_resume`.** When the
  match score is ≥ 65% (the current `_needs_tailoring` threshold), it
  already uses the master as-is. The user's "80% = skip" target is
  satisfied by the existing code path — no change needed here. The batch
  loop just calls `apply_job(job_id)` and lets the builder decide.
- **Alternative considered:** build a parallel `batch_apply(job_ids)`
  function in `applicator.py` that builds all docs first and then submits
  them. Rejected — sequential is simpler, provides live progress, and
  failures don't block subsequent jobs.
- **Alternative considered:** re-use the existing All Jobs data_editor
  pattern. Rejected — Review Queue has score reasons and description
  previews in expanders that the flat table can't host; the batch table
  is a separate compact surface above the expanders.

## Tickets

### Ticket 05-01: Batch selection table at top of Review Queue
**Type:** Feature
**Files in scope:** `app.py`
**Description:** Above the existing expanders, render a new compact
`st.data_editor` titled "Batch Actions". Columns:
- `Select` (checkbox, editable)
- `Score` (number)
- `Title` (text)
- `Company` (text)
- `Role` (text, from `role_type` → "Analyst" or "Program Manager")
- `Match` (text, formatted `"{pct}%"` from `resume_match_score`)
- `Industry` (text, title-cased from `job.get("industry")`)

All columns except `Select` are disabled. Table source is the same `pending`
list that drives the expander loop.
**Acceptance Criteria:**
- [ ] Table shows every job currently in `pending_review` + `approved`
- [ ] Checkbox column is editable, all other columns read-only
- [ ] Match column shows integer percentage for each job
- [ ] Table collapses gracefully when the queue is empty (no error, show the
  existing "No jobs pending review" info message)
**Edge Cases:**
- Missing `role_type` on a legacy row → display "Analyst"
- Match score computation raises → display "—" for that row, do not crash
  the whole table

### Ticket 05-02: "Auto-Apply Selected" batch action
**Type:** Feature
**Files in scope:** `app.py`
**Description:** Button placed above the batch table. On click:
1. Read the edited dataframe from `st.session_state`.
2. Filter to rows where `Select == True`.
3. For each checked row, call `apply_job(job_id)` inside a
   `st.status("Applying to {title} @ {company}")` block.
4. Track success/failure counts.
5. After the loop finishes, show a `st.success` summary
   (`"Applied to X of Y jobs — Z failed and marked apply_failed"`).
6. Call `st.rerun()`.

Uses the existing `apply_job` from `src.applicator` — no new pipeline code.
Failed jobs remain in the DB with `apply_failed` status; the user reviews
them in the Applied tab as usual.
**Acceptance Criteria:**
- [ ] Button disabled when no rows are checked
- [ ] Each checked job triggers a full `apply_job` call sequentially
- [ ] Successes counted and reported; failures counted and reported
- [ ] A single job failing does NOT abort the batch — loop continues
- [ ] Summary message is accurate
- [ ] Table refreshes after the batch completes (applied jobs disappear
  from Review Queue)
**Edge Cases:**
- `apply_job` raises → caught, counted as failure, loop continues
- Zero rows checked → warning toast, no loop runs
- User navigates away mid-loop → Streamlit kills the run; partial results
  are persisted in the DB and visible on next load (acceptable)

### Ticket 05-03: "Remove Selected" batch action
**Type:** Feature
**Files in scope:** `app.py`
**Description:** Second button next to Auto-Apply Selected. On click, set
status to `rejected` on every checked row via
`set_status(job_id, "rejected")`, then `st.rerun()`.
**Acceptance Criteria:**
- [ ] Button placed next to Auto-Apply Selected
- [ ] Each checked row → `set_status(..., "rejected")`
- [ ] Summary message: `"Removed N jobs from the queue"`
- [ ] Zero rows checked → warning, no writes
**Edge Cases:**
- Database write error on one row → caught, logged, other rows still
  processed

## Out of Scope (future sprints)
- Sprint 06: Daily 8am email + Fly.io remote-trigger endpoint
