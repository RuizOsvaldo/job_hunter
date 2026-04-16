"""APScheduler: run job search pipeline at 12pm and 6pm daily."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import config


def _run_gov_scrapers() -> int:
    """Run all government scrapers and upsert results. Returns count of new jobs inserted."""
    from src.database import upsert_job
    from scrapers.usajobs import scrape_usajobs
    from scrapers.county_san_diego import scrape_county_san_diego
    from scrapers.city_san_diego import scrape_city_san_diego
    from scrapers.calcareers import scrape_calcareers

    gov_scrapers = [
        ("usajobs", scrape_usajobs),
        ("county_sd", scrape_county_san_diego),
        ("city_sd", scrape_city_san_diego),
        ("calcareers", scrape_calcareers),
    ]

    total_new = 0
    for name, scraper_fn in gov_scrapers:
        try:
            jobs = scraper_fn()
            inserted = sum(1 for j in jobs if upsert_job(j))
            total_new += inserted
            print(f"[scheduler] {name}: {len(jobs)} found, {inserted} new")
        except Exception as exc:
            print(f"[scheduler] WARNING: {name} scraper failed — {exc}")

    return total_new


def run_pipeline():
    """Full pipeline: scrape → score → generate docs → notify."""
    from src.scraper import run_search
    from src.scorer import score_unscored_jobs
    from src.database import get_pending_review, get_stats, get_todays_top_matches
    from src.notifier import (
        notify_pending_review, notify_daily_summary, notify_morning_digest
    )

    print("[scheduler] Starting pipeline run...")

    new_count = run_search()
    print(f"[scheduler] {new_count} new jobs found (jobspy)")

    gov_count = _run_gov_scrapers()
    new_count += gov_count
    print(f"[scheduler] {gov_count} new jobs found (government scrapers)")

    scored = score_unscored_jobs()
    print(f"[scheduler] {scored} jobs scored")

    # Notify about each high-scoring job that needs review
    pending = get_pending_review()
    for job in pending:
        # Only notify if documents not yet generated
        if not job.get("resume_path"):
            try:
                notify_pending_review(job)
            except Exception as e:
                print(f"[scheduler] Notify error for {job['job_id']}: {e}")

    # Morning digest — top 10 newly scraped tech jobs from today's run
    if config.DIGEST_ENABLED:
        try:
            todays = get_todays_top_matches(limit=10)
            notify_morning_digest(todays)
            print(f"[scheduler] Morning digest sent ({len(todays)} jobs).")
        except Exception as e:
            print(f"[scheduler] Morning digest failed: {e}")

    # Daily summary email
    stats = get_stats()
    try:
        notify_daily_summary(stats, new_count)
    except Exception as e:
        print(f"[scheduler] Summary email error: {e}")

    print("[scheduler] Pipeline run complete.")


def run_weekly_summary():
    """Send the weekly summary email (Sundays 10am)."""
    from src.database import get_weekly_stats
    from src.notifier import notify_weekly_summary
    try:
        stats = get_weekly_stats()
        notify_weekly_summary(stats)
        print("[scheduler] Weekly summary sent.")
    except Exception as exc:
        print(f"[scheduler] Weekly summary failed — {exc}")


def start(run_now: bool = False) -> BackgroundScheduler:
    """Start the background scheduler. Returns the scheduler instance."""
    from src.database import init_db
    init_db()

    scheduler = BackgroundScheduler(timezone="America/Los_Angeles")

    for hour in config.SCHEDULE_HOURS:
        scheduler.add_job(
            run_pipeline,
            CronTrigger(hour=hour, minute=0, day_of_week="mon-fri"),
            id=f"pipeline_{hour}",
            replace_existing=True,
        )

    # Weekly summary — Sundays at 10am
    scheduler.add_job(
        run_weekly_summary,
        CronTrigger(day_of_week="sun", hour=10, minute=0),
        id="weekly_summary",
        replace_existing=True,
    )

    scheduler.start()
    print(f"[scheduler] Started — pipeline at {config.SCHEDULE_HOURS} weekdays, weekly summary Sundays 10am.")

    if run_now:
        run_pipeline()

    return scheduler
