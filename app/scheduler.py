from __future__ import annotations

import logging
import os
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import Settings
from app.db import Database
from app.services.crawler import LotteryCrawler
from app.services.sync_service import SyncService


def run_sync_once() -> None:
    try:
        settings = Settings(database_path=os.getenv("LOTTO_DB_PATH", "data/lotto.db"))
        db = Database(settings)
        db.init_schema()
        crawler = LotteryCrawler(settings)
        sync_service = SyncService(settings, db, crawler)
        result = sync_service.run_weekly_sync()
        if result.status != "success":
            logging.error("sync failed: %s (run=%s)", result.source, result.run_id)
        else:
            logging.info("sync success: latest=%s inserted=%s updated=%s skipped=%s", result.latest_draw_no, result.inserted, result.updated, result.skipped)
    except Exception as exc:
        logging.exception("scheduler sync failed: %s", exc)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    scheduler = BlockingScheduler(timezone=ZoneInfo("Asia/Seoul"))
    trigger = CronTrigger(day_of_week="sun", hour=9, minute=0)
    scheduler.add_job(run_sync_once, trigger=trigger, id="weekly_lotto_sync", max_instances=1, replace_existing=True)

    logging.info("Starting scheduler. Weekly sync at Sunday 09:00 Asia/Seoul")
    scheduler.start()


if __name__ == "__main__":
    main()
