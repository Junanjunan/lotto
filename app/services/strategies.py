from __future__ import annotations

import random
from typing import Callable, Mapping


def generate_low_overlap_random(game_count: int, seed: int | None = None) -> list[list[int]]:
    if game_count <= 0:
        return []

    rnd = random.Random(seed)
    numbers = list(range(1, 46))

    total_slots = game_count * 6
    games: list[list[int]] = []

    if total_slots <= 45:
        rnd.shuffle(numbers)
        selected = numbers[:total_slots]
        for i in range(game_count):
            games.append(sorted(selected[i * 6 : (i + 1) * 6]))
        return games

    usage = {n: 0 for n in range(1, 46)}
    for _ in range(game_count):
        ordered = sorted(
            range(1, 46),
            key=lambda n: (usage[n], rnd.random()),
        )
        game = sorted(ordered[:6])
        games.append(game)
        for n in game:
            usage[n] += 1

    return games


def generate_uniform_random(game_count: int, seed: int | None = None) -> list[list[int]]:
    if game_count <= 0:
        return []

    rnd = random.Random(seed)
    games = []
    all_nums = list(range(1, 46))

    for _ in range(game_count):
        games.append(sorted(rnd.sample(all_nums, 6)))

    return games


Strategy = Callable[[int, int | None], list[list[int]]]

STRATEGIES: dict[str, Strategy] = {
    "low_overlap_random": generate_low_overlap_random,
    "uniform_random": generate_uniform_random,
}

STRATEGY_LABELS: dict[str, str] = {
    "low_overlap_random": "중복 최소 랜덤",
    "uniform_random": "균등 랜덤",
}

STRATEGY_DESCRIPTIONS: dict[str, str] = {
    "low_overlap_random": "여러 게임의 숫자 중복을 최대한 줄여 고르게 분산합니다.",
    "uniform_random": "각 게임을 완전 무작위로 생성하는 기본 랜덤 방식입니다.",
}

DEFAULT_STRATEGY_OPTIONS: dict[str, bool] = {
    "avoid_birthday_bias": False,
    "include_consecutive_pair": False,
    "avoid_popular_numbers": False,
    "balanced_odd_even": False,
    "balanced_high_low": False,
    "sum_band_100_170": False,
    "avoid_same_last_digit_cluster": False,
    "avoid_arithmetic_sequence": False,
}

STRATEGY_OPTION_LABELS: dict[str, str] = {
    "avoid_birthday_bias": "생일 편향 회피(32~45 비중 강화)",
    "include_consecutive_pair": "연속 번호 1쌍 이상 포함",
    "avoid_popular_numbers": "인기 숫자(7) 제외",
    "balanced_odd_even": "홀짝 균형(2:4~4:2)",
    "balanced_high_low": "고저 균형(1~22 / 23~45)",
    "sum_band_100_170": "번호합 100~170 구간",
    "avoid_same_last_digit_cluster": "끝수(일의 자리) 쏠림 방지",
    "avoid_arithmetic_sequence": "등차수열 패턴 제외",
}

_POPULAR_NUMBERS = {7}


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "t", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "f", "no", "n", "off", ""}:
            return False
    return bool(value)


def normalize_strategy_options(options: Mapping[str, object] | None) -> dict[str, bool]:
    normalized = dict(DEFAULT_STRATEGY_OPTIONS)
    if not options:
        return normalized
    for key in normalized:
        normalized[key] = _coerce_bool(options.get(key, False))
    return normalized


def _has_consecutive_pair(numbers: list[int]) -> bool:
    return any((numbers[i + 1] - numbers[i]) == 1 for i in range(len(numbers) - 1))


def _is_balanced_odd_even(numbers: list[int]) -> bool:
    odd_count = sum(1 for n in numbers if n % 2 == 1)
    return 2 <= odd_count <= 4


def _is_balanced_high_low(numbers: list[int]) -> bool:
    high_count = sum(1 for n in numbers if n >= 23)
    return 2 <= high_count <= 4


def _is_in_sum_band(numbers: list[int], min_sum: int, max_sum: int) -> bool:
    total = sum(numbers)
    return min_sum <= total <= max_sum


