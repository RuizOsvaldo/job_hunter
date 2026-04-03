"""
Auto-apply via Playwright. Supports:
  - Indeed Easy Apply
  - LinkedIn Easy Apply
  - Greenhouse ATS  (boards.greenhouse.io)
  - Lever ATS       (jobs.lever.co)
  - External / unknown → flagged for manual apply

apply_job() detects the ATS from the job URL and routes automatically.
"""
import asyncio
import json
import os
import random
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

import config
from src.database import set_status, set_documents, get_job
from src.resume_builder import build_resume
from src.cover_letter import build_cover_letter, get_cover_letter_text
from src.notifier import notify_applied, notify_apply_failed

INDEED_COOKIES_PATH   = "data/indeed_cookies.json"
LINKEDIN_COOKIES_PATH = "data/linkedin_cookies.json"

CANDIDATE = {
    "first_name": "Osvaldo",
    "last_name":  "Ruiz",
    "full_name":  "Osvaldo Ruiz",
    "email":      "oruiz.code@gmail.com",
    "phone":      "6192139405",
    "city":       "San Diego",
    "state":      "CA",
    "zip":        "92101",
    "location":   "San Diego, CA",
    "linkedin":   "linkedin.com/in/OsvaldoRuiz",
    "website":    "ruizosvaldo.github.io",
}

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


# ── ATS detection ─────────────────────────────────────────────────────────────

def _detect_ats(url: str) -> str:
    """Return 'indeed' | 'linkedin' | 'greenhouse' | 'lever' | 'external'."""
    if not url:
        return "external"
    u = url.lower()
    if "greenhouse.io" in u or "grnh.se" in u:
        return "greenhouse"
    if "lever.co" in u:
        return "lever"
    if "linkedin.com" in u:
        return "linkedin"
    if "indeed.com" in u:
        return "indeed"
    return "external"


# ── Cookie helpers ────────────────────────────────────────────────────────────

async def _save_cookies(context, path: str):
    cookies = await context.cookies()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(cookies, f)


async def _load_cookies(context, path: str) -> bool:
    if Path(path).exists():
        with open(path) as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)
        return True
    return False


# ── Login ─────────────────────────────────────────────────────────────────────

