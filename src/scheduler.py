"""APScheduler: run job search pipeline at 12pm and 6pm daily."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import config


def run_pipeline():
    """Full pipeline: scrape → score → generate docs → notify."""
    from src.scraper import run_search
    from src.scorer import score_unscored_jobs
    from src.database import get_pending_review, get_stats
    from src.notifier import notify_pending_review, notify_daily_summary

    print("[scheduler] Starting pipeline run...")

    new_count = run_search()
    print(f"[scheduler] {new_count} new jobs found")

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

    # Daily summary email
    stats = get_stats()
    try:
        notify_daily_summary(stats, new_count)
    except Exception as e:
        print(f"[scheduler] Summary email error: {e}")

    print("[scheduler] Pipeline run complete.")


def start(run_now: bool = False) -> BackgroundScheduler:
    """Start the background scheduler. Returns the scheduler instance."""
    from src.database import init_db
    init_db()

    scheduler = BackgroundScheduler()

    for hour in config.SCHEDULE_HOURS:
        scheduler.add_job(
            run_pipeline,
            CronTrigger(hour=hour, minute=0, day_of_week="mon-fri"),
            id=f"pipeline_{hour}",
            replace_existing=True,
        )

    scheduler.start()
    print(f"[scheduler] Started — runs at {config.SCHEDULE_HOURS} weekdays.")

    if run_now:
        run_pipeline()

    return scheduler
