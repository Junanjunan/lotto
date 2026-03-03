from __future__ import annotations

from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator


class SyncResponse(BaseModel):
    status: str
    latest_draw_no: int
    inserted: int
    updated: int
    skipped: int
    run_id: int
    source: str


class StrategyOptions(BaseModel):
    avoid_birthday_bias: bool = False
    include_consecutive_pair: bool = False
    avoid_popular_numbers: bool = False
    balanced_odd_even: bool = False
    balanced_high_low: bool = False
    sum_band_100_170: bool = False
    avoid_same_last_digit_cluster: bool = False
    avoid_arithmetic_sequence: bool = False


class GenerateRequest(BaseModel):
    game_count: int = Field(..., ge=1, description="Number of game sets to generate")
    strategy: str = "low_overlap_random"
    seed: Optional[int] = None
    options: StrategyOptions = Field(default_factory=StrategyOptions)


class GameCreateResponse(BaseModel):
    run_id: int
    created_at: str
    strategy: str
    strategy_options: StrategyOptions
    game_count: int
    seed: Optional[int]
    evaluated_until: int
    games: list[dict]


class NumberCheckRequest(BaseModel):
    numbers: list[int] = Field(..., min_length=6, max_length=6)

    @field_validator("numbers")
    @classmethod
    def validate_numbers(cls, value: list[int]) -> list[int]:
        if len(set(value)) != 6:
            raise ValueError("numbers must contain 6 unique values")
        if any(n < 1 or n > 45 for n in value):
            raise ValueError("numbers must be between 1 and 45")
        return sorted(value)


class NumberCheckHit(BaseModel):
    draw_no: int
    draw_date: str
    rank: int
    match_count: int
    bonus_match: bool
    draw_numbers: list[int]
    bonus: int
    matched_numbers: list[int]


class NumberCheckResponse(BaseModel):
    numbers: list[int]
    total_draws: int
    evaluated_until: int
    rank_distribution: dict[int, int]
    total_hits: int
    hits: list[NumberCheckHit]
