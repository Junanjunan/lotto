from __future__ import annotations

import tempfile
import unittest

from app.config import Settings
from app.db import Database
from app.models import Draw


class DatabaseUpsertTests(unittest.TestCase):
    def test_upsert_draws_keeps_last_duplicate_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Settings(database_path=f"{tmpdir}/lotto.db"))
            db.init_schema()

            inserted, updated, skipped = db.upsert_draws(
                [
                    Draw(draw_no=100, draw_date="2024-01-01", numbers=[1, 2, 3, 4, 5, 6], bonus=7),
                    Draw(draw_no=100, draw_date="2024-01-02", numbers=[10, 11, 12, 13, 14, 15], bonus=16),
                ]
            )

            self.assertEqual(inserted, 1)
            self.assertEqual(updated, 0)
            self.assertEqual(skipped, 0)

            saved = db.fetch_draws(start_no=100, end_no=100)
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0].draw_date, "2024-01-02")
            self.assertEqual(saved[0].numbers, [10, 11, 12, 13, 14, 15])
            self.assertEqual(saved[0].bonus, 16)

    def test_upsert_draws_deduplicates_before_querying_existing_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Settings(database_path=f"{tmpdir}/lotto.db"))
            db.init_schema()

            db.upsert_draws(
                [
                    Draw(draw_no=200, draw_date="2024-02-01", numbers=[1, 2, 3, 4, 5, 6], bonus=7),
                ]
            )
            inserted, updated, skipped = db.upsert_draws(
                [
                    Draw(draw_no=200, draw_date="2024-02-01", numbers=[1, 2, 3, 4, 5, 6], bonus=7),
                    Draw(draw_no=200, draw_date="2024-02-01", numbers=[1, 2, 3, 4, 5, 6], bonus=7),
                ]
            )

            self.assertEqual(inserted, 0)
            self.assertEqual(updated, 0)
            self.assertEqual(skipped, 1)


if __name__ == "__main__":
    unittest.main()
