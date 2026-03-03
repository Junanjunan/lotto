from __future__ import annotations

from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class SyncResponse(BaseModel):
    status: str
    latest_draw_no: int
    inserted: int
    updated: int
    skipped: int
    run_id: int
    source: str


class GenerateRequest(BaseModel):
    game_count: int = Field(..., ge=1, description="Number of game sets to generate")
    strategy: str = "low_overlap_random"
    seed: Optional[int] = None


class GameCreateResponse(BaseModel):
    run_id: int
    created_at: str
    strategy: str
    game_count: int
    seed: Optional[int]
    evaluated_until: int
    games: list[dict]
