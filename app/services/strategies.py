from __future__ import annotations

import random
from collections import Counter
from typing import Callable, Mapping, Sequence

from app.models import Draw

Strategy = Callable[[int, int | None], list[list[int]]]

_POPULAR_NUMBERS = {7}
_PAIR_MODES = {"any", "none", "one_or_two"}


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
    games: list[list[int]] = []
    all_nums = list(range(1, 46))
    for _ in range(game_count):
        games.append(sorted(rnd.sample(all_nums, 6)))
    return games


STRATEGY_LABELS: dict[str, str] = {
    "low_overlap_random": "중복 최소 랜덤",
    "uniform_random": "균등 랜덤",
    "balanced_quickpick": "균형 퀵픽",
    "zone_spread": "구간 분산",
    "pair_tuner": "연속수 튜너",
    "sum_span_guard": "합/스팬 가드",
    "hot_focus": "최근 강세 중심",
    "cold_focus": "미출현 중심",
    "hot_cold_mix": "강세+미출현 혼합",
    "portfolio_diversify_v2": "중복 최소 강화",
}

STRATEGY_DESCRIPTIONS: dict[str, str] = {
    "low_overlap_random": "여러 게임의 숫자 중복을 최대한 줄여 고르게 분산합니다.",
    "uniform_random": "각 게임을 완전 무작위로 생성하는 기본 랜덤 방식입니다.",
    "balanced_quickpick": "홀짝/고저/합계/스팬/끝수 제약을 적용한 설명 가능한 기본 전략입니다.",
    "zone_spread": "1~45 번호대가 여러 구간에 퍼지도록 분산을 강제합니다.",
    "pair_tuner": "연속 번호 쌍 개수를 제어해 취향을 반영합니다.",
    "sum_span_guard": "극단적 합계·스팬 조합을 줄이는 안정형 전략입니다.",
    "hot_focus": "최근 N회차 빈도에 가중치를 두는 전략입니다.",
    "cold_focus": "오래 미출현한 번호에 가중치를 두는 전략입니다.",
    "hot_cold_mix": "강세 번호와 미출현 번호를 혼합해 편향을 완화합니다.",
    "portfolio_diversify_v2": "게임 간 중복 페널티를 강화한 포트폴리오 분산 전략입니다.",
}

STRATEGY_DIFFICULTIES: dict[str, str] = {
    "low_overlap_random": "easy",
    "uniform_random": "easy",
    "balanced_quickpick": "easy",
    "zone_spread": "easy",
    "pair_tuner": "easy",
    "sum_span_guard": "easy",
    "hot_focus": "normal",
    "cold_focus": "normal",
    "hot_cold_mix": "normal",
    "portfolio_diversify_v2": "normal",
}

STRATEGY_CATALOG: list[dict[str, str]] = [
    {
        "id": strategy_id,
        "label": STRATEGY_LABELS[strategy_id],
        "description": STRATEGY_DESCRIPTIONS[strategy_id],
        "difficulty": STRATEGY_DIFFICULTIES.get(strategy_id, "easy"),
    }
    for strategy_id in STRATEGY_LABELS
]

DEFAULT_STRATEGY_OPTIONS: dict[str, object] = {
    "avoid_birthday_bias": False,
    "include_consecutive_pair": False,
    "avoid_popular_numbers": False,
    "balanced_odd_even": False,
    "balanced_high_low": False,
    "sum_band_100_170": False,
    "avoid_same_last_digit_cluster": False,
    "avoid_arithmetic_sequence": False,
    "zone_coverage_min": 0,
    "consecutive_pair_mode": "any",
    "consecutive_pair_max": None,
    "sum_min": None,
    "sum_max": None,
    "span_min": None,
    "span_max": None,
    "hot_cold_window": 30,
    "hot_cold_alpha": 1.4,
    "hot_mix_ratio": 0.5,
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
    "zone_coverage_min": "구간 최소 커버(1~10/11~20/21~30/31~40/41~45)",
    "consecutive_pair_mode": "연속쌍 모드(any/none/one_or_two)",
    "consecutive_pair_max": "연속쌍 최대 개수",
    "sum_min": "번호합 최소값",
    "sum_max": "번호합 최대값",
    "span_min": "스팬 최소값(max-min)",
    "span_max": "스팬 최대값(max-min)",
    "hot_cold_window": "강세/미출현 계산 윈도우 회차",
    "hot_cold_alpha": "강세/미출현 가중치 강도",
    "hot_mix_ratio": "혼합 전략의 hot 비율(0~1)",
}

