from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.config import Settings
from app.services.crawler import LotteryCrawler
from app.db import Database
from app.services.excel_parser import parse_excel_draws
from app.models import Draw


@dataclass
class SyncOutput:
    inserted: int
    updated: int
    skipped: int
    latest_draw_no: int
    run_id: int
    source: str
    status: str


class SyncService:
    def __init__(self, settings: Settings, database: Database, crawler: LotteryCrawler):
        self.settings = settings
        self.db = database
        self.crawler = crawler

    def _build_records_from_json(self, payload: dict) -> list[Draw]:
        data = payload.get("data", {}).get("list", [])
        out: list[Draw] = []
        for row in data:
            try:
                draw_no = int(row["ltEpsd"])
                main = [
                    int(row["tm1WnNo"]),
                    int(row["tm2WnNo"]),
                    int(row["tm3WnNo"]),
                    int(row["tm4WnNo"]),
                    int(row["tm5WnNo"]),
                    int(row["tm6WnNo"]),
                ]
                bonus = int(row["bnsWnNo"])
                date = row.get("ltRflYmd", "")
                out.append(Draw(draw_no=draw_no, draw_date=str(date), numbers=sorted(main), bonus=bonus))
            except (TypeError, KeyError, ValueError):
                continue
        return out

    def _build_json_map(self, payload: dict) -> dict[int, Draw]:
        out = {}
        for row in payload.get("data", {}).get("list", []):
            try:
                draw_no = int(row["ltEpsd"])
                main = [
                    int(row["tm1WnNo"]),
                    int(row["tm2WnNo"]),
                    int(row["tm3WnNo"]),
                    int(row["tm4WnNo"]),
                    int(row["tm5WnNo"]),
                    int(row["tm6WnNo"]),
                ]
                bonus = int(row["bnsWnNo"])
                date = row.get("ltRflYmd", "")
                out[draw_no] = Draw(draw_no=draw_no, draw_date=str(date), numbers=sorted(main), bonus=bonus)
            except (TypeError, KeyError, ValueError):
                continue
        return out

    def run_weekly_sync(self) -> SyncOutput:
        started_at = datetime.now(timezone.utc).isoformat()
        inserted = updated = skipped = 0
        latest = None
        status = "success"
        source = "excel"
        run_id = -1
        err_msg = None

        try:
            latest = self.crawler.get_latest_draw_no()
            records: list[Draw] = []

            # Always download all rounds from 1 to latest
            try:
                content, _ = self.crawler.download_excel(1, latest)
                records = parse_excel_draws(content)
            except Exception as exc:
                source = "api_fallback"
                err_msg = str(exc)
                payload = self.crawler.fetch_draws_json(1, latest)
                records = self._build_records_from_json(payload)

            # merge metadata from API payload for stable draw date (and to fill potential missing rounds)
            try:
                payload = self.crawler.fetch_draws_json(1, latest)
                json_map = self._build_json_map(payload)
                merged: dict[int, Draw] = {r.draw_no: r for r in records}
                for r in merged.values():
                    json_row = json_map.get(r.draw_no)
                    if json_row and not r.draw_date:
                        r.draw_date = json_row.draw_date
                for draw_no in range(1, latest + 1):
                    if draw_no not in merged and draw_no in json_map:
                        merged[draw_no] = json_map[draw_no]
                records = sorted(merged.values(), key=lambda d: d.draw_no)

                # if Excel missed some rounds, prefer API row data completely if it fills the gap.
                if len(records) != latest:
                    missing = [n for n in range(1, latest + 1) if n not in merged]
                    if missing:
                        source = "api_fill"
                        for missing_no in missing:
                            if missing_no in json_map:
                                records.append(json_map[missing_no])
                        records = sorted({d.draw_no: d for d in records}.values(), key=lambda d: d.draw_no)
            except Exception:
                pass

            # fallback safety
            if not records:
                if err_msg:
                    raise RuntimeError(f"sync failed after fallback: {err_msg}")
                raise RuntimeError("no records found")

            inserted, updated, skipped = self.db.upsert_draws(records)
            latest = max(d.draw_no for d in records)
            status = "success"

        except Exception as exc:
            status = "failed"
            err_msg = str(exc)

        finished_at = datetime.now(timezone.utc).isoformat()
        run_id = self.db.log_sync_run(
            started_at,
            finished_at,
            latest,
            inserted,
            updated,
            skipped,
            status,
            source,
            err_msg,
        )

        return SyncOutput(
            inserted=inserted,
            updated=updated,
            skipped=skipped,
            latest_draw_no=latest or 0,
            run_id=run_id,
            source=source,
            status=status,
        )
