"""
Background scheduler process.
Run this alongside the Streamlit app:

  Terminal 1:  python run.py          # background scheduler
  Terminal 2:  streamlit run app.py   # UI

Or to test the pipeline immediately:
  python run.py --now
"""
import sys
import time

from src.database import init_db
from src.scheduler import start

if __name__ == "__main__":
    init_db()
    run_now = "--now" in sys.argv
    scheduler = start(run_now=run_now)
    print("Scheduler running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.shutdown()
        print("Scheduler stopped.")