STRATEGY_OPTION_SCHEMA: dict[str, dict[str, object]] = {
    "avoid_birthday_bias": {"type": "bool", "default": False},
    "include_consecutive_pair": {"type": "bool", "default": False},
    "avoid_popular_numbers": {"type": "bool", "default": False},
    "balanced_odd_even": {"type": "bool", "default": False},
    "balanced_high_low": {"type": "bool", "default": False},
    "sum_band_100_170": {"type": "bool", "default": False},
    "avoid_same_last_digit_cluster": {"type": "bool", "default": False},
    "avoid_arithmetic_sequence": {"type": "bool", "default": False},
    "zone_coverage_min": {"type": "int", "min": 0, "max": 5, "default": 0},
    "consecutive_pair_mode": {"type": "enum", "values": ["any", "none", "one_or_two"], "default": "any"},
    "consecutive_pair_max": {"type": "int_or_null", "min": 0, "max": 5, "default": None},
    "sum_min": {"type": "int_or_null", "min": 21, "max": 260, "default": None},
    "sum_max": {"type": "int_or_null", "min": 21, "max": 260, "default": None},
    "span_min": {"type": "int_or_null", "min": 0, "max": 44, "default": None},
    "span_max": {"type": "int_or_null", "min": 0, "max": 44, "default": None},
    "hot_cold_window": {"type": "int", "min": 5, "max": 260, "default": 30},
    "hot_cold_alpha": {"type": "float", "min": 0.1, "max": 5.0, "default": 1.4},
    "hot_mix_ratio": {"type": "float", "min": 0.0, "max": 1.0, "default": 0.5},
}

STRATEGY_RUNTIME_CONFIG: dict[str, dict[str, object]] = {
    "low_overlap_random": {
        "prefer_low_overlap": True,
        "usage_power": 1.0,
        "weight_mode": "none",
        "defaults": {},
    },
    "uniform_random": {
        "prefer_low_overlap": False,
        "usage_power": 1.0,
        "weight_mode": "none",
        "defaults": {},
    },
    "balanced_quickpick": {
        "prefer_low_overlap": True,
        "usage_power": 1.1,
        "weight_mode": "none",
        "defaults": {
            "balanced_odd_even": True,
            "balanced_high_low": True,
            "sum_min": 105,
            "sum_max": 175,
            "span_min": 22,
            "span_max": 42,
            "avoid_same_last_digit_cluster": True,
            "consecutive_pair_max": 2,
        },
    },
    "zone_spread": {
        "prefer_low_overlap": False,
        "usage_power": 1.0,
        "weight_mode": "none",
        "defaults": {
            "zone_coverage_min": 4,
        },
    },
    "pair_tuner": {
        "prefer_low_overlap": False,
        "usage_power": 1.0,
        "weight_mode": "none",
        "defaults": {
            "consecutive_pair_mode": "one_or_two",
        },
    },
    "sum_span_guard": {
        "prefer_low_overlap": False,
        "usage_power": 1.0,
        "weight_mode": "none",
        "defaults": {
            "sum_min": 105,
            "sum_max": 175,
            "span_min": 22,
            "span_max": 42,
        },
    },
    "hot_focus": {
        "prefer_low_overlap": False,
        "usage_power": 1.0,
        "weight_mode": "hot",
        "defaults": {
            "hot_cold_window": 30,
            "hot_cold_alpha": 1.4,
        },
    },
    "cold_focus": {
        "prefer_low_overlap": False,
        "usage_power": 1.0,
        "weight_mode": "cold",
        "defaults": {
            "hot_cold_window": 30,
            "hot_cold_alpha": 1.4,
        },
    },
    "hot_cold_mix": {
        "prefer_low_overlap": False,
        "usage_power": 1.0,
        "weight_mode": "hot_cold_mix",
        "defaults": {
            "hot_cold_window": 30,
            "hot_cold_alpha": 1.4,
            "hot_mix_ratio": 0.5,
        },
    },
    "portfolio_diversify_v2": {
        "prefer_low_overlap": True,
        "usage_power": 1.8,
        "weight_mode": "none",
        "defaults": {
            "balanced_odd_even": True,
            "balanced_high_low": True,
        },
    },
}


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


