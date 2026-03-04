from __future__ import annotations

from statistics import mean
from typing import Any

from app.models import Draw


def _percentile(sorted_values: list[int], p: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    rank = (len(sorted_values) - 1) * p
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    frac = rank - low
    return float(sorted_values[low] + ((sorted_values[high] - sorted_values[low]) * frac))


def _zone_label(number: int) -> str:
    if number <= 10:
        return "1-10"
    if number <= 20:
        return "11-20"
    if number <= 30:
        return "21-30"
    if number <= 40:
        return "31-40"
    return "41-45"


def _has_consecutive_pair(numbers: list[int]) -> bool:
    for i in range(len(numbers) - 1):
        if numbers[i + 1] - numbers[i] == 1:
            return True
    return False


def _max_same_last_digit_count(numbers: list[int]) -> int:
    counts: dict[int, int] = {}
    for n in numbers:
        digit = n % 10
        counts[digit] = counts.get(digit, 0) + 1
    return max(counts.values())


def _miss_streaks(draws: list[Draw]) -> dict[int, int]:
    latest_to_oldest = list(reversed(draws))
    out: dict[int, int] = {}
    for n in range(1, 46):
        streak = 0
        for draw in latest_to_oldest:
            if n in draw.numbers:
                break
            streak += 1
        out[n] = streak
    return out


class LotteryStatsService:
    def __init__(self) -> None:
        self._cached_latest_draw_no: int | None = None
        self._cached_payload: dict[str, Any] | None = None

    def build(self, draws: list[Draw]) -> dict[str, Any]:
        if not draws:
            return {
                "evaluated_until": None,
                "draw_count": 0,
                "number_frequency": [],
                "zone_share_pct": {},
                "sum_stats": {},
                "span_stats": {},
                "distribution": {},
                "miss_streak_top": [],
            }

        latest_draw_no = draws[-1].draw_no
        if self._cached_latest_draw_no == latest_draw_no and self._cached_payload is not None:
            return self._cached_payload

        payload = self._compute(draws)
        self._cached_latest_draw_no = latest_draw_no
        self._cached_payload = payload
        return payload

    def _compute(self, draws: list[Draw]) -> dict[str, Any]:
        frequency = {n: 0 for n in range(1, 46)}
        zone_counts = {
            "1-10": 0,
            "11-20": 0,
            "21-30": 0,
            "31-40": 0,
            "41-45": 0,
        }
        draw_sums: list[int] = []
        draw_spans: list[int] = []
        balanced_odd_even_count = 0
        balanced_high_low_count = 0
        consecutive_pair_count = 0
        last_digit_safe_count = 0

        for draw in draws:
            numbers = sorted(draw.numbers)
            draw_sums.append(sum(numbers))
            draw_spans.append(numbers[-1] - numbers[0])

            odd_count = sum(1 for n in numbers if n % 2 == 1)
            if 2 <= odd_count <= 4:
                balanced_odd_even_count += 1

            high_count = sum(1 for n in numbers if n >= 23)
            if 2 <= high_count <= 4:
                balanced_high_low_count += 1

            if _has_consecutive_pair(numbers):
                consecutive_pair_count += 1

            if _max_same_last_digit_count(numbers) <= 2:
                last_digit_safe_count += 1

            for n in numbers:
                frequency[n] += 1
                zone_counts[_zone_label(n)] += 1

        total_draws = len(draws)
        total_slots = total_draws * 6
        sorted_sums = sorted(draw_sums)
        sorted_spans = sorted(draw_spans)

        sum_stats = {
            "mean": round(float(mean(draw_sums)), 2),
            "p10": int(round(_percentile(sorted_sums, 0.10))),
            "median": int(round(_percentile(sorted_sums, 0.50))),
            "p90": int(round(_percentile(sorted_sums, 0.90))),
            "min": min(draw_sums),
            "max": max(draw_sums),
        }
        span_stats = {
            "mean": round(float(mean(draw_spans)), 2),
            "p10": int(round(_percentile(sorted_spans, 0.10))),
            "median": int(round(_percentile(sorted_spans, 0.50))),
            "p90": int(round(_percentile(sorted_spans, 0.90))),
            "min": min(draw_spans),
            "max": max(draw_spans),
        }

        number_frequency = [
            {"number": n, "count": frequency[n]}
            for n in sorted(frequency, key=lambda x: (-frequency[x], x))
        ]
        zone_share_pct = {
            zone: round((count * 100.0 / total_slots), 2) if total_slots > 0 else 0.0
            for zone, count in zone_counts.items()
        }

        miss_streak = _miss_streaks(draws)
        miss_streak_top = [
            {"number": n, "miss_draws": miss_streak[n]}
            for n in sorted(miss_streak, key=lambda x: (-miss_streak[x], x))[:10]
        ]

        distribution = {
            "odd_even_balanced_pct": round((balanced_odd_even_count * 100.0 / total_draws), 2),
            "high_low_balanced_pct": round((balanced_high_low_count * 100.0 / total_draws), 2),
            "consecutive_pair_pct": round((consecutive_pair_count * 100.0 / total_draws), 2),
            "last_digit_safe_pct": round((last_digit_safe_count * 100.0 / total_draws), 2),
        }

        return {
            "evaluated_until": draws[-1].draw_no,
            "draw_count": total_draws,
            "number_frequency": number_frequency,
            "zone_share_pct": zone_share_pct,
            "sum_stats": sum_stats,
            "span_stats": span_stats,
            "distribution": distribution,
            "miss_streak_top": miss_streak_top,
        }
