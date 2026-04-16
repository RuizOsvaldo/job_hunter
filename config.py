"""Central configuration for the job hunter tool."""
import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM Provider ────────────────────────────────────────────────────────────
# Set LLM_PROVIDER to "groq" in .env to use Groq for free (Llama 3.3 70B)
# Set to "claude" to use Anthropic's Claude (higher quality, costs money)
LLM_PROVIDER  = os.getenv("LLM_PROVIDER", "claude")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL  = "claude-sonnet-4-6"
GROQ_API_KEY  = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL    = "llama-3.3-70b-versatile"

# ── Email ────────────────────────────────────────────────────────────────────
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "oruiz.code@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL", "oruiz.code@gmail.com")

# ── Platform Credentials (Easy Apply automation) ─────────────────────────────
INDEED_EMAIL    = os.getenv("INDEED_EMAIL", "")
INDEED_PASSWORD = os.getenv("INDEED_PASSWORD", "")
LINKEDIN_EMAIL    = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

# ── Job Search Settings ───────────────────────────────────────────────────────
SEARCH_TERMS = [
    "Data Analyst",
    "Data Analyst Python SQL",
    "Business Intelligence Analyst",
    "Business Analyst SQL",
    "Program Analyst data",
    "Reporting Analyst",
    "Data Analytics Coordinator",
    "Program Manager",
    "Technical Program Manager",
    "Project Manager",
]

SEARCH_LOCATIONS = [
    "San Diego, CA",
    "remote",
]

# Jobs posted within this many hours are included
HOURS_OLD = 24
RESULTS_PER_SEARCH = 10

# ── Scoring ───────────────────────────────────────────────────────────────────
AUTO_APPLY_THRESHOLD = 7   # Score >= this → auto-apply after user approval
MIN_SALARY = 80_000        # Annual; jobs below this score lower

# ── Paths ─────────────────────────────────────────────────────────────────────
DB_PATH = "data/jobs.db"
RESUMES_DIR = "data/resumes"
COVER_LETTERS_DIR = "data/cover_letters"
BASE_RESUME_PATH = "assets/base_resume.json"

# ── Scheduler ─────────────────────────────────────────────────────────────────
SCHEDULE_HOURS = [8]  # 8:00 AM weekdays
DIGEST_ENABLED = os.getenv("DIGEST_ENABLED", "true").lower() == "true"
