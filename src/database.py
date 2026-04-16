"""SQLite database operations for the job hunter."""
import re
import sqlite3
import json
from datetime import datetime
from pathlib import Path
import config


def get_conn() -> sqlite3.Connection:
    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    # Main schema
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id           TEXT UNIQUE,
            title            TEXT,
            company          TEXT,
            location         TEXT,
            city             TEXT,
            state            TEXT,
            work_type        TEXT,   -- 'Remote' | 'Hybrid' | 'On-site'
            job_type         TEXT,
            salary_min       INTEGER,
            salary_max       INTEGER,
            description      TEXT,
            apply_url        TEXT,
            source           TEXT,
            date_posted      TEXT,
            date_found       TEXT,

            -- Scoring
            score            REAL,
            score_reasons    TEXT,   -- JSON list of reason strings

            -- Workflow status
            -- 'found' | 'scored' | 'pending_review' | 'approved' | 'rejected'
            -- | 'applied' | 'apply_failed' | 'skipped'
            status           TEXT DEFAULT 'found',

            -- Documents
            resume_path      TEXT,
            cover_letter_path TEXT,

            -- Application record
            applied_at       TEXT,
            error_message    TEXT
        );

    """)
    # Add new columns to existing DBs — each ALTER is tried individually
    # so a pre-existing column on one doesn't abort the others
    for col in [
        "ALTER TABLE jobs ADD COLUMN city      TEXT",
        "ALTER TABLE jobs ADD COLUMN state     TEXT",
        "ALTER TABLE jobs ADD COLUMN work_type TEXT",
        "ALTER TABLE jobs ADD COLUMN role_type TEXT NOT NULL DEFAULT 'analyst'",
        "ALTER TABLE jobs ADD COLUMN industry  TEXT",
        "ALTER TABLE jobs ADD COLUMN scored_at TEXT",
    ]:
        try:
            conn.execute(col)
        except Exception:
            pass
    # Backfill city/state/work_type for any rows that have a location but NULL fields
    _backfill_location_columns(conn)
    _backfill_role_type(conn)

    conn.commit()
    conn.close()


ANALYST_SUBSTRINGS = ("analyst", "analytics", "business intelligence", "reporting")
ANALYST_WORDS = {"bi", "data"}
PM_SUBSTRINGS = ("program manager", "project manager", "technical program manager")
PM_WORDS = {"tpm"}


def detect_role_type(title: str) -> str:
    """Classify a job title as 'analyst' or 'pm'. Analyst wins ties."""
    if not title:
        return "analyst"
    lower = title.lower()
    words = set(re.findall(r"[a-z]+", lower))
    if any(kw in lower for kw in ANALYST_SUBSTRINGS) or (words & ANALYST_WORDS):
        return "analyst"
    if any(kw in lower for kw in PM_SUBSTRINGS) or (words & PM_WORDS):
        return "pm"
    return "analyst"


def _backfill_role_type(conn):
    """Set role_type to the detected value on any row where it's missing or stale."""
    rows = conn.execute("SELECT job_id, title, role_type FROM jobs").fetchall()
    for row in rows:
        detected = detect_role_type(row["title"] or "")
        if row["role_type"] != detected:
            conn.execute(
                "UPDATE jobs SET role_type = ? WHERE job_id = ?",
                (detected, row["job_id"]),
            )


def _backfill_location_columns(conn):
    """Parse city/state/work_type from location string for rows missing these fields."""
    from src.scraper import _parse_location

    rows = conn.execute(
        "SELECT job_id, location, title, description FROM jobs "
        "WHERE city IS NULL OR city = ''"
    ).fetchall()

    for row in rows:
        location = row["location"] or ""
        city, state = _parse_location(location)
        combined = (location + " " + (row["title"] or "") + " " + (row["description"] or "")[:300]).lower()
        if "hybrid" in combined:
            work_type = "Hybrid"
        elif "remote" in location.lower():
            work_type = "Remote"
        else:
            work_type = "On-site"

        conn.execute(
            "UPDATE jobs SET city=?, state=?, work_type=? WHERE job_id=?",
            (city, state, work_type, row["job_id"])
        )


# ── Write ────────────────────────────────────────────────────────────────────

