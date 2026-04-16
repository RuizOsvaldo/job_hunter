"""Score jobs 1-10 using the configured LLM with the job_hunter_system.md system prompt."""
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import config
from src.database import get_jobs, set_score
from src.llm import call_llm

# Groq free tier is rate-limited; 1 worker avoids hammering the API.
# Claude can safely use more workers.
_SCORE_WORKERS = 1 if config.LLM_PROVIDER == "groq" else 5

# Title keywords that must appear for a job to be worth scoring.
# Anything that doesn't match any of these is skipped immediately — no LLM call.
_TITLE_KEYWORDS = {
    "analyst", "analytics", "analysis", "data", "business intelligence",
    "reporting", "insights", "metrics", "dashboard", "intelligence",
    "bi ", " bi", "etl", "sql", "python", "program analyst",
    "operations analyst", "coordinator",
    "program manager", "project manager", "technical program manager", "tpm",
}

# Title keywords that are hard rejections even if a soft keyword matched.
# e.g. "Data Entry Specialist" matches "data" but is clearly not a fit.
_TITLE_BLOCKLIST = {
    "data entry", "office associate", "receptionist", "administrative assistant",
    "solutions architect", "enterprise architect", "software engineer",
    "software developer", "devops engineer", "sre ", "site reliability",
    "clinical data", "sales representative", "account executive",
    "account manager", "store manager", "warehouse", "driver",
}


def _title_passes_filter(title: str) -> bool:
    """Return True if the job title is worth spending an LLM call to score.

    Any title containing 'analyst' always passes — blocklist does not apply.
    """
    t = title.lower()
    if "analyst" in t:
        return True
    if any(block in t for block in _TITLE_BLOCKLIST):
        return False
    return any(kw in t for kw in _TITLE_KEYWORDS)


def _load_system_prompt() -> str:
    with open("prompts/job_hunter_system.md", "r") as f:
        return f.read()


def score_job(job: dict, system_prompt: str = None) -> tuple[float, list[str], str]:
    """Score a single job. Returns (score, reasons, industry)."""
    if system_prompt is None:
        system_prompt = _load_system_prompt()

    salary_str = "Not listed"
    if job.get("salary_min") and job.get("salary_max"):
        salary_str = f"${job['salary_min']:,} – ${job['salary_max']:,}"
    elif job.get("salary_min"):
        salary_str = f"${job['salary_min']:,}+"

    user_message = f"""Evaluate this job posting and return your response as valid JSON only, with this exact structure:
{{"score": <number 1-10, one decimal>, "reasons": ["<reason 1>", "<reason 2>", "<reason 3>"], "industry": "tech" | "non-tech"}}

No other text. No markdown fences. Follow the Industry Classification rules in the system prompt exactly — "tech" or "non-tech" only.

Job Title: {job.get('title', '')}
Company: {job.get('company', '')}
Location: {job.get('location', '')}
Salary: {salary_str}
Description:
{job.get('description', '')[:4000]}"""

    raw = call_llm(system=system_prompt, user=user_message, max_tokens=512)
    data = json.loads(raw)
    industry = data.get("industry")
    if industry not in ("tech", "non-tech"):
        raise ValueError(f"Scorer returned invalid industry: {industry!r}")
    return float(data["score"]), data["reasons"], industry


def score_unscored_jobs() -> int:
    """Score all jobs in 'found' status in parallel. Returns count scored.

    Jobs whose titles don't match _TITLE_KEYWORDS are marked 'skipped' without
    an LLM call, preserving Groq quota for genuine candidates.
    """
    from src.database import set_status
    jobs = get_jobs("found")
    if not jobs:
        return 0

    # Pre-filter by title — free, instant, saves LLM quota
    scoreable, skipped = [], []
    for job in jobs:
        if _title_passes_filter(job.get("title", "")):
            scoreable.append(job)
        else:
            skipped.append(job)

    for job in skipped:
        set_status(job["job_id"], "skipped")
        print(f"[scorer] SKIPPED (title filter): {job['title']} @ {job['company']}")

    if skipped:
        print(f"[scorer] Title filter: {len(skipped)} skipped, {len(scoreable)} queued for scoring")

    if not scoreable:
        return 0

    system_prompt = _load_system_prompt()  # load once, reuse across all workers
    scored = 0

    def _score_one(job):
        for attempt in range(4):
            try:
                score, reasons, industry = score_job(job, system_prompt)
                if industry == "non-tech":
                    set_status(job["job_id"], "skipped", "Non-tech industry")
                    print(f"[scorer] SKIPPED (non-tech): {job['title']} @ {job['company']}")
                    return 1
                set_score(job["job_id"], score, reasons, industry=industry)
                status = "pending_review" if score >= config.AUTO_APPLY_THRESHOLD else "scored"
                print(f"[scorer] {job['title']} @ {job['company']} → {score}/10 ({status}) [tech]")
                return 1
            except Exception as e:
                if "rate" in str(e).lower() and attempt < 3:
                    wait = 2 ** attempt * 5  # 5s, 10s, 20s
                    print(f"[scorer] Rate limit, retrying in {wait}s ({job['title']})")
                    time.sleep(wait)
                else:
                    print(f"[scorer] Failed {job['title']}: {e}")
                    return 0
        return 0

    with ThreadPoolExecutor(max_workers=_SCORE_WORKERS) as pool:
        futures = {pool.submit(_score_one, job): job for job in scoreable}
        for future in as_completed(futures):
            try:
                scored += future.result()
            except Exception as e:
                job = futures[future]
                print(f"[scorer] Error scoring {job['job_id']}: {e}")

    return scored
