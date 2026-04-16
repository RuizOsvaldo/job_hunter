"""Parse the reference resume .docx files in assets/ into two JSON masters.

Outputs:
  assets/base_resume_analyst.json
  assets/base_resume_pm.json

Run once (and again any time the reference .docx files change):
  python scripts/build_masters.py
"""
import json
import re
from pathlib import Path

from docx import Document


REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS = REPO_ROOT / "assets"

ANALYST_DOCX = ASSETS / "Osvaldo Ruiz Resume Analyst.docx"
PM_DOCX      = ASSETS / "Osvaldo Ruiz Resume Program Manager.docx"

SECTION_HEADERS = {
    "SUMMARY",
    "TECHNICAL SKILLS",
    "PROFESSIONAL EXPERIENCE",
    "RELEVANT PROJECTS",
    "EDUCATION",
}


def _nonempty_paragraphs(doc: Document) -> list:
    """Return paragraphs with non-empty text, paired with a bold flag."""
    out = []
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        bolds = [r.bold for r in p.runs if r.text.strip()]
        bold = any(bolds) if bolds else False
        out.append((text, bold))
    return out


def _split_contact(line: str) -> dict:
    parts = [p.strip() for p in line.split("\u2022") if p.strip()]
    return {
        "phone":    parts[0] if len(parts) > 0 else "",
        "email":    parts[1] if len(parts) > 1 else "",
        "linkedin": parts[2] if len(parts) > 2 else "",
        "github":   parts[3] if len(parts) > 3 else "",
        "website":  parts[4] if len(parts) > 4 else "",
    }


def _parse_role_header(text: str) -> dict:
    """'Company, City, ST: Title\\tDate' → {company, location, title, start_date, end_date}."""
    parts = re.split(r"\t+|\s{3,}", text)
    header = parts[0].strip()
    date_str = parts[-1].strip() if len(parts) > 1 else ""

    title = ""
    location = ""
    company = header
    if ":" in header:
        left, title = header.rsplit(":", 1)
        title = title.strip()
        left_parts = [p.strip() for p in left.split(",")]
        company = left_parts[0]
        location = ", ".join(left_parts[1:]) if len(left_parts) > 1 else ""

    start_date, end_date = "", ""
    if date_str:
        m = re.split(r"\s*[-\u2013]\s*", date_str, maxsplit=1)
        start_date = m[0].strip()
        end_date = m[1].strip() if len(m) > 1 else ""

    return {
        "company": company,
        "location": location,
        "title": title,
        "start_date": start_date,
        "end_date": end_date,
    }


def _parse_project_header(text: str) -> dict:
    """'IBM HR Attrition Analysis Dashboard, Individual Project\\t...\\tFebruary 2026' → {name, date}."""
    parts = [p.strip() for p in re.split(r"\t+|\s{3,}", text) if p.strip()]
    name_part = parts[0]
    date = parts[-1] if len(parts) > 1 else ""
    name = re.sub(r",\s*Individual Project\s*$", "", name_part).strip()
    return {"name": name, "date": date}


def _parse_education_header(text: str) -> dict:
    """'B.S. Information Technology, Concentration on Information Systems\\tDecember 2024'."""
    parts = re.split(r"\t+|\s{3,}", text, maxsplit=1)
    degree = parts[0].strip()
    graduation_date = parts[1].strip() if len(parts) > 1 else ""
    return {"degree": degree, "graduation_date": graduation_date}


def _parse_skill_row(text: str) -> dict:
    """'Category: item1, item2, item3' → {category, items}."""
    if ":" not in text:
        return {"category": "", "items": text}
    category, items = text.split(":", 1)
    return {"category": category.strip(), "items": items.strip()}


def parse_resume(path: Path, role_type: str) -> dict:
    doc = Document(path)
    paragraphs = _nonempty_paragraphs(doc)

    master = {
        "role_type": role_type,
        "contact": {"name": "", "phone": "", "email": "", "linkedin": "", "github": "", "website": ""},
        "summary": "",
        "skills": [],
        "experience": [],
        "projects": [],
        "education": [],
    }

    # Header (first two non-empty paragraphs are name + contact line)
    if not paragraphs:
        raise ValueError(f"Empty document: {path}")
    master["contact"]["name"] = paragraphs[0][0]
    master["contact"].update(_split_contact(paragraphs[1][0]))

    section = None
    current_exp = None
    current_project = None
    current_edu = None

    for text, bold in paragraphs[2:]:
        if text.upper() in SECTION_HEADERS and bold:
            section = text.upper()
            current_exp = None
            current_project = None
            current_edu = None
            continue

        if section == "SUMMARY":
            master["summary"] = (master["summary"] + " " + text).strip() if master["summary"] else text

        elif section == "TECHNICAL SKILLS":
            if bold:
                master["skills"].append(_parse_skill_row(text))

        elif section == "PROFESSIONAL EXPERIENCE":
            if bold:
                current_exp = _parse_role_header(text)
                current_exp["bullets"] = []
                master["experience"].append(current_exp)
            elif current_exp is not None:
                current_exp["bullets"].append(text)

        elif section == "RELEVANT PROJECTS":
            if bold:
                current_project = _parse_project_header(text)
                current_project["bullets"] = []
                master["projects"].append(current_project)
            elif current_project is not None:
                current_project["bullets"].append(text)

        elif section == "EDUCATION":
            if bold:
                current_edu = _parse_education_header(text)
                current_edu["school"] = ""
                current_edu["honors"] = []
                master["education"].append(current_edu)
            elif current_edu is not None:
                if not current_edu["school"]:
                    current_edu["school"] = text
                else:
                    current_edu["honors"].append(text)

    return master


def main():
    analyst = parse_resume(ANALYST_DOCX, "analyst")
    pm = parse_resume(PM_DOCX, "pm")

    (ASSETS / "base_resume_analyst.json").write_text(json.dumps(analyst, indent=2, ensure_ascii=False))
    (ASSETS / "base_resume_pm.json").write_text(json.dumps(pm, indent=2, ensure_ascii=False))

    old_master = ASSETS / "base_resume.json"
    if old_master.exists():
        old_master.unlink()

    print(f"Wrote assets/base_resume_analyst.json ({len(analyst['experience'])} jobs, {len(analyst['projects'])} projects)")
    print(f"Wrote assets/base_resume_pm.json ({len(pm['experience'])} jobs, {len(pm['projects'])} projects)")
    if not old_master.exists():
        print("Removed old assets/base_resume.json")


if __name__ == "__main__":
    main()