def _coerce_int(
    value: object,
    default: int,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        parsed = default
    if min_value is not None and parsed < min_value:
        parsed = min_value
    if max_value is not None and parsed > max_value:
        parsed = max_value
    return parsed


def _coerce_optional_int(
    value: object,
    default: int | None,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int | None:
    if value is None:
        return default
    if isinstance(value, str) and value.strip() == "":
        return default
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    if min_value is not None and parsed < min_value:
        parsed = min_value
    if max_value is not None and parsed > max_value:
        parsed = max_value
    return parsed


def _coerce_float(
    value: object,
    default: float,
    *,
    min_value: float | None = None,
    max_value: float | None = None,
) -> float:
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        parsed = default
    if min_value is not None and parsed < min_value:
        parsed = min_value
    if max_value is not None and parsed > max_value:
        parsed = max_value
    return parsed


def normalize_strategy_options(options: Mapping[str, object] | None) -> dict[str, object]:
    normalized: dict[str, object] = dict(DEFAULT_STRATEGY_OPTIONS)
    if not options:
        return normalized

    bool_keys = [
        "avoid_birthday_bias",
        "include_consecutive_pair",
        "avoid_popular_numbers",
        "balanced_odd_even",
        "balanced_high_low",
        "sum_band_100_170",
        "avoid_same_last_digit_cluster",
        "avoid_arithmetic_sequence",
    ]
    for key in bool_keys:
        normalized[key] = _coerce_bool(options.get(key, normalized[key]))

    normalized["zone_coverage_min"] = _coerce_int(options.get("zone_coverage_min"), 0, min_value=0, max_value=5)

    pair_mode_raw = options.get("consecutive_pair_mode", normalized["consecutive_pair_mode"])
    pair_mode = str(pair_mode_raw).strip().lower() if pair_mode_raw is not None else "any"
    if pair_mode not in _PAIR_MODES:
        pair_mode = "any"
    normalized["consecutive_pair_mode"] = pair_mode

    normalized["consecutive_pair_max"] = _coerce_optional_int(
        options.get("consecutive_pair_max"),
        None,
        min_value=0,
        max_value=5,
    )
    normalized["sum_min"] = _coerce_optional_int(options.get("sum_min"), None, min_value=21, max_value=260)
    normalized["sum_max"] = _coerce_optional_int(options.get("sum_max"), None, min_value=21, max_value=260)
    normalized["span_min"] = _coerce_optional_int(options.get("span_min"), None, min_value=0, max_value=44)
    normalized["span_max"] = _coerce_optional_int(options.get("span_max"), None, min_value=0, max_value=44)
    normalized["hot_cold_window"] = _coerce_int(options.get("hot_cold_window"), 30, min_value=5, max_value=260)
    normalized["hot_cold_alpha"] = _coerce_float(options.get("hot_cold_alpha"), 1.4, min_value=0.1, max_value=5.0)
    normalized["hot_mix_ratio"] = _coerce_float(options.get("hot_mix_ratio"), 0.5, min_value=0.0, max_value=1.0)
    return normalized


def _validate_option_ranges(options: Mapping[str, object]) -> None:
    sum_min = options.get("sum_min")
    sum_max = options.get("sum_max")
    span_min = options.get("span_min")
    span_max = options.get("span_max")
    if sum_min is not None and sum_max is not None and int(sum_min) > int(sum_max):
        raise ValueError("sum_min must be less than or equal to sum_max.")
    if span_min is not None and span_max is not None and int(span_min) > int(span_max):
        raise ValueError("span_min must be less than or equal to span_max.")


def _consecutive_pair_count(numbers: list[int]) -> int:
    count = 0
    for i in range(len(numbers) - 1):
        if numbers[i + 1] - numbers[i] == 1:
            count += 1
    return count


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


def _zone_index(number: int) -> int:
    if number <= 10:
        return 0
    if number <= 20:
        return 1
    if number <= 30:
        return 2
    if number <= 40:
        return 3
    return 4


def _zone_coverage_count(numbers: list[int]) -> int:
    return len({_zone_index(n) for n in numbers})


def _is_full_arithmetic_progression(numbers: list[int]) -> bool:
    if len(numbers) < 3:
        return False
    step = numbers[1] - numbers[0]
    for i in range(2, len(numbers)):
        if numbers[i] - numbers[i - 1] != step:
            return False
    return True


def _resolve_sum_band(options: Mapping[str, object]) -> tuple[int | None, int | None]:
    sum_min = options.get("sum_min")
    sum_max = options.get("sum_max")
    if _coerce_bool(options.get("sum_band_100_170", False)):
        if sum_min is None:
            sum_min = 100
        if sum_max is None:
            sum_max = 170
    return (int(sum_min), int(sum_max)) if sum_min is not None and sum_max is not None else (
        int(sum_min) if sum_min is not None else None,
        int(sum_max) if sum_max is not None else None,
    )


def _passes_constraints(numbers: list[int], options: Mapping[str, object]) -> bool:
    if _coerce_bool(options.get("avoid_birthday_bias", False)):
        high_band_count = sum(1 for n in numbers if n >= 32)
        if high_band_count < 3:
            return False

    pair_count = _consecutive_pair_count(numbers)
    pair_mode = str(options.get("consecutive_pair_mode", "any"))
    if pair_mode == "none" and pair_count != 0:
        return False
    if pair_mode == "one_or_two" and not (1 <= pair_count <= 2):
        return False
    if _coerce_bool(options.get("include_consecutive_pair", False)) and pair_count < 1:
        return False
    pair_max = options.get("consecutive_pair_max")
    if pair_max is not None and pair_count > int(pair_max):
        return False

    if _coerce_bool(options.get("avoid_popular_numbers", False)) and any(n in _POPULAR_NUMBERS for n in numbers):
        return False

    if _coerce_bool(options.get("balanced_odd_even", False)) and not _is_balanced_odd_even(numbers):
        return False

    if _coerce_bool(options.get("balanced_high_low", False)) and not _is_balanced_high_low(numbers):
        return False

    sum_min, sum_max = _resolve_sum_band(options)
    if sum_min is not None or sum_max is not None:
        min_bound = 21 if sum_min is None else sum_min
        max_bound = 260 if sum_max is None else sum_max
        if not _is_in_sum_band(numbers, min_bound, max_bound):
            return False

    span_min = options.get("span_min")
    span_max = options.get("span_max")
    if span_min is not None or span_max is not None:
        span = numbers[-1] - numbers[0]
        min_span = 0 if span_min is None else int(span_min)
        max_span = 44 if span_max is None else int(span_max)
        if span < min_span or span > max_span:
            return False

    zone_coverage_min = int(options.get("zone_coverage_min", 0))
    if zone_coverage_min > 0 and _zone_coverage_count(numbers) < zone_coverage_min:
        return False

    if _coerce_bool(options.get("avoid_same_last_digit_cluster", False)) and _max_same_last_digit_count(numbers) > 2:
        return False

    if _coerce_bool(options.get("avoid_arithmetic_sequence", False)) and _is_full_arithmetic_progression(numbers):
        return False

    return True


def _candidate_pool(options: Mapping[str, object]) -> list[int]:
    if _coerce_bool(options.get("avoid_popular_numbers", False)):
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


def _build_hot_cold_weights(
    draws: Sequence[Draw],
    window: int,
    alpha: float,
    mode: str,
    hot_ratio: float,
) -> dict[int, float]:
    if not draws:
        return {n: 1.0 for n in range(1, 46)}

    recent = draws[-window:] if window > 0 else draws
    frequency: Counter[int] = Counter()
    for draw in recent:
        frequency.update(draw.numbers)
    max_frequency = max(frequency.values(), default=1)

    latest_to_oldest = list(reversed(draws))
    miss_streak: dict[int, int] = {}
    for n in range(1, 46):
        streak = 0
        for draw in latest_to_oldest:
            if n in draw.numbers:
                break
            streak += 1
        miss_streak[n] = streak
    max_miss = max(miss_streak.values(), default=1)

    ratio = max(0.0, min(1.0, hot_ratio))
    weights: dict[int, float] = {}
    for n in range(1, 46):
        hot_score = frequency[n] / max_frequency
        cold_score = miss_streak[n] / max_miss if max_miss > 0 else 0.0
        if mode == "hot":
            score = hot_score
        elif mode == "cold":
            score = cold_score
        else:
            score = (hot_score * ratio) + (cold_score * (1.0 - ratio))
        weight = 1.0 + (alpha * score)
        weights[n] = max(weight, 0.0001)
    return weights


def _sampling_weights(
    pool: list[int],
    usage: Mapping[int, int],
    base_weights: Mapping[int, float] | None,
    prefer_low_overlap: bool,
    usage_power: float,
) -> list[float]:
    out: list[float] = []
    for n in pool:
        weight = base_weights.get(n, 1.0) if base_weights else 1.0
        if prefer_low_overlap:
            penalty = (1.0 + usage[n]) ** usage_power
            weight = weight / penalty
        out.append(max(weight, 0.0001))
    return out


def _generate_constrained(
    game_count: int,
    seed: int | None,
    options: Mapping[str, object],
    prefer_low_overlap: bool,
    base_weights: Mapping[int, float] | None = None,
    usage_power: float = 1.0,
) -> list[list[int]]:
    if game_count <= 0:
        return []

    pool = _candidate_pool(options)
    if len(pool) < 6:
        raise ValueError("Selected options leave fewer than 6 usable numbers.")

    rnd = random.Random(seed)
    usage = {n: 0 for n in range(1, 46)}
    games: list[list[int]] = []
    attempts_per_game = 2000

    for _ in range(game_count):
        selected: list[int] | None = None
        for _ in range(attempts_per_game):
            use_weighted = prefer_low_overlap or base_weights is not None
            if use_weighted:
                weights = _sampling_weights(pool, usage, base_weights, prefer_low_overlap, usage_power)
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


def _has_any_constraints(options: Mapping[str, object]) -> bool:
    bool_keys = (
        "avoid_birthday_bias",
        "include_consecutive_pair",
        "avoid_popular_numbers",
        "balanced_odd_even",
        "balanced_high_low",
        "sum_band_100_170",
        "avoid_same_last_digit_cluster",
        "avoid_arithmetic_sequence",
    )
    if any(_coerce_bool(options.get(key, False)) for key in bool_keys):
        return True
    if int(options.get("zone_coverage_min", 0)) > 0:
        return True
    if str(options.get("consecutive_pair_mode", "any")) != "any":
        return True
    if options.get("consecutive_pair_max") is not None:
        return True
    if options.get("sum_min") is not None or options.get("sum_max") is not None:
        return True
    if options.get("span_min") is not None or options.get("span_max") is not None:
        return True
    return False


def _apply_strategy_defaults(strategy_name: str, options: Mapping[str, object]) -> dict[str, object]:
    merged = dict(options)
    runtime = STRATEGY_RUNTIME_CONFIG.get(strategy_name, {})
    defaults = runtime.get("defaults", {})
    if isinstance(defaults, dict):
        merged.update(defaults)
    return merged


def _generate_for_strategy(
    strategy_name: str,
    game_count: int,
    seed: int | None,
    options: Mapping[str, object],
    draws: Sequence[Draw] | None,
) -> list[list[int]]:
    runtime = STRATEGY_RUNTIME_CONFIG.get(strategy_name, {})
    prefer_low_overlap = bool(runtime.get("prefer_low_overlap", strategy_name == "low_overlap_random"))
    usage_power = float(runtime.get("usage_power", 1.0))
    weight_mode = str(runtime.get("weight_mode", "none"))

    base_weights: dict[int, float] | None = None
    if weight_mode != "none":
        if not draws:
            raise ValueError("Selected strategy requires draw history.")
        window = int(options.get("hot_cold_window", 30))
        alpha = float(options.get("hot_cold_alpha", 1.4))
        hot_ratio = float(options.get("hot_mix_ratio", 0.5))
        base_weights = _build_hot_cold_weights(draws, window, alpha, weight_mode, hot_ratio)

    return _generate_constrained(
        game_count=game_count,
        seed=seed,
        options=options,
        prefer_low_overlap=prefer_low_overlap,
        base_weights=base_weights,
        usage_power=usage_power,
    )


def generate_balanced_quickpick(game_count: int, seed: int | None = None) -> list[list[int]]:
    options = _apply_strategy_defaults("balanced_quickpick", normalize_strategy_options(None))
    return _generate_constrained(game_count, seed, options, prefer_low_overlap=True, usage_power=1.1)


def generate_zone_spread(game_count: int, seed: int | None = None) -> list[list[int]]:
    options = _apply_strategy_defaults("zone_spread", normalize_strategy_options(None))
    return _generate_constrained(game_count, seed, options, prefer_low_overlap=False)


def generate_pair_tuner(game_count: int, seed: int | None = None) -> list[list[int]]:
    options = _apply_strategy_defaults("pair_tuner", normalize_strategy_options(None))
    return _generate_constrained(game_count, seed, options, prefer_low_overlap=False)


def generate_sum_span_guard(game_count: int, seed: int | None = None) -> list[list[int]]:
    options = _apply_strategy_defaults("sum_span_guard", normalize_strategy_options(None))
    return _generate_constrained(game_count, seed, options, prefer_low_overlap=False)


def generate_hot_focus(game_count: int, seed: int | None = None) -> list[list[int]]:
    return generate_uniform_random(game_count, seed)


def generate_cold_focus(game_count: int, seed: int | None = None) -> list[list[int]]:
    return generate_uniform_random(game_count, seed)


def generate_hot_cold_mix(game_count: int, seed: int | None = None) -> list[list[int]]:
    return generate_uniform_random(game_count, seed)


def generate_portfolio_diversify_v2(game_count: int, seed: int | None = None) -> list[list[int]]:
    options = _apply_strategy_defaults("portfolio_diversify_v2", normalize_strategy_options(None))
    return _generate_constrained(game_count, seed, options, prefer_low_overlap=True, usage_power=1.8)


STRATEGIES: dict[str, Strategy] = {
    "low_overlap_random": generate_low_overlap_random,
    "uniform_random": generate_uniform_random,
    "balanced_quickpick": generate_balanced_quickpick,
    "zone_spread": generate_zone_spread,
    "pair_tuner": generate_pair_tuner,
    "sum_span_guard": generate_sum_span_guard,
    "hot_focus": generate_hot_focus,
    "cold_focus": generate_cold_focus,
    "hot_cold_mix": generate_hot_cold_mix,
    "portfolio_diversify_v2": generate_portfolio_diversify_v2,
}


def generate_games_with_options(
    strategy_name: str,
    game_count: int,
    seed: int | None = None,
    options: Mapping[str, object] | None = None,
    draws: Sequence[Draw] | None = None,
) -> tuple[list[list[int]], dict[str, object]]:
    strategy = STRATEGIES.get(strategy_name)
    if strategy is None:
        raise KeyError(strategy_name)

    normalized = normalize_strategy_options(options)
    _validate_option_ranges(normalized)

    effective = _apply_strategy_defaults(strategy_name, normalized)
    _validate_option_ranges(effective)

    is_legacy_strategy = strategy_name in {"low_overlap_random", "uniform_random"}
    if is_legacy_strategy and not _has_any_constraints(effective):
        return strategy(game_count, seed), effective

    games = _generate_for_strategy(strategy_name, game_count, seed, effective, draws)
    return games, effective
