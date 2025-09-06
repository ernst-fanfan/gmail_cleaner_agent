from __future__ import annotations

import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

log = logging.getLogger(__name__)


def start_scheduler(daily_time: time, timezone: str, runner) -> None:
    """Start the APScheduler that invokes `runner` at the configured time."""
    tz = ZoneInfo(timezone)
    scheduler = BackgroundScheduler(timezone=tz)
    trigger = CronTrigger(hour=daily_time.hour, minute=daily_time.minute)
    scheduler.add_job(lambda: runner(datetime.now(tz)), trigger=trigger, id="daily-run")
    scheduler.start()
    log.info("Scheduler started for %02d:%02d %s", daily_time.hour, daily_time.minute, timezone)
    try:
        # Keep the foreground process alive
        import time as _t

        while True:
            _t.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler shutting down...")
        scheduler.shutdown()


def run_once(runner, timezone: str) -> None:
    """Convenience entry for a single immediate processing run (no schedule)."""
    tz = ZoneInfo(timezone)
    runner(datetime.now(tz))

