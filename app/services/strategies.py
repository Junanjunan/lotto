from __future__ import annotations

import random
from typing import Callable


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
