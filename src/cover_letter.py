"""Generate a tailored, concise cover letter PDF using Claude + ReportLab."""
import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from datetime import date

import config
from src.llm import call_llm

DARK = colors.HexColor("#1a1a2e")


def _load_system_prompt() -> str:
    with open("prompts/job_hunter_system.md", "r") as f:
        return f.read()


def _generate_text(job: dict) -> str:
    user_message = f"""Write a cover letter for this job posting. Follow the cover letter format, tone, and length guidelines in your instructions.

Output ONLY the body paragraphs (no date, no address block, no subject line, no salutation). 3-4 paragraphs separated by blank lines.

Job Title: {job.get('title', '')}
Company: {job.get('company', '')}
Location: {job.get('location', '')}
Job Description:
{job.get('description', '')[:2500]}"""

    return call_llm(system=_load_system_prompt(), user=user_message, max_tokens=600)


def _styles():
    base = getSampleStyleSheet()
    return {
        "header": ParagraphStyle("header", parent=base["Normal"],
            fontSize=11, fontName="Helvetica-Bold", textColor=DARK, spaceAfter=2),
        "contact": ParagraphStyle("contact", parent=base["Normal"],
            fontSize=9, fontName="Helvetica", textColor=colors.HexColor("#555"),
            spaceAfter=16),
        "date": ParagraphStyle("date", parent=base["Normal"],
            fontSize=9, fontName="Helvetica", textColor=DARK, spaceAfter=10),
        "salutation": ParagraphStyle("salutation", parent=base["Normal"],
            fontSize=10, fontName="Helvetica", textColor=DARK, spaceAfter=8),
        "body": ParagraphStyle("body", parent=base["Normal"],
            fontSize=10, fontName="Helvetica", textColor=DARK,
            spaceAfter=10, leading=14, alignment=TA_JUSTIFY),
        "closing": ParagraphStyle("closing", parent=base["Normal"],
            fontSize=10, fontName="Helvetica", textColor=DARK,
            spaceAfter=4, spaceBefore=14),
        "sig": ParagraphStyle("sig", parent=base["Normal"],
            fontSize=10, fontName="Helvetica-Bold", textColor=DARK),
    }


def get_cover_letter_text(job: dict) -> str:
    """Return the plain-text cover letter body (no PDF). Used by ATS text areas."""
    return _generate_text(job)


def build_cover_letter(job: dict) -> str:
    """Generate a tailored cover letter PDF. Returns the file path."""
    Path(config.COVER_LETTERS_DIR).mkdir(parents=True, exist_ok=True)
    out_path = os.path.join(config.COVER_LETTERS_DIR, f"{job['job_id']}_cover_letter.pdf")

    body_text = _generate_text(job)
    paragraphs = [p.strip() for p in body_text.split("\n\n") if p.strip()]

    s = _styles()
    doc = SimpleDocTemplate(
        out_path,
        pagesize=letter,
        leftMargin=1.0 * inch,
        rightMargin=1.0 * inch,
        topMargin=1.0 * inch,
        bottomMargin=1.0 * inch,
    )

    story = []

    # Header
    story.append(Paragraph("Osvaldo Ruiz", s["header"]))
    story.append(Paragraph(
        "619-213-9405 &bull; oruiz.code@gmail.com &bull; linkedin.com/in/OsvaldoRuiz",
        s["contact"]
    ))

    # Date + addressee
    story.append(Paragraph(date.today().strftime("%B %d, %Y"), s["date"]))
    story.append(Paragraph(f"Hiring Manager<br/>{job.get('company', '')}", s["salutation"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Re: {job.get('title', 'Position')} — {job.get('company', '')}", s["salutation"]))
    story.append(Spacer(1, 8))

    # Body
    for para in paragraphs:
        story.append(Paragraph(para, s["body"]))

    # Closing
    story.append(Paragraph("Sincerely,", s["closing"]))
    story.append(Spacer(1, 20))
    story.append(Paragraph("Osvaldo Ruiz", s["sig"]))

    doc.build(story)
    return out_path
