from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List


@dataclass
class Draw:
    draw_no: int
    draw_date: str
    numbers: List[int]
    bonus: int

    @property
    def hash_key(self) -> str:
        payload = f"{self.draw_no}|{self.draw_date}|{','.join(map(str, self.numbers))}|{self.bonus}"
        import hashlib

        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass
class GameSet:
    index: int
    numbers: List[int]
    rank_distribution: Dict[int, int]
    hit_count: int


@dataclass
class GameRun:
    id: int
    created_at: str
    strategy: str
    game_count: int
    seed: int | None
    options_json: str
    evaluated_until: int
    game_sets: List[GameSet]


@dataclass
class SyncResult:
    status: str
    latest_draw_no: int | None
    inserted: int
    updated: int
    skipped: int
    run_id: int
    started_at: str
    finished_at: str
    source: str