def upsert_job(job: dict) -> bool:
    """Insert a new job; skip if already exists. Returns True if inserted."""
    job = {**job, "role_type": detect_role_type(job.get("title", ""))}
    conn = get_conn()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO jobs
                (job_id, title, company, location, city, state, work_type, job_type,
                 salary_min, salary_max, description, apply_url,
                 source, date_posted, date_found, role_type, status)
            VALUES
                (:job_id, :title, :company, :location, :city, :state, :work_type, :job_type,
                 :salary_min, :salary_max, :description, :apply_url,
                 :source, :date_posted, :date_found, :role_type, 'found')
        """, job)
        inserted = conn.execute("SELECT changes()").fetchone()[0] > 0
        conn.commit()
        return inserted
    finally:
        conn.close()


def set_score(job_id: str, score: float, reasons: list[str], industry: str = None):
    conn = get_conn()
    status = "pending_review" if score >= config.AUTO_APPLY_THRESHOLD else "scored"
    conn.execute("""
        UPDATE jobs
        SET score = ?, score_reasons = ?, status = ?,
            industry = COALESCE(?, industry),
            scored_at = ?
        WHERE job_id = ?
    """, (score, json.dumps(reasons), status, industry,
          datetime.now().isoformat(), job_id))
    conn.commit()
    conn.close()


def set_documents(job_id: str, resume_path: str, cover_letter_path: str):
    conn = get_conn()
    conn.execute("""
        UPDATE jobs SET resume_path = ?, cover_letter_path = ? WHERE job_id = ?
    """, (resume_path, cover_letter_path, job_id))
    conn.commit()
    conn.close()


def set_status(job_id: str, status: str, error: str = None):
    conn = get_conn()
    updates = {"status": status, "job_id": job_id}
    if status == "applied":
        updates["applied_at"] = datetime.now().isoformat()
    if error:
        updates["error_message"] = error
    conn.execute("""
        UPDATE jobs
        SET status = :status,
            applied_at = COALESCE(:applied_at, applied_at),
            error_message = COALESCE(:error_message, error_message)
        WHERE job_id = :job_id
    """, {
        "status": status,
        "applied_at": updates.get("applied_at"),
        "error_message": error,
        "job_id": job_id,
    })
    conn.commit()
    conn.close()


# ── Read ─────────────────────────────────────────────────────────────────────

def get_jobs(status: str = None) -> list[dict]:
    conn = get_conn()
    if status:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE status = ? ORDER BY date_found DESC", (status,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY date_found DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_job(job_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_pending_review() -> list[dict]:
    return get_jobs("pending_review")


def get_todays_top_matches(limit: int = 10) -> list[dict]:
    """Return tech jobs scored ≥ 7 during today's Pacific calendar day."""
    from zoneinfo import ZoneInfo
    pt_now = datetime.now(ZoneInfo("America/Los_Angeles")).replace(tzinfo=None)
    start_of_day_pt = pt_now.replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff = start_of_day_pt.isoformat()
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM jobs
        WHERE score >= ?
          AND industry = 'tech'
          AND scored_at IS NOT NULL
          AND scored_at >= ?
        ORDER BY score DESC, scored_at DESC
        LIMIT ?
    """, (config.AUTO_APPLY_THRESHOLD, cutoff, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_approved() -> list[dict]:
    return get_jobs("approved")


def get_stats() -> dict:
    conn = get_conn()
    row = conn.execute("""
        SELECT
            COUNT(*)                                         AS total,
            SUM(CASE WHEN status = 'applied'  THEN 1 END)   AS applied,
            SUM(CASE WHEN status = 'pending_review' THEN 1 END) AS pending_review,
            SUM(CASE WHEN status = 'approved' THEN 1 END)   AS approved,
            SUM(CASE WHEN status = 'rejected' THEN 1 END)   AS rejected,
            SUM(CASE WHEN status = 'skipped'  THEN 1 END)   AS skipped
        FROM jobs
    """).fetchone()
    conn.close()
    return dict(row)


def get_weekly_stats() -> dict:
    """Return job counts and top applied matches for the last 7 days."""
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    conn = get_conn()
    counts = conn.execute("""
        SELECT
            COUNT(*)                                              AS total,
            SUM(CASE WHEN status = 'applied'        THEN 1 END)  AS applied,
            SUM(CASE WHEN status = 'pending_review' THEN 1 END)  AS pending_review,
            SUM(CASE WHEN status = 'rejected'       THEN 1 END)  AS rejected,
            SUM(CASE WHEN status = 'scored'         THEN 1 END)  AS scored
        FROM jobs
        WHERE date_found >= ?
    """, (cutoff,)).fetchone()

    top_applied = conn.execute("""
        SELECT title, company, score, apply_url
        FROM jobs
        WHERE status = 'applied' AND date_found >= ?
        ORDER BY score DESC
        LIMIT 10
    """, (cutoff,)).fetchall()

    conn.close()
    return {
        **dict(counts),
        "top_applied": [dict(r) for r in top_applied],
    }


def job_exists(job_id: str) -> bool:
    conn = get_conn()
    exists = conn.execute(
        "SELECT 1 FROM jobs WHERE job_id = ?", (job_id,)
    ).fetchone() is not None
    conn.close()
    return exists


def purge_foreign_jobs() -> int:
    """
    Delete non-US jobs already in the DB using the same logic as the scraper.
    Skips jobs already applied to. Returns count deleted.
    """
    from src.scraper import _is_us_job, _parse_location

    conn = get_conn()
    all_rows = conn.execute(
        "SELECT job_id, location, description, apply_url "
        "FROM jobs WHERE status NOT IN ('applied')"
    ).fetchall()

    to_delete = []
    for row in all_rows:
        row_dict = dict(row)
        city, state = _parse_location(row_dict.get("location") or "")
        if not _is_us_job(row_dict, city, state):
            to_delete.append(row_dict["job_id"])

    if to_delete:
        conn.executemany(
            "DELETE FROM jobs WHERE job_id = ?",
            [(jid,) for jid in to_delete]
        )
        conn.commit()

    conn.close()
    return len(to_delete)
