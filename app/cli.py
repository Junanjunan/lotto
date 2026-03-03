from __future__ import annotations

import argparse
import os

from app.config import Settings
from app.db import Database
from app.services.crawler import LotteryCrawler
from app.services.sync_service import SyncService


def main() -> None:
    parser = argparse.ArgumentParser(description="Lotto service utilities")
    parser.add_argument("command", choices=["sync"], help="Run tasks")
    parser.add_argument("--db", default=os.getenv("LOTTO_DB_PATH", "data/lotto.db"))
    args = parser.parse_args()

    settings = Settings(database_path=args.db)
    db = Database(settings)
    db.init_schema()

    if args.command == "sync":
        crawler = LotteryCrawler(settings)
        sync_service = SyncService(settings, db, crawler)
        out = sync_service.run_weekly_sync()
        print(
            {
                "status": out.status,
                "latest_draw_no": out.latest_draw_no,
                "inserted": out.inserted,
                "updated": out.updated,
                "skipped": out.skipped,
                "run_id": out.run_id,
                "source": out.source,
            }
        )


if __name__ == "__main__":
    main()
