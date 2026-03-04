from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterable, Optional

from .config import Settings
from .models import Draw


class Database:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db_path = settings.database_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.executescript(
                """
                CREATE TABLE IF NOT EXISTS draws (
                    draw_no INTEGER PRIMARY KEY,
                    draw_date TEXT NOT NULL,
                    n1 INTEGER NOT NULL,
                    n2 INTEGER NOT NULL,
                    n3 INTEGER NOT NULL,
                    n4 INTEGER NOT NULL,
                    n5 INTEGER NOT NULL,
                    n6 INTEGER NOT NULL,
                    bonus INTEGER NOT NULL,
                    row_hash TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    game_count INTEGER NOT NULL,
                    seed INTEGER,
                    options_json TEXT,
                    evaluated_until INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS game_sets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
                    game_index INTEGER NOT NULL,
                    numbers_json TEXT NOT NULL,
                    rank_json TEXT,
                    total_hits INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS game_hits (
                    game_set_id INTEGER NOT NULL REFERENCES game_sets(id) ON DELETE CASCADE,
                    draw_no INTEGER NOT NULL REFERENCES draws(draw_no),
                    match_count INTEGER NOT NULL,
                    bonus_match INTEGER NOT NULL,
                    rank INTEGER NOT NULL,
                    PRIMARY KEY (game_set_id, draw_no)
                );

                CREATE TABLE IF NOT EXISTS sync_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL,
                    latest_draw_no INTEGER,
                    inserted_count INTEGER NOT NULL,
                    updated_count INTEGER NOT NULL,
                    skipped_count INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    source TEXT NOT NULL,
                    error_message TEXT
                );

                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_game_sets_game_id ON game_sets(game_id);
                CREATE INDEX IF NOT EXISTS idx_game_hits_game_set_id ON game_hits(game_set_id);
                CREATE INDEX IF NOT EXISTS idx_game_hits_draw_no ON game_hits(draw_no);
                """
            )

    def get_latest_draw_no(self) -> Optional[int]:
        with self.connect() as conn:
            row = conn.execute("SELECT MAX(draw_no) as latest FROM draws").fetchone()
            return row["latest"] if row and row["latest"] is not None else None

    def fetch_draws(self, start_no: int | None = None, end_no: int | None = None) -> list[Draw]:
        with self.connect() as conn:
            q = "SELECT * FROM draws"
            args: list = []
            if start_no is not None and end_no is not None:
                q += " WHERE draw_no BETWEEN ? AND ?"
                args.extend([start_no, end_no])
            elif start_no is not None:
                q += " WHERE draw_no >= ?"
                args.append(start_no)
            elif end_no is not None:
                q += " WHERE draw_no <= ?"
                args.append(end_no)
            q += " ORDER BY draw_no ASC"
            rows = conn.execute(q, args).fetchall()
            return [
                Draw(
                    draw_no=row["draw_no"],
                    draw_date=row["draw_date"],
                    numbers=[row["n1"], row["n2"], row["n3"], row["n4"], row["n5"], row["n6"]],
                    bonus=row["bonus"],
                )
                for row in rows
            ]

    def fetch_draw_numbers_map(self, draw_nos: Iterable[int]) -> dict[int, Draw]:
        draw_no_list = list(draw_nos)
        if not draw_no_list:
            return {}
        placeholders = ",".join("?" for _ in draw_no_list)
        with self.connect() as conn:
            sql = f"SELECT * FROM draws WHERE draw_no IN ({placeholders})"
            rows = conn.execute(sql, draw_no_list).fetchall()
            return {
                row["draw_no"]:
                    Draw(
                        draw_no=row["draw_no"],
                        draw_date=row["draw_date"],
                        numbers=[row["n1"], row["n2"], row["n3"], row["n4"], row["n5"], row["n6"],],
                        bonus=row["bonus"],
                    )
                for row in rows
            }

    def upsert_draws(self, draws: list[Draw]) -> tuple[int, int, int]:
        inserted = updated = skipped = 0
        if not draws:
            return inserted, updated, skipped

        # Prevent UNIQUE constraint failures when the incoming payload contains duplicated draw_no entries.
        # Keep the last payload value for each draw_no so later parser rows can override earlier rows.
        uniq_by_draw_no: dict[int, Draw] = {}
        for draw in draws:
            uniq_by_draw_no[draw.draw_no] = draw
        uniq_draws = list(uniq_by_draw_no.values())

        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as conn:
            in_clause = ",".join("?" for _ in uniq_draws)
            existing = {
                row["draw_no"]: row["row_hash"]
                for row in conn.execute(
                    f"SELECT draw_no, row_hash FROM draws WHERE draw_no IN ({in_clause})",
                    [d.draw_no for d in uniq_draws],
                )
            }

            for draw in uniq_draws:
                hash_key = draw.hash_key
                numbers = draw.numbers
                if draw.draw_no not in existing:
                    conn.execute(
                        """
                        INSERT INTO draws (draw_no, draw_date, n1, n2, n3, n4, n5, n6, bonus, row_hash, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (draw.draw_no, draw.draw_date, *numbers, draw.bonus, hash_key, now),
                    )
                    inserted += 1
                    continue

                if existing[draw.draw_no] != hash_key:
                    conn.execute(
                        """
                        UPDATE draws
                        SET draw_date=?, n1=?, n2=?, n3=?, n4=?, n5=?, n6=?, bonus=?, row_hash=?, updated_at=?
                        WHERE draw_no=?
                        """,
                        (draw.draw_date, *numbers, draw.bonus, hash_key, now, draw.draw_no),
                    )
                    updated += 1
                else:
                    skipped += 1
        return inserted, updated, skipped

    def log_sync_run(self, started_at: str, finished_at: str, latest_draw_no: int | None, inserted: int, updated: int, skipped: int, status: str, source: str, error_message: str | None = None) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO sync_runs (started_at, finished_at, latest_draw_no, inserted_count, updated_count, skipped_count, status, source, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (started_at, finished_at, latest_draw_no, inserted, updated, skipped, status, source, error_message),
            )
            return int(cur.lastrowid)

    def save_game_run(self, strategy: str, game_count: int, seed: int | None, options_json: str, evaluated_until: int, game_sets: list[dict]) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO games (created_at, strategy_name, game_count, seed, options_json, evaluated_until) VALUES (?, ?, ?, ?, ?, ?)",
                (datetime.now(timezone.utc).isoformat(), strategy, game_count, seed, options_json, evaluated_until),
            )
            game_id = int(cur.lastrowid)

            for gs in game_sets:
                gs_cur = conn.execute(
                    "INSERT INTO game_sets (game_id, game_index, numbers_json, rank_json, total_hits) VALUES (?, ?, ?, ?, ?)",
                    (game_id, gs["game_index"], json.dumps(gs["numbers"]), json.dumps(gs["rank_distribution"]), gs["total_hits"]),
                )
                game_set_id = int(gs_cur.lastrowid)
                for hit in gs["hits"]:
                    conn.execute(
                        "INSERT INTO game_hits (game_set_id, draw_no, match_count, bonus_match, rank) VALUES (?, ?, ?, ?, ?)",
                        (game_set_id, hit["draw_no"], hit["match_count"], hit["bonus_match"], hit["rank"]),
                    )
            return game_id

    def list_game_runs(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                "SELECT id, created_at, strategy_name, game_count, seed, options_json, evaluated_until FROM games ORDER BY id DESC"
            ).fetchall()

    def get_game_run_detail(self, run_id: int):
        with self.connect() as conn:
            run = conn.execute(
                "SELECT * FROM games WHERE id = ?",
                (run_id,),
            ).fetchone()
            if run is None:
                return None

            sets = conn.execute(
                "SELECT id, game_index, numbers_json, rank_json, total_hits FROM game_sets WHERE game_id = ? ORDER BY game_index ASC",
                (run_id,),
            ).fetchall()

            set_payload = [
                {
                    "game_set_id": row[0],
                    "game_index": row[1],
                    "numbers": json.loads(row[2]),
                    "rank_distribution": json.loads(row[3] or "{}"),
                    "total_hits": row[4],
                }
                for row in sets
            ]

            return {"run": run, "sets": set_payload}

    def get_game_set_hits(self, game_set_id: int):
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT draw_no, match_count, bonus_match, rank FROM game_hits WHERE game_set_id = ? ORDER BY draw_no DESC",
                (game_set_id,),
            ).fetchall()
            return [dict(row) for row in rows]
