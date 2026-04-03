"""Generate a tailored 1-page PDF resume using ReportLab."""
import json
import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, ListFlowable, ListItem
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
import config
from src.llm import call_llm

# ── Styles ────────────────────────────────────────────────────────────────────

DARK = colors.HexColor("#1a1a2e")
ACCENT = colors.HexColor("#16213e")
RULE = colors.HexColor("#0f3460")


def _styles():
    base = getSampleStyleSheet()
    s = {}
    s["name"] = ParagraphStyle("name", parent=base["Normal"],
        fontSize=16, fontName="Helvetica-Bold", textColor=DARK,
        alignment=TA_CENTER, spaceAfter=2)
    s["contact"] = ParagraphStyle("contact", parent=base["Normal"],
        fontSize=8, fontName="Helvetica", textColor=colors.HexColor("#555555"),
        alignment=TA_CENTER, spaceAfter=6)
    s["section"] = ParagraphStyle("section", parent=base["Normal"],
        fontSize=9, fontName="Helvetica-Bold", textColor=RULE,
        spaceBefore=6, spaceAfter=2, textTransform="uppercase",
        letterSpacing=1)
    s["job_title"] = ParagraphStyle("job_title", parent=base["Normal"],
        fontSize=9, fontName="Helvetica-Bold", textColor=DARK, spaceAfter=0)
    s["job_meta"] = ParagraphStyle("job_meta", parent=base["Normal"],
        fontSize=8, fontName="Helvetica-Oblique", textColor=colors.HexColor("#666666"),
        spaceAfter=2)
    s["bullet"] = ParagraphStyle("bullet", parent=base["Normal"],
        fontSize=8, fontName="Helvetica", textColor=DARK,
        leftIndent=10, spaceAfter=1, leading=11)
    s["summary"] = ParagraphStyle("summary", parent=base["Normal"],
        fontSize=8.5, fontName="Helvetica", textColor=DARK,
        spaceAfter=4, leading=12)
    s["skills_label"] = ParagraphStyle("skills_label", parent=base["Normal"],
        fontSize=8, fontName="Helvetica-Bold", textColor=DARK, spaceAfter=0)
    s["skills_value"] = ParagraphStyle("skills_value", parent=base["Normal"],
        fontSize=8, fontName="Helvetica", textColor=DARK, spaceAfter=2)
    return s


def _rule():
    return HRFlowable(width="100%", thickness=0.5, color=RULE, spaceAfter=4, spaceBefore=0)


# ── Tailoring via Claude ──────────────────────────────────────────────────────

def _tailor_bullets(job: dict, section: str, bullets: list[str]) -> list[str]:
    """Rewrite resume bullets to match the job description."""
    with open("prompts/job_hunter_system.md", "r") as f:
        system_prompt = f.read()

    user_message = f"""Rewrite these resume bullet points to better match the job posting.
Keep bullets truthful — do NOT invent metrics or experiences.
Tighten language. Prefer action verbs. Keep each bullet under 120 characters.

JOB TITLE: {job.get('title')}
COMPANY: {job.get('company')}
JOB DESCRIPTION (excerpt):
{job.get('description', '')[:2000]}

SECTION: {section}
ORIGINAL BULLETS:
{chr(10).join(f'- {b}' for b in bullets)}

Return ONLY a JSON array of strings — the rewritten bullets (same count or fewer).
No markdown, no extra text."""

    raw = call_llm(system=system_prompt, user=user_message, max_tokens=600)
    return json.loads(raw)


# ── PDF Builder ───────────────────────────────────────────────────────────────

