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


def _format_reasons(job: dict) -> str:
    import json
    raw = job.get("score_reasons", "[]")
    try:
        reasons = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        reasons = []
    return "".join(f"<li>{r}</li>" for r in reasons)