def _max_same_last_digit_count(numbers: list[int]) -> int:
    counts: dict[int, int] = {}
    for n in numbers:
        last_digit = n % 10
        counts[last_digit] = counts.get(last_digit, 0) + 1
    return max(counts.values())


def _is_full_arithmetic_progression(numbers: list[int]) -> bool:
    if len(numbers) < 3:
        return False
    step = numbers[1] - numbers[0]
    for i in range(2, len(numbers)):
        if numbers[i] - numbers[i - 1] != step:
            return False
    return True


def _passes_constraints(numbers: list[int], options: dict[str, bool]) -> bool:
    if options["avoid_birthday_bias"]:
        high_band_count = sum(1 for n in numbers if n >= 32)
        if high_band_count < 3:
            return False

    if options["include_consecutive_pair"] and not _has_consecutive_pair(numbers):
        return False

    if options["avoid_popular_numbers"] and any(n in _POPULAR_NUMBERS for n in numbers):
        return False

    if options["balanced_odd_even"] and not _is_balanced_odd_even(numbers):
        return False

    if options["balanced_high_low"] and not _is_balanced_high_low(numbers):
        return False

    if options["sum_band_100_170"] and not _is_in_sum_band(numbers, 100, 170):
        return False

    if options["avoid_same_last_digit_cluster"] and _max_same_last_digit_count(numbers) > 2:
        return False

    if options["avoid_arithmetic_sequence"] and _is_full_arithmetic_progression(numbers):
        return False

    return True


def _candidate_pool(options: dict[str, bool]) -> list[int]:
    if options["avoid_popular_numbers"]:
        return [n for n in range(1, 46) if n not in _POPULAR_NUMBERS]
    return list(range(1, 46))


def _weighted_sample_without_replacement(
    items: list[int],
    weights: list[float],
    k: int,
    rnd: random.Random,
) -> list[int]:
    chosen: list[int] = []
    available_items = list(items)
    available_weights = list(weights)
    for _ in range(k):
        total = sum(available_weights)
        if total <= 0:
            idx = rnd.randrange(len(available_items))
        else:
            pick = rnd.random() * total
            cumulative = 0.0
            idx = len(available_weights) - 1
            for i, weight in enumerate(available_weights):
                cumulative += weight
                if pick <= cumulative:
                    idx = i
                    break
        chosen.append(available_items.pop(idx))
        available_weights.pop(idx)
    return chosen


def _generate_constrained(
    game_count: int,
    seed: int | None,
    options: dict[str, bool],
    prefer_low_overlap: bool,
) -> list[list[int]]:
    if game_count <= 0:
        return []

    pool = _candidate_pool(options)
    if len(pool) < 6:
        raise ValueError("Selected options leave fewer than 6 usable numbers.")

    rnd = random.Random(seed)
    usage = {n: 0 for n in range(1, 46)}
    games: list[list[int]] = []
    attempts_per_game = 1500

    for _ in range(game_count):
        selected: list[int] | None = None
        for _ in range(attempts_per_game):
            if prefer_low_overlap:
                weights = [1.0 / (1.0 + usage[n]) for n in pool]
                candidate = _weighted_sample_without_replacement(pool, weights, 6, rnd)
            else:
                candidate = rnd.sample(pool, 6)

            candidate = sorted(candidate)
            if _passes_constraints(candidate, options):
                selected = candidate
                break

        if selected is None:
            raise ValueError("Unable to satisfy strategy options with current settings.")

        games.append(selected)
        for n in selected:
            usage[n] += 1

    return games


def generate_games_with_options(
    strategy_name: str,
    game_count: int,
    seed: int | None = None,
    options: Mapping[str, object] | None = None,
) -> tuple[list[list[int]], dict[str, bool]]:
    strategy = STRATEGIES.get(strategy_name)
    if strategy is None:
        raise KeyError(strategy_name)

    normalized = normalize_strategy_options(options)
    if not any(normalized.values()):
        return strategy(game_count, seed), normalized

    if strategy_name == "low_overlap_random":
        return _generate_constrained(game_count, seed, normalized, prefer_low_overlap=True), normalized

    return _generate_constrained(game_count, seed, normalized, prefer_low_overlap=False), normalized
