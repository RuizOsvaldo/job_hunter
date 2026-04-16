"""Gmail SMTP notifications for job events."""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
import config


def _send(subject: str, html_body: str, attachments: list[str] = None):
    """Send an email via Gmail SMTP with optional PDF attachments."""
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = config.GMAIL_ADDRESS
    msg["To"] = config.NOTIFY_EMAIL

    msg.attach(MIMEText(html_body, "html"))

    for path in (attachments or []):
        p = Path(path)
        if p.exists():
            with open(p, "rb") as f:
                part = MIMEApplication(f.read(), _subtype="pdf")
                part.add_header("Content-Disposition", "attachment", filename=p.name)
                msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
        server.send_message(msg)


# ── Public notification functions ─────────────────────────────────────────────

def notify_pending_review(job: dict):
    """Alert: high-scoring job needs your review before applying."""
    score = job.get("score", "?")
    title = job.get("title", "")
    company = job.get("company", "")
    location = job.get("location", "")
    apply_url = job.get("apply_url", "#")
    reasons = _format_reasons(job)

    subject = f"[Job Hunter] Review needed — {title} @ {company} (Score: {score}/10)"
    html = f"""
<h2 style="color:#0f3460;">High-Match Job Found — Your Review Needed</h2>
<p><b>Role:</b> {title}<br>
<b>Company:</b> {company}<br>
<b>Location:</b> {location}<br>
<b>Score:</b> {score}/10</p>
<h3>Why it matched:</h3>
<ul>{reasons}</ul>
<p><a href="{apply_url}" style="color:#0f3460;">View Job Posting</a></p>
<p style="color:#888;">Open the Job Hunter dashboard to approve and submit your application.</p>
"""
    _send(subject, html)


def notify_applied(job: dict, resume_path: str = None, cover_letter_path: str = None):
    """Confirmation: application submitted successfully."""
    score = job.get("score", "?")
    title = job.get("title", "")
    company = job.get("company", "")
    location = job.get("location", "")
    apply_url = job.get("apply_url", "#")
    reasons = _format_reasons(job)

    subject = f"[Job Hunter] Applied — {title} @ {company}"
    html = f"""
<h2 style="color:#0f3460;">Application Submitted</h2>
<p><b>Role:</b> {title}<br>
<b>Company:</b> {company}<br>
<b>Location:</b> {location}<br>
<b>Score:</b> {score}/10</p>
<h3>Why it matched:</h3>
<ul>{reasons}</ul>
<p><a href="{apply_url}" style="color:#0f3460;">View Original Posting</a></p>
<p style="color:#888;">Resume and cover letter attached below.</p>
"""
    attachments = [p for p in [resume_path, cover_letter_path] if p]
    _send(subject, html, attachments=attachments)


def notify_apply_failed(job: dict, error: str):
    """Alert: auto-apply failed, needs manual follow-up."""
    title = job.get("title", "")
    company = job.get("company", "")
    apply_url = job.get("apply_url", "#")

    subject = f"[Job Hunter] Apply FAILED — {title} @ {company}"
    html = f"""
<h2 style="color:#c0392b;">Auto-Apply Failed — Manual Action Needed</h2>
<p><b>Role:</b> {title}<br>
<b>Company:</b> {company}<br>
<b>Error:</b> {error}</p>
<p><a href="{apply_url}" style="color:#0f3460;">Apply Manually Here</a></p>
"""
    _send(subject, html)


def notify_daily_summary(stats: dict, new_jobs: int):
    """Daily digest with run stats."""
    subject = f"[Job Hunter] Daily Summary — {new_jobs} new jobs found"
    html = f"""
<h2 style="color:#0f3460;">Daily Job Hunt Summary</h2>
<table style="border-collapse:collapse;">
<tr><td style="padding:4px 12px 4px 0;"><b>New jobs found</b></td><td>{new_jobs}</td></tr>
<tr><td style="padding:4px 12px 4px 0;"><b>Pending your review</b></td><td>{stats.get('pending_review', 0)}</td></tr>
<tr><td style="padding:4px 12px 4px 0;"><b>Applied (total)</b></td><td>{stats.get('applied', 0)}</td></tr>
<tr><td style="padding:4px 12px 4px 0;"><b>Skipped / rejected</b></td><td>{(stats.get('skipped', 0) or 0) + (stats.get('rejected', 0) or 0)}</td></tr>
<tr><td style="padding:4px 12px 4px 0;"><b>Total tracked</b></td><td>{stats.get('total', 0)}</td></tr>
</table>
<p style="color:#888;">Open the Job Hunter dashboard to review pending applications.</p>
"""
    _send(subject, html)


def _format_salary(job: dict) -> str:
    lo, hi = job.get("salary_min"), job.get("salary_max")
    if lo and hi:
        return f"${lo:,} – ${hi:,}"
    if lo:
        return f"${lo:,}+"
    return "Not listed"


