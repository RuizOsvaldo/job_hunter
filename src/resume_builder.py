"""Generate a tailored 1-page PDF resume using ReportLab.

Layout matches Osvaldo's original resume exactly:
- Black/white, no color accents
- Bold uppercase section headers with full-width underline
- Job title + date on same line (right-aligned date via Table)
- Circle bullet points (●)
- 1-inch margins
"""
import json
import os
import re
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.platypus.flowables import KeepInFrame
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
import config
from src.llm import call_claude

# ── Page geometry ─────────────────────────────────────────────────────────────

LEFT_MARGIN   = 1.0 * inch
RIGHT_MARGIN  = 1.0 * inch
TOP_MARGIN    = 0.75 * inch
BOTTOM_MARGIN = 0.75 * inch
PAGE_W, PAGE_H = letter
AVAIL_W = PAGE_W - LEFT_MARGIN - RIGHT_MARGIN
AVAIL_H = PAGE_H - TOP_MARGIN - BOTTOM_MARGIN


# ── Styles ────────────────────────────────────────────────────────────────────
# Every style sets leading explicitly (>= fontSize) to prevent line overlap.
# Do not change font sizes. Use KeepInFrame(mode='shrink') for overflow.

def _styles():
    base = getSampleStyleSheet()
    s = {}
    s["name"] = ParagraphStyle("name", parent=base["Normal"],
        fontSize=13, fontName="Helvetica-Bold", textColor=colors.black,
        alignment=TA_CENTER, leading=16, spaceAfter=2)
    s["contact"] = ParagraphStyle("contact", parent=base["Normal"],
        fontSize=9, fontName="Helvetica", textColor=colors.black,
        alignment=TA_CENTER, leading=11, spaceAfter=4)
    s["section"] = ParagraphStyle("section", parent=base["Normal"],
        fontSize=10, fontName="Helvetica-Bold", textColor=colors.black,
        leading=12, spaceBefore=7, spaceAfter=1, textTransform="uppercase")
    s["job_title"] = ParagraphStyle("job_title", parent=base["Normal"],
        fontSize=10, fontName="Helvetica-Bold", textColor=colors.black,
        leading=12, spaceAfter=0,
        leftIndent=0, rightIndent=0, firstLineIndent=0, alignment=TA_LEFT)
    s["date_right"] = ParagraphStyle("date_right", parent=base["Normal"],
        fontSize=9.5, fontName="Helvetica", textColor=colors.black,
        alignment=TA_RIGHT, leading=12, spaceAfter=0,
        leftIndent=0, rightIndent=0, firstLineIndent=0)
    s["bullet"] = ParagraphStyle("bullet", parent=base["Normal"],
        fontSize=9.5, fontName="Helvetica", textColor=colors.black,
        leftIndent=14, firstLineIndent=0, leading=12, spaceAfter=1)
    s["summary"] = ParagraphStyle("summary", parent=base["Normal"],
        fontSize=9.5, fontName="Helvetica", textColor=colors.black,
        leading=12, spaceAfter=4)
    s["skills"] = ParagraphStyle("skills", parent=base["Normal"],
        fontSize=9.5, fontName="Helvetica", textColor=colors.black,
        leading=12, spaceAfter=1)
    s["edu_degree"] = ParagraphStyle("edu_degree", parent=base["Normal"],
        fontSize=10, fontName="Helvetica-Bold", textColor=colors.black,
        leading=12, spaceAfter=0)
    s["edu_school"] = ParagraphStyle("edu_school", parent=base["Normal"],
        fontSize=9.5, fontName="Helvetica", textColor=colors.black,
        leading=12, spaceAfter=1)
    s["edu_detail"] = ParagraphStyle("edu_detail", parent=base["Normal"],
        fontSize=9.5, fontName="Helvetica", textColor=colors.black,
        leftIndent=14, leading=12, spaceAfter=0)
    return s


def _rule():
    """Full-width black underline below section headers, matching original resume."""
    return HRFlowable(width="100%", thickness=0.5, color=colors.black,
                      spaceAfter=3, spaceBefore=0)