def build_resume(job: dict) -> str:
    """Generate a tailored 1-page PDF resume. Returns the file path."""
    Path(config.RESUMES_DIR).mkdir(parents=True, exist_ok=True)
    out_path = os.path.join(config.RESUMES_DIR, f"{job['job_id']}_resume.pdf")

    s = _styles()
    doc = SimpleDocTemplate(
        out_path,
        pagesize=letter,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
    )

    # ── Tailor bullets via Claude ─────────────────────────────────────────────
    league_bullets_raw = [
        "Led operations for a technical school, overseeing 7 staff and 20+ volunteers; hiring, onboarding, and training instructors, increasing student retention by 18%.",
        "Designed advanced Excel reports to track onboarding and training metrics, improving staff retention by 25% and saving $12,350 through volunteer coordination.",
        "Built and maintained Java and Python curriculum, expanding program reach to 1,000+ students across San Diego.",
    ]
    border_bullets_raw = [
        "Built Python ETL pipeline consolidating cross-departmental data into automated Google Sheets dashboard, enabling KPI tracking across $84K+ in expenditures.",
        "Developed automated Excel reporting and volunteer management workflows, saving $12,000+ annually through process optimization.",
        "Delivered data-driven presentations to 600+ participants, increasing monetary donations by 30%.",
    ]
    sbux_bullets_raw = [
        "Analyzed P&L and weekly reports to direct a 30+ employee team at a $2.5M annual revenue location, increasing profit by 14%.",
        "Improved customer satisfaction by 230% using weekly data to drive targeted coaching and performance adjustments.",
        "Recognized as Starbucks Manager of the Quarter (FY20/Q1) and San Diego Barista Champion (2017).",
    ]

    try:
        league_bullets = _tailor_bullets(job, "Program Manager, The LEAGUE", league_bullets_raw)
        border_bullets = _tailor_bullets(job, "Programs Coordinator, Border Angels", border_bullets_raw)
        sbux_bullets = _tailor_bullets(job, "Store Manager, Starbucks", sbux_bullets_raw)
    except Exception:
        league_bullets = league_bullets_raw
        border_bullets = border_bullets_raw
        sbux_bullets = sbux_bullets_raw

    # ── Build flowables ───────────────────────────────────────────────────────
    story = []

    # Header
    story.append(Paragraph("Osvaldo Ruiz", s["name"]))
    story.append(Paragraph(
        "619-213-9405 &bull; oruiz.code@gmail.com &bull; "
        "linkedin.com/in/OsvaldoRuiz &bull; github.com/ruizOsvaldo &bull; ruizosvaldo.github.io",
        s["contact"]
    ))
    story.append(_rule())

    # Summary
    story.append(Paragraph("Summary", s["section"]))
    story.append(Paragraph(
        "Data Analyst with 9+ years of experience driving measurable results through team leadership, "
        "process improvement, and data-driven decision-making. Skilled in Python, SQL, GCP, and cloud "
        "automation to build ETL pipelines, dashboards, and data-driven workflows.",
        s["summary"]
    ))
    story.append(_rule())

    # Technical Skills
    story.append(Paragraph("Technical Skills", s["section"]))
    skills = [
        ("Programming & Automation", "Python (Pandas, NumPy, Playwright), SQL, Google Apps Script (JavaScript)"),
        ("Cloud & Infrastructure", "GCP (BigQuery, Cloud Storage, Cloud Functions), AWS (in progress), Docker, Ansible"),
        ("Data & Visualization", "Google Sheets (advanced), Looker Studio, ETL pipeline design, data cleaning"),
        ("Tools & Platforms", "Git/GitHub, web scraping, cron scheduling, ntfy.sh push notifications"),
        ("Certifications", "AWS Solutions Architect Associate (in progress), DevOps/Linux (COMP 643, in progress)"),
    ]
    for label, value in skills:
        story.append(Paragraph(f"<b>{label}:</b> {value}", s["skills_value"]))
    story.append(_rule())

    # Experience
    story.append(Paragraph("Professional Experience", s["section"]))

    def exp_block(title_co, date, bullets):
        story.append(Paragraph(title_co, s["job_title"]))
        story.append(Paragraph(date, s["job_meta"]))
        for b in bullets:
            story.append(Paragraph(f"• {b}", s["bullet"]))
        story.append(Spacer(1, 3))

    exp_block(
        "The LEAGUE of Amazing Programmers, San Diego, CA — Program Manager",
        "September 2021 – Present",
        league_bullets,
    )
    exp_block(
        "Border Angels, San Diego, CA — Programs Coordinator",
        "December 2015 – Present",
        border_bullets,
    )
    exp_block(
        "Starbucks, San Diego, CA — Store Manager",
        "November 2013 – March 2021",
        sbux_bullets,
    )
    story.append(_rule())

    # Projects
    story.append(Paragraph("Relevant Projects", s["section"]))

    def proj_block(name, date, bullets):
        story.append(Paragraph(f"<b>{name}</b> — <i>Individual Project</i>", s["job_title"]))
        story.append(Paragraph(date, s["job_meta"]))
        for b in bullets:
            story.append(Paragraph(f"• {b}", s["bullet"]))
        story.append(Spacer(1, 2))

    proj_block("IBM HR Attrition Analysis Dashboard (Tableau)", "February 2026", [
        "Built interactive Tableau dashboard analyzing attrition across 1,470 employees; identified overtime workers leave at 3× the rate of non-overtime peers.",
        "Discovered 40% attrition among Sales Reps and 35% turnover in first-year employees using calculated fields and dynamic filters.",
    ])
    proj_block("Economic Indicators Dashboard (Python, PostgreSQL, Google Sheets)", "January 2026", [
        "Engineered Python ETL pipeline extracting 13 economic indicators from the FRED API into PostgreSQL with 10+ years of historical data.",
        "Built SQL analytics with window functions (YoY changes, rolling averages, yield curve recession signals) and an auto-refreshing Google Sheets dashboard.",
    ])
    proj_block("Google Analytics E-Commerce Dashboard (BigQuery, Google Sheets)", "January 2026", [
        "Engineered BigQuery views analyzing 903,653 sessions and $1.54M revenue; built 4-pivot dashboard with 6 slicers across channels, devices, and geography.",
        "Found desktop users generate 95.6% of revenue despite mobile being 23% of traffic; referral channel drives 42% of total revenue.",
    ])
    story.append(_rule())

    # Education
    story.append(Paragraph("Education", s["section"]))
    story.append(Paragraph(
        "<b>B.S. Information Technology, Concentration on Information Systems</b> — Arizona State University",
        s["job_title"]
    ))
    story.append(Paragraph("Conferred December 2024 &bull; Dean's List, Fall 2023", s["job_meta"]))

    doc.build(story)
    return out_path