async def _login_indeed(page, context) -> bool:
    await _load_cookies(context, INDEED_COOKIES_PATH)
    await page.goto("https://www.indeed.com/", wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(2)

    if any(p in page.url for p in ["indeed.com/account", "indeed.com/myjobs"]):
        return True
    signed_in = await page.query_selector('[data-gnav-element-name="UserDropdown"]')
    if signed_in:
        return True

    print("[applicator] Indeed session expired — run: python scripts/save_cookies.py indeed")
    return False


async def _login_linkedin(page, context) -> bool:
    await _load_cookies(context, LINKEDIN_COOKIES_PATH)
    await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(2)

    if "linkedin.com/feed" in page.url:
        return True

    try:
        await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
        await asyncio.sleep(1)
        await page.fill('input#username', config.LINKEDIN_EMAIL, timeout=8000)
        await page.fill('input#password', config.LINKEDIN_PASSWORD, timeout=8000)
        await page.click('button[type="submit"]', timeout=5000)
        await asyncio.sleep(3)
        if "feed" in page.url or "jobs" in page.url:
            await _save_cookies(context, LINKEDIN_COOKIES_PATH)
            return True
        print("[applicator] LinkedIn session expired — run: python scripts/save_cookies.py linkedin")
        return False
    except Exception as e:
        print(f"[applicator] LinkedIn login failed: {e}")
        return False


# ── Shared form helpers ───────────────────────────────────────────────────────

async def _fill_if_empty(page, selector: str, value: str, timeout: int = 3000):
    try:
        el = await page.wait_for_selector(selector, timeout=timeout)
        current = await el.input_value()
        if not current.strip():
            await el.fill(value)
    except PlaywrightTimeout:
        pass


async def _upload_file(page, selector: str, file_path: str, timeout: int = 5000):
    try:
        el = await page.wait_for_selector(selector, timeout=timeout)
        await el.set_input_files(os.path.abspath(file_path))
        await asyncio.sleep(2)
        return True
    except PlaywrightTimeout:
        return False


async def _answer_custom_questions(page):
    """Best-effort answers to screening questions common across ATS platforms."""
    try:
        # Dropdowns — select first non-blank option if unanswered
        selects = await page.query_selector_all("select")
        for sel in selects[:8]:
            val = await sel.evaluate("el => el.value")
            if not val:
                options = await sel.evaluate("el => [...el.options].map(o => o.value)")
                if len(options) > 1:
                    await sel.select_option(options[1])
                    await asyncio.sleep(0.2)

        # Radio buttons — answer each named group once (first option)
        radios = await page.query_selector_all('input[type="radio"]')
        answered = set()
        for radio in radios:
            name = await radio.get_attribute("name") or ""
            if name not in answered:
                await radio.check()
                answered.add(name)
                await asyncio.sleep(0.2)

        # Number inputs — fill blanks with reasonable defaults
        number_inputs = await page.query_selector_all('input[type="number"]')
        for inp in number_inputs[:8]:
            val = await inp.input_value()
            if val.strip():
                continue
            label_text = ""
            try:
                label = await inp.evaluate_handle(
                    "el => el.closest('div,li,label')?.querySelector('label,span')"
                )
                label_text = (await label.inner_text()).lower() if label else ""
            except Exception:
                pass
            if "python" in label_text:
                await inp.fill("3")
            elif "sql" in label_text:
                await inp.fill("5")
            elif "year" in label_text or "experience" in label_text:
                await inp.fill("4")
            else:
                await inp.fill("3")

    except Exception as e:
        print(f"[applicator] Custom question error (non-fatal): {e}")


async def _check_success(page, platform: str) -> bool:
    """Return True if the page indicates a successful submission."""
    await asyncio.sleep(2)
    url = page.url.lower()
    try:
        body = (await page.inner_text("body")).lower()
    except Exception:
        body = ""

    success_signals = [
        "thank you", "application received", "application submitted",
        "successfully submitted", "we'll be in touch", "submission confirmed",
        "your application", "thank-you", "confirmation",
    ]
    if any(s in url for s in ["thank-you", "confirmation", "submitted", "success"]):
        return True
    if any(s in body for s in success_signals):
        return True
    return False


# ── Indeed form flow ──────────────────────────────────────────────────────────

async def _fill_indeed_contact(page):
    await _fill_if_empty(page, 'input[name="applicant.name.first"]', CANDIDATE["first_name"])
    await _fill_if_empty(page, 'input[name="applicant.name.last"]',  CANDIDATE["last_name"])
    await _fill_if_empty(page, 'input[name="applicant.phoneNumber"]', CANDIDATE["phone"])
    await _fill_if_empty(page, 'input[name="applicant.emailAddress"]', CANDIDATE["email"])
    await _fill_if_empty(page, 'input[name="applicant.location.city"]', CANDIDATE["city"])


async def _step_through_indeed_form(page, resume_path: str) -> bool:
    for _ in range(10):
        await asyncio.sleep(1.5)
        await _fill_indeed_contact(page)
        await _upload_file(page, 'input[type="file"]', resume_path, timeout=3000)
        await _answer_custom_questions(page)

        submit = await page.query_selector('button[aria-label="Submit your application"]')
        if submit:
            await submit.click()
            await asyncio.sleep(3)
            return True

        cont = (
            await page.query_selector('button[aria-label="Continue to next step"]')
            or await page.query_selector('button:text("Continue")')
            or await page.query_selector('button:text("Next")')
        )
        if cont:
            await cont.click()
        else:
            break
    return False


# ── LinkedIn form flow ────────────────────────────────────────────────────────

async def _fill_linkedin_step(page, resume_path: str):
    for selector, value in [
        ('input[id*="firstName"]',   CANDIDATE["first_name"]),
        ('input[id*="lastName"]',    CANDIDATE["last_name"]),
        ('input[id*="phoneNumber"]', CANDIDATE["phone"]),
        ('input[id*="city"]',        CANDIDATE["city"]),
    ]:
        await _fill_if_empty(page, selector, value)

    await _upload_file(page, 'input[type="file"]', resume_path, timeout=3000)
    await _answer_custom_questions(page)


async def _step_through_linkedin_form(page, resume_path: str) -> bool:
    for _ in range(10):
        await _fill_linkedin_step(page, resume_path)
        await asyncio.sleep(random.uniform(1.5, 3.0))

        for selector in ['button[aria-label="Submit application"]', 'button:text("Submit application")']:
            btn = await page.query_selector(selector)
            if btn:
                await btn.click()
                await asyncio.sleep(3)
                return True

        review = await page.query_selector('button[aria-label="Review your application"]')
        if review:
            await review.click()
            await asyncio.sleep(2)
            continue

        next_btn = None
        for selector in [
            'button[aria-label="Continue to next step"]',
            'button[aria-label="Next"]',
            'button:text("Next")',
        ]:
            next_btn = await page.query_selector(selector)
            if next_btn:
                break

        if next_btn:
            await next_btn.click()
        else:
            break

    return False


# ── Greenhouse ────────────────────────────────────────────────────────────────

async def _apply_greenhouse(job: dict, resume_path: str, cl_path: str) -> bool:
    """Apply via Greenhouse ATS. Returns True on success."""
    apply_url = job["apply_url"]

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=USER_AGENT,
        )
        page = await context.new_page()
        try:
            await page.goto(apply_url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(2)

            # Standard contact fields
            await _fill_if_empty(page, 'input#first_name', CANDIDATE["first_name"])
            await _fill_if_empty(page, 'input#last_name',  CANDIDATE["last_name"])
            await _fill_if_empty(page, 'input#email',      CANDIDATE["email"])
            await _fill_if_empty(page, 'input#phone',      CANDIDATE["phone"])

            # Resume — Greenhouse uses input#resume
            await _upload_file(page, 'input#resume', resume_path)

            # Cover letter — file upload or textarea
            cl_uploaded = await _upload_file(page, 'input#cover_letter', cl_path, timeout=3000)
            if not cl_uploaded:
                try:
                    cl_area = await page.query_selector('textarea#cover_letter_text')
                    if cl_area:
                        cl_text = get_cover_letter_text(job)
                        await cl_area.fill(cl_text)
                except Exception:
                    pass

            # Optional fields
            await _fill_if_empty(page, 'input[name*="linkedin"]', CANDIDATE["linkedin"])
            await _fill_if_empty(page, 'input[name*="website"]',  CANDIDATE["website"])

            await _answer_custom_questions(page)

            # Submit
            submit = (
                await page.query_selector('input[type="submit"]')
                or await page.query_selector('button[type="submit"]')
            )
            if not submit:
                print(f"[applicator] Greenhouse: no submit button found for {job['job_id']}")
                return False

            await submit.click()
            return await _check_success(page, "greenhouse")

        except Exception as e:
            print(f"[applicator] Greenhouse error: {e}")
            raise
        finally:
            await browser.close()


# ── Lever ─────────────────────────────────────────────────────────────────────

async def _apply_lever(job: dict, resume_path: str) -> bool:
    """Apply via Lever ATS. Returns True on success."""
    apply_url = job["apply_url"]
    if "/apply" not in apply_url:
        apply_url = apply_url.rstrip("/") + "/apply"

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=USER_AGENT,
        )
        page = await context.new_page()
        try:
            await page.goto(apply_url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(2)

            # Lever uses full name, not first/last separately
            await _fill_if_empty(page, 'input[name="name"]',     CANDIDATE["full_name"])
            await _fill_if_empty(page, 'input[name="email"]',    CANDIDATE["email"])
            await _fill_if_empty(page, 'input[name="phone"]',    CANDIDATE["phone"])
            await _fill_if_empty(page, 'input[name="location"]', CANDIDATE["location"])

            # Resume — Lever has a generic file input
            await _upload_file(page, 'input[type="file"]', resume_path)

            # Cover letter — Lever uses a textarea named "comments"
            try:
                cl_area = await page.query_selector('textarea[name="comments"]')
                if cl_area:
                    cl_text = get_cover_letter_text(job)
                    await cl_area.fill(cl_text)
            except Exception:
                pass

            # Optional social fields
            await _fill_if_empty(page, 'input[name="urls[LinkedIn]"]', CANDIDATE["linkedin"])
            await _fill_if_empty(page, 'input[name="urls[Other]"]',    CANDIDATE["website"])

            await _answer_custom_questions(page)

            submit = await page.query_selector('button[type="submit"]')
            if not submit:
                print(f"[applicator] Lever: no submit button found for {job['job_id']}")
                return False

            await submit.click()
            return await _check_success(page, "lever")

        except Exception as e:
            print(f"[applicator] Lever error: {e}")
            raise
        finally:
            await browser.close()


# ── Platform-specific apply wrappers ─────────────────────────────────────────

async def _apply_indeed(job: dict, resume_path: str) -> bool:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=USER_AGENT,
        )
        page = await context.new_page()
        try:
            if not await _login_indeed(page, context):
                return False
            await page.goto(job["apply_url"], wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(2)

            easy_apply = (
                await page.query_selector('button[aria-label="Apply now"]')
                or await page.query_selector('button:text("Easily apply")')
                or await page.query_selector('a:text("Easy Apply")')
            )
            if not easy_apply:
                print(f"[applicator] No Indeed Easy Apply for {job['job_id']}")
                return False

            await easy_apply.click()
            await asyncio.sleep(2)
            return await _step_through_indeed_form(page, resume_path)

        except Exception as e:
            print(f"[applicator] Indeed error: {e}")
            raise
        finally:
            await browser.close()


async def _apply_linkedin(job: dict, resume_path: str) -> bool:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=USER_AGENT,
        )
        page = await context.new_page()
        try:
            if not await _login_linkedin(page, context):
                return False

            await page.goto(job["apply_url"], wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(random.uniform(2, 4))

            easy_apply = None
            for selector in [
                'button.jobs-apply-button',
                'button[aria-label*="Easy Apply"]',
                'button:text("Easy Apply")',
            ]:
                try:
                    easy_apply = await page.wait_for_selector(selector, timeout=5000)
                    if easy_apply:
                        break
                except PlaywrightTimeout:
                    continue

            if not easy_apply:
                print(f"[applicator] No LinkedIn Easy Apply for {job['job_id']}")
                return False

            await easy_apply.click()
            await asyncio.sleep(2)
            return await _step_through_linkedin_form(page, resume_path)

        except Exception as e:
            print(f"[applicator] LinkedIn error: {e}")
            raise
        finally:
            await browser.close()


# ── Public API ────────────────────────────────────────────────────────────────

def apply_job(job_id: str) -> bool:
    """
    Build docs then route to the correct ATS based on the job URL.
    Returns True on success.
    """
    job = get_job(job_id)
    if not job:
        return False

    # Build documents
    try:
        resume_path = build_resume(job)
        cl_path = build_cover_letter(job)
        set_documents(job_id, resume_path, cl_path)
        job = get_job(job_id)
    except Exception as e:
        set_status(job_id, "apply_failed", str(e))
        notify_apply_failed(job, f"Document generation failed: {e}")
        return False

    ats = _detect_ats(job.get("apply_url", ""))

    # Fall back to source if URL doesn't reveal the ATS
    if ats == "external":
        source = (job.get("source") or "").lower()
        if "linkedin" in source:
            ats = "linkedin"
        elif "indeed" in source:
            ats = "indeed"

    print(f"[applicator] Routing {job['job_id']} → {ats}")

    try:
        if ats == "linkedin":
            success = asyncio.run(_apply_linkedin(job, resume_path))
        elif ats == "greenhouse":
            success = asyncio.run(_apply_greenhouse(job, resume_path, cl_path))
        elif ats == "lever":
            success = asyncio.run(_apply_lever(job, resume_path))
        elif ats == "indeed":
            success = asyncio.run(_apply_indeed(job, resume_path))
        else:
            # External site with no known ATS — flag for manual apply
            set_status(job_id, "apply_failed", f"External ATS not supported: {job.get('apply_url', '')}")
            notify_apply_failed(job, "External application site — please apply manually at the link.")
            return False
    except Exception as e:
        set_status(job_id, "apply_failed", str(e))
        notify_apply_failed(job, str(e))
        return False

    if success:
        set_status(job_id, "applied")
        notify_applied(job, resume_path, cl_path)
        return True
    else:
        set_status(job_id, "apply_failed", f"{ats} Easy Apply not available on this posting.")
        notify_apply_failed(job, f"{ats.title()} Easy Apply not available — apply manually at the link.")
        return False


def generate_documents_only(job_id: str) -> tuple[str, str]:
    """Build resume + cover letter without applying. Returns (resume_path, cl_path)."""
    job = get_job(job_id)
    resume_path = build_resume(job)
    cl_path = build_cover_letter(job)
    set_documents(job_id, resume_path, cl_path)
    return resume_path, cl_path
