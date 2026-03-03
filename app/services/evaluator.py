from __future__ import annotations

from collections import defaultdict

from app.models import Draw


def evaluate_game_numbers(game_numbers: list[int], draw: Draw) -> tuple[int, int, int]:
    draw_set = set(draw.numbers)
    game_set = set(game_numbers)

    match_count = len(draw_set & game_set)
    bonus_match = 1 if draw.bonus in game_set else 0

    if match_count == 6:
        rank = 1
    elif match_count == 5 and bonus_match == 1:
        rank = 2
    elif match_count == 5:
        rank = 3
    elif match_count == 4:
        rank = 4
    elif match_count == 3:
        rank = 5
    else:
        rank = 0

    return match_count, bonus_match, rank


def evaluate_games(games: list[list[int]], draws: list[Draw]) -> list[dict]:
    out: list[dict] = []
    rank_labels = (1, 2, 3, 4, 5)

    for idx, game_numbers in enumerate(games):
        rank_distribution = defaultdict(int)
        hits: list[dict] = []
        game_set = set(game_numbers)

        for draw in draws:
            match_count, bonus_match, rank = evaluate_game_numbers(game_numbers, draw)
            rank_distribution[rank] += 1
            if rank == 0:
                continue

            matched_numbers = sorted(game_set & set(draw.numbers))
            hits.append(
                {
                    "draw_no": draw.draw_no,
                    "match_count": match_count,
                    "bonus_match": bonus_match,
                    "rank": rank,
                    "draw_numbers": draw.numbers,
                    "matched_numbers": matched_numbers,
                }
            )

        public_distribution = {
            label: rank_distribution[label]
            for label in rank_labels
            if rank_distribution[label] > 0
        }

        out.append(
            {
                "game_index": idx,
                "numbers": game_numbers,
                "rank_distribution": public_distribution,
                "total_hits": sum(rank_distribution[label] for label in rank_labels),
                "hits": hits,
            }
        )

    return out