def _match_pct(job: dict) -> str:
    from src.resume_builder import resume_match_score
    try:
        return f"{resume_match_score(job)}%"
    except Exception:
        return "—"


def notify_morning_digest(jobs: list[dict]) -> None:
    """Send the 8am digest with up to 10 new high-scoring tech matches."""
    if not jobs:
        subject = "[Job Hunter] No new matches today"
        html = """
<h2 style="color:#0f3460;">No new matches today</h2>
<p>The morning pipeline ran and found no new tech jobs scoring 7 or higher.</p>
<p style="color:#888;">Check back tomorrow, or run the pipeline manually from the dashboard.</p>
"""
        _send(subject, html)
        return

    rows = []
    for j in jobs[:10]:
        title = j.get("title", "")
        company = j.get("company", "")
        score = j.get("score", "?")
        match = _match_pct(j)
        salary = _format_salary(j)
        location = j.get("location", "") or "—"
        apply_url = j.get("apply_url", "#")
        reasons = _format_reasons(j)
        rows.append(f"""
<div style="border:1px solid #e1e4e8;border-radius:8px;padding:14px 18px;margin-bottom:14px;">
  <h3 style="margin:0 0 6px 0;color:#0f3460;">{title}</h3>
  <p style="margin:0 0 8px 0;color:#444;">
    <b>{company}</b> &nbsp;·&nbsp; {location}
  </p>
  <p style="margin:0 0 8px 0;">
    <b>Score:</b> {score}/10 &nbsp;·&nbsp;
    <b>Match:</b> {match} &nbsp;·&nbsp;
    <b>Salary:</b> {salary}
  </p>
  <ul style="margin:6px 0 10px 18px;padding:0;">{reasons}</ul>
  <p style="margin:0;"><a href="{apply_url}" style="color:#0f3460;">View Posting ↗</a></p>
</div>""")

    subject = f"[Job Hunter] Top {len(jobs[:10])} matches today"
    html = f"""
<h2 style="color:#0f3460;">Top {len(jobs[:10])} matches from this morning's run</h2>
<p style="color:#555;">Tech-industry jobs scored 7+ that were freshly scraped today. Open the Job Hunter dashboard to review and batch-apply.</p>
{''.join(rows)}
<p style="color:#888;margin-top:18px;">Use the Review Queue's "Auto-Apply Selected" to apply in bulk.</p>
"""
    _send(subject, html)


def notify_weekly_summary(stats: dict):
    """Weekly digest with 7-day counts and top applied matches. Sent every Sunday 10am."""
    applied = stats.get("applied") or 0
    total = stats.get("total") or 0
    pending = stats.get("pending_review") or 0
    rejected = stats.get("rejected") or 0
    scored = stats.get("scored") or 0
    top_applied = stats.get("top_applied") or []

    if top_applied:
        rows = "".join(
            f"<tr>"
            f"<td style='padding:3px 10px 3px 0'>{j['title']}</td>"
            f"<td style='padding:3px 10px 3px 0'>{j['company']}</td>"
            f"<td style='padding:3px 10px 3px 0'>{j.get('score', '?')}/10</td>"
            f"<td style='padding:3px 10px 3px 0'><a href='{j['apply_url']}'>View</a></td>"
            f"</tr>"
            for j in top_applied
        )
        matches_html = f"""
<h3>Top Applied Matches</h3>
<table style="border-collapse:collapse;">
<tr>
  <th style="text-align:left;padding:3px 10px 3px 0;">Role</th>
  <th style="text-align:left;padding:3px 10px 3px 0;">Company</th>
  <th style="text-align:left;padding:3px 10px 3px 0;">Score</th>
  <th style="text-align:left;padding:3px 10px 3px 0;">Link</th>
</tr>
{rows}
</table>"""
    else:
        matches_html = "<p style='color:#888;'>No applications submitted this week.</p>"

    subject = f"[Job Hunter] Weekly Summary — {applied} applied this week"
    html = f"""
<h2 style="color:#0f3460;">Weekly Job Hunt Summary</h2>
<table style="border-collapse:collapse;">
<tr><td style="padding:4px 12px 4px 0;"><b>Jobs found this week</b></td><td>{total}</td></tr>
<tr><td style="padding:4px 12px 4px 0;"><b>Applied</b></td><td>{applied}</td></tr>
<tr><td style="padding:4px 12px 4px 0;"><b>Pending your review</b></td><td>{pending}</td></tr>
<tr><td style="padding:4px 12px 4px 0;"><b>Scored (below threshold)</b></td><td>{scored}</td></tr>
<tr><td style="padding:4px 12px 4px 0;"><b>Rejected</b></td><td>{rejected}</td></tr>
</table>
{matches_html}
<p style="color:#888;margin-top:16px;">Open the Job Hunter dashboard to review pending applications.</p>
"""
    _send(subject, html)


def _format_reasons(job: dict) -> str:
    import json
    raw = job.get("score_reasons", "[]")
    try:
        reasons = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        reasons = []
    return "".join(f"<li>{r}</li>" for r in reasons)