def _job_header(company_title: str, date: str, s: dict) -> Table:
    """Company + title on the left, date right-aligned — same line via Table."""
    data = [[
        Paragraph(f"<b>{company_title}</b>", s["job_title"]),
        Paragraph(date, s["date_right"]),
    ]]
    left_w = AVAIL_W * 0.70
    right_w = AVAIL_W - left_w
    t = Table(data, colWidths=[left_w, right_w], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("VALIGN",         (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING",    (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 0),
        ("TOPPADDING",     (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 2),
    ]))
    return t


def _proj_header(name: str, date: str, s: dict) -> Table:
    """Project name (bold) + 'Individual Project' (italic) left, date right."""
    data = [[
        Paragraph(f"<b>{name}</b>, <i>Individual Project</i>", s["job_title"]),
        Paragraph(date, s["date_right"]),
    ]]
    left_w = AVAIL_W * 0.70
    right_w = AVAIL_W - left_w
    t = Table(data, colWidths=[left_w, right_w], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("VALIGN",         (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING",    (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 0),
        ("TOPPADDING",     (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 2),
    ]))
    return t


# ── Master resume loading ─────────────────────────────────────────────────────

_MASTER_CACHE: dict[str, dict] = {}


def _load_master(role_type: str) -> dict:
    """Load the role-specific master JSON. Cached per process."""
    key = role_type if role_type in ("analyst", "pm") else "analyst"
    if key in _MASTER_CACHE:
        return _MASTER_CACHE[key]
    path = Path("assets") / f"base_resume_{key}.json"
    if not path.exists():
        raise FileNotFoundError(f"Master resume not found: {path}")
    master = json.loads(path.read_text())
    _MASTER_CACHE[key] = master
    return master


def _build_corpus(master: dict) -> str:
    """Flatten a master into a lowercase string for keyword match scoring."""
    parts = [master.get("summary", "")]
    for row in master.get("skills", []):
        parts.append(row.get("category", ""))
        parts.append(row.get("items", ""))
    for exp in master.get("experience", []):
        parts.append(exp.get("title", ""))
        parts.append(exp.get("company", ""))
        parts.extend(exp.get("bullets", []))
    for proj in master.get("projects", []):
        parts.append(proj.get("name", ""))
        parts.extend(proj.get("bullets", []))
    for edu in master.get("education", []):
        parts.append(edu.get("degree", ""))
        parts.append(edu.get("school", ""))
    return " ".join(parts).lower()


_TAILORING_STOPWORDS = {
    "with", "that", "this", "from", "have", "will", "your", "their", "must",
    "able", "work", "team", "role", "into", "over", "also", "about", "other",
    "more", "than", "such", "each", "been", "would", "could", "should",
    "using", "within", "across", "strong", "experience", "skills", "required",
    "preferred", "including", "ability", "knowledge", "understanding", "position",
    "candidate", "looking", "seeking", "opportunity", "environment", "support",
}


def _needs_tailoring(job: dict, master: dict, threshold: float = 0.65) -> tuple[bool, float, list[str]]:
    """Check if the role-specific master already covers the job's key requirements.

    Returns (needs_tailoring, match_score 0-1, notable_gaps).
    If match_score >= threshold, bullet tailoring is skipped.
    """
    corpus = _build_corpus(master)
    desc = (job.get("description", "") + " " + job.get("title", "")).lower()
    tokens = [
        w.strip(".,;:()[]/-—")
        for w in desc.split()
        if len(w.strip(".,;:()[]/-—")) > 4
        and w.strip(".,;:()[]/-—") not in _TAILORING_STOPWORDS
    ]
    unique_tokens = list(dict.fromkeys(tokens))[:30]
    if not unique_tokens:
        return False, 1.0, []
    matched = [t for t in unique_tokens if t in corpus]
    unmatched = [t for t in unique_tokens if t not in corpus][:5]
    score = len(matched) / len(unique_tokens)
    return score < threshold, score, unmatched


def resume_match_score(job: dict) -> int:
    """Public helper: return integer match percentage against the correct master."""
    master = _load_master(job.get("role_type") or "analyst")
    _, score, _ = _needs_tailoring(job, master)
    return int(round(score * 100))


# ── Tailoring via Claude ──────────────────────────────────────────────────────

def _load_system_prompt() -> str:
    with open("prompts/job_hunter_system.md", "r") as f:
        return f.read()


def _tailor_summary(job: dict, original_summary: str, feedback: str = "") -> str:
    """Rewrite the summary to match the job. Returns original on failure."""
    system_prompt = _load_system_prompt()
    feedback_line = f"User feedback on the previous version: {feedback}\n\n" if feedback.strip() else ""
    user_message = f"""{feedback_line}Rewrite the resume summary below to better match the job posting.

RULES:
- Keep it truthful. Do NOT invent experience or credentials.
- Target: 2 sentences, under 300 characters total.
- Same professional tone and style as the original.
- Do not use filler phrases like "passionate about" or "results-driven".
- Do not use em dashes.

JOB TITLE: {job.get('title')}
COMPANY: {job.get('company')}
JOB DESCRIPTION (excerpt):
{job.get('description', '')[:2000]}

ORIGINAL SUMMARY:
{original_summary}

Return ONLY the rewritten summary as plain text. No quotes, no markdown, no extra text."""

    result = call_claude(system=system_prompt, user=user_message, max_tokens=150)
    result = result.strip().strip('"').strip("'")
    return result[:300] if result else original_summary


def _tailor_skills(job: dict, skills: list[dict], feedback: str = "") -> list[dict]:
    """Reorder skills rows to front-load those most relevant to the job.

    Input/output: list of {"category", "items"} dicts from the master.
    """
    desc = (job.get("description", "") + " " + job.get("title", "")).lower()

    def relevance(row: dict) -> int:
        combined = (row.get("category", "") + " " + row.get("items", "")).lower()
        keywords = combined.split()
        return sum(1 for kw in keywords if len(kw) > 3 and kw in desc)

    return sorted(skills, key=relevance, reverse=True)


def _parse_bullets_json(raw: str, required_count: int, section: str) -> list[str] | None:
    """Parse a JSON array of bullets from raw LLM output. Returns None on failure."""
    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass
    match = re.search(r'\[.*?\]', raw, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass
    print(f"[resume_builder] Could not parse JSON for '{section}'. Raw: {raw[:200]}")
    return None


def _tailor_bullets(job: dict, section: str, bullets: list[str], feedback: str = "") -> list[str]:
    """Rewrite resume bullets in place for ATS keywords. May add new bullets.

    Never drops bullets. Returns >= len(bullets) items, or raises ValueError
    if the LLM returns fewer than the original count.
    """
    required_count = len(bullets)
    system_prompt = _load_system_prompt()
    feedback_line = f"User feedback on the previous version: {feedback}\n\n" if feedback.strip() else ""

    user_message = f"""{feedback_line}Rewrite the resume bullet points below for the section "{section}" to better match the job.

NON-NEGOTIABLE RULES:
1. Return AT LEAST {required_count} bullets in a JSON array. Never fewer.
2. Keep EVERY original bullet — rewrite in place for ATS keywords, do not drop,
   summarize, or merge any bullet.
3. You MAY add new bullets if the job clearly calls for them and the new bullets
   follow all rules below.
4. Each bullet MUST follow: [Strong action verb] + [what was done] + [tool or method] + [measurable result].
5. Preserve ALL numbers and metrics from the originals. Do not drop or invent figures.
6. Never merge two bullets into one. Never split one into two.
7. Each bullet under 120 characters.
8. Do not fabricate. Only draw from what the originals or the candidate profile describe.
9. Mirror the job description language where honest and accurate.
10. Do not use em dashes.

JOB TITLE: {job.get('title')}
COMPANY: {job.get('company')}
JOB DESCRIPTION (excerpt):
{job.get('description', '')[:2000]}

SECTION: {section}
ORIGINAL BULLETS ({required_count} required, return {required_count} or more):
{chr(10).join(f'{i+1}. {b}' for i, b in enumerate(bullets))}

Return ONLY a JSON array of strings. No markdown, no explanation."""

    raw = call_claude(system=system_prompt, user=user_message, max_tokens=1200)
    result = _parse_bullets_json(raw, required_count, section)

    if result is None:
        raise ValueError(f"LLM returned unparseable bullets for '{section}'")

    if len(result) < required_count:
        raise ValueError(
            f"LLM dropped bullets for '{section}': expected >= {required_count}, got {len(result)}"
        )

    return result


# ── PDF Builder ───────────────────────────────────────────────────────────────

def _format_date_range(exp: dict) -> str:
    start = exp.get("start_date", "")
    end = exp.get("end_date", "")
    if start and end:
        return f"{start} - {end}"
    return start or end


def _role_header_text(exp: dict) -> str:
    """'Company, Location: Title' per reference format."""
    company = exp.get("company", "")
    location = exp.get("location", "")
    title = exp.get("title", "")
    left = f"{company}, {location}" if location else company
    return f"{left}: {title}" if title else left


def build_resume(job: dict, feedback: str = "") -> str:
    """Generate a tailored 1-page PDF resume from the role-specific master. Returns file path."""
    Path(config.RESUMES_DIR).mkdir(parents=True, exist_ok=True)
    out_path = os.path.join(config.RESUMES_DIR, f"{job['job_id']}_resume.pdf")

    role_type = job.get("role_type") or "analyst"
    master = _load_master(role_type)

    # Feedback forces tailoring on regardless of match score.
    tailoring_needed, match_score, gaps = _needs_tailoring(job, master)
    if feedback.strip():
        tailoring_needed = True
    print(f"[resume_builder] Role: {role_type} | Match: {match_score:.0%} | Tailoring: {tailoring_needed}"
          + (f" | Gaps: {gaps}" if gaps else "")
          + (f" | Feedback: yes" if feedback.strip() else ""))

    skills = _tailor_skills(job, master["skills"], feedback=feedback)

    if tailoring_needed:
        summary = _tailor_summary(job, master["summary"], feedback=feedback)
        tailored_experience = []
        for exp in master["experience"]:
            section_label = f"{exp.get('title', '')}, {exp.get('company', '')}"
            new_bullets = _tailor_bullets(job, section_label, exp["bullets"], feedback=feedback)
            tailored_experience.append({**exp, "bullets": new_bullets})
        tailored_projects = []
        for proj in master.get("projects", []):
            new_bullets = _tailor_bullets(job, proj["name"], proj["bullets"], feedback=feedback)
            tailored_projects.append({**proj, "bullets": new_bullets})
    else:
        print(f"[resume_builder] Strong match ({match_score:.0%}) — using master as-is.")
        summary = master["summary"]
        tailored_experience = master["experience"]
        tailored_projects = master.get("projects", [])

    # ── Build flowables ───────────────────────────────────────────────────────
    s = _styles()
    story = []

    # Header
    contact = master["contact"]
    story.append(Paragraph(contact["name"], s["name"]))
    contact_line = " \u2022 ".join([
        v for v in [
            contact.get("phone"), contact.get("email"), contact.get("linkedin"),
            contact.get("github"), contact.get("website"),
        ] if v
    ])
    story.append(Paragraph(contact_line, s["contact"]))

    # Summary
    story.append(Paragraph("Summary", s["section"]))
    story.append(_rule())
    story.append(Paragraph(summary, s["summary"]))

    # Technical Skills
    story.append(Paragraph("Technical Skills", s["section"]))
    story.append(_rule())
    for row in skills:
        story.append(Paragraph(f"<b>{row['category']}:</b> {row['items']}", s["skills"]))

    # Professional Experience
    story.append(Paragraph("Professional Experience", s["section"]))
    story.append(_rule())
    for exp in tailored_experience:
        story.append(_job_header(_role_header_text(exp), _format_date_range(exp), s))
        for b in exp["bullets"]:
            story.append(Paragraph(f"\u25cf {b}", s["bullet"]))
        story.append(Spacer(1, 3))

    # Relevant Projects (PM master has none)
    if tailored_projects:
        story.append(Paragraph("Relevant Projects", s["section"]))
        story.append(_rule())
        for proj in tailored_projects:
            story.append(_proj_header(proj["name"], proj.get("date", ""), s))
            for b in proj["bullets"]:
                story.append(Paragraph(f"\u25cf {b}", s["bullet"]))
            story.append(Spacer(1, 3))

    # Education
    story.append(Paragraph("Education", s["section"]))
    story.append(_rule())
    for edu in master.get("education", []):
        story.append(_job_header(f"<b>{edu['degree']}</b>", edu.get("graduation_date", ""), s))
        if edu.get("school"):
            story.append(Paragraph(edu["school"], s["edu_school"]))
        for honor in edu.get("honors", []):
            story.append(Paragraph(f"\u25cf {honor}", s["edu_detail"]))

    # ── Enforce one page via KeepInFrame ──────────────────────────────────────
    doc = SimpleDocTemplate(
        out_path,
        pagesize=letter,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
    )
    contained = KeepInFrame(
        maxWidth=AVAIL_W,
        maxHeight=AVAIL_H,
        content=story,
        mode='shrink',
    )
    doc.build([contained])
    return out_path
