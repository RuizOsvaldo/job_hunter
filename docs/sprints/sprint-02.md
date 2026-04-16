# Sprint 02 — Document Regeneration with Feedback

## Goal
Add per-document regeneration with an optional feedback prompt to the Review Queue tab so documents can be improved after review or refreshed after prompt/app updates.

## Context
- User wanted a "Regenerate" button on reviewed roles in the Review Queue tab.
- Documents should be regeneratable individually (resume or cover letter) or together.
- An optional feedback text field lets the user guide the LLM (e.g. "make the cover letter less formal").
- Files overwrite in-place (same filename, no versioning).
- Status resets to `pending_review` if job was `approved` at time of regeneration.
- Applied jobs are left untouched — no regenerate UI shown.

## Architecture Notes
- `build_resume` and `build_cover_letter` accept `feedback: str = ""` and prepend it to every LLM user message when non-empty. Feedback also forces `tailoring_needed = True` in `build_resume`, bypassing the match-score threshold that would otherwise skip tailoring.
- `generate_documents_only` accepts `resume_feedback` and `cover_letter_feedback` and threads them to the respective builders.
- The UI uses a collapsed `st.expander` ("🔄 Regenerate Documents") so it takes zero visible space until opened. Three buttons inside: Resume, Cover Letter, Both.
- **Alternative considered:** A separate `regenerate_resume(job, feedback)` function — rejected because it would duplicate all build logic with no benefit.

## Tickets

### Ticket 02-01: Add `feedback` param to `build_resume` and `build_cover_letter`
**Type:** Feature
**Files in scope:** `src/resume_builder.py`, `src/cover_letter.py`
**Description:** Both builder functions accept `feedback: str = ""`. When non-empty, it is prepended to each LLM user message. In `build_resume`, non-empty feedback also forces `tailoring_needed = True`.
**Acceptance Criteria:**
- [x] `build_resume(job, feedback="")` backward-compatible
- [x] `build_cover_letter(job, feedback="")` backward-compatible
- [x] Feedback prepended as `"User feedback on the previous version: {feedback}\n\n"` in all LLM calls
- [x] Feedback forces tailoring on in `build_resume` regardless of match score
**Edge Cases:**
- Whitespace-only feedback → treated as empty via `.strip()`
- LLM failure with feedback present → same fallback behavior (originals returned)

### Ticket 02-02: Add `resume_feedback` / `cover_letter_feedback` params to `generate_documents_only`
**Type:** Feature
**Files in scope:** `src/applicator.py`
**Description:** Pass-through feedback params from `generate_documents_only` to each builder.
**Acceptance Criteria:**
- [x] Signature updated; existing callers with no args unaffected
- [x] `resume_feedback` passed to `build_resume`, `cover_letter_feedback` to `build_cover_letter`
**Edge Cases:**
- `job_id` not found → raises as before

### Ticket 02-03: Add regeneration UI to Review Queue tab
**Type:** Feature
**Files in scope:** `app.py`
**Description:** Collapsed expander below document previews for any job that has documents and is not `applied`. Contains an optional feedback text area and three buttons: Resume, Cover Letter, Both.
**Acceptance Criteria:**
- [x] Section hidden for `applied` jobs
- [x] Each button regenerates the correct document(s) and overwrites in-place
- [x] Status reset to `pending_review` if job was `approved`
- [x] Feedback passed to builder; empty feedback works fine
- [x] Spinner during generation, success message after
- [x] Exceptions shown via `st.error`, status unchanged on failure
**Edge Cases:**
- User leaves feedback empty → normal regeneration, no error
- LLM raises → `st.error` with message, no status change
