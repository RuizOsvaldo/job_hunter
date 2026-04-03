"""
One-time manual login helper.
Run this once per platform to save session cookies.
After this, the automated apply flow uses saved cookies and skips login entirely.

Usage:
    source venv/bin/activate

    # Save Indeed cookies
    python scripts/save_cookies.py indeed

    # Save LinkedIn cookies
    python scripts/save_cookies.py linkedin
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright

COOKIES = {
    "indeed":   "data/indeed_cookies.json",
    "linkedin": "data/linkedin_cookies.json",
}

URLS = {
    "indeed":   "https://secure.indeed.com/auth",
    "linkedin": "https://www.linkedin.com/login",
}

SUCCESS_PATTERNS = {
    "indeed":   ["indeed.com/account", "indeed.com/jobs", "indeed.com/myjobs"],
    "linkedin": ["linkedin.com/feed", "linkedin.com/jobs"],
}


async def run(platform: str):
    cookies_path = COOKIES[platform]
    url = URLS[platform]
    success = SUCCESS_PATTERNS[platform]

    Path(cookies_path).parent.mkdir(parents=True, exist_ok=True)

    print(f"\n[save_cookies] Opening {platform} login page...")
    print("[save_cookies] Log in normally — complete any MFA when prompted.")
    print("[save_cookies] The browser will close automatically once you're logged in.\n")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        await page.goto(url)

        # Wait until the user is logged in (URL changes to a logged-in page)
        print("[save_cookies] Waiting for successful login...")
        while True:
            await asyncio.sleep(2)
            current_url = page.url
            if any(pattern in current_url for pattern in success):
                break
            # Also check if we're on a page that looks post-login
            if platform == "linkedin" and "checkpoint" not in current_url and "login" not in current_url:
                if "linkedin.com/" in current_url:
                    break

        cookies = await context.cookies()
        with open(cookies_path, "w") as f:
            json.dump(cookies, f)

        print(f"[save_cookies] Cookies saved to {cookies_path}")
        print(f"[save_cookies] Done — {platform} login will be skipped in future runs.")
        await browser.close()


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COOKIES:
        print("Usage: python scripts/save_cookies.py [indeed|linkedin]")
        sys.exit(1)

    asyncio.run(run(sys.argv[1]))
