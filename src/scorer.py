"""Score jobs 1-10 using the configured LLM with the job_hunter_system.md system prompt."""
import json
import config
from src.database import get_jobs, set_score
from src.llm import call_llm


def _load_system_prompt() -> str:
    with open("prompts/job_hunter_system.md", "r") as f:
        return f.read()


def score_job(job: dict) -> tuple[float, list[str]]:
    """Score a single job. Returns (score, reasons)."""
    salary_str = "Not listed"
    if job.get("salary_min") and job.get("salary_max"):
        salary_str = f"${job['salary_min']:,} – ${job['salary_max']:,}"
    elif job.get("salary_min"):
        salary_str = f"${job['salary_min']:,}+"

    user_message = f"""Evaluate this job posting and return your response as valid JSON only, with this exact structure:
{{"score": <number 1-10, one decimal>, "reasons": ["<reason 1>", "<reason 2>", "<reason 3>"]}}

No other text. No markdown fences.

Job Title: {job.get('title', '')}
Company: {job.get('company', '')}
Location: {job.get('location', '')}
Salary: {salary_str}
Description:
{job.get('description', '')[:4000]}"""

    raw = call_llm(system=_load_system_prompt(), user=user_message, max_tokens=512)
    data = json.loads(raw)
    return float(data["score"]), data["reasons"]


def score_unscored_jobs() -> int:
    """Score all jobs in 'found' status. Returns count scored."""
    jobs = get_jobs("found")
    scored = 0
    for job in jobs:
        try:
            score, reasons = score_job(job)
            set_score(job["job_id"], score, reasons)
            status = "pending_review" if score >= config.AUTO_APPLY_THRESHOLD else "scored"
            print(f"[scorer] {job['title']} @ {job['company']} → {score}/10 ({status})")
            scored += 1
        except Exception as e:
            print(f"[scorer] Error scoring {job['job_id']}: {e}")
    return scored
