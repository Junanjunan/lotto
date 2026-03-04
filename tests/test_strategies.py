from __future__ import annotations

import unittest

from app.services.strategies import generate_games_with_options, normalize_strategy_options


class StrategyOptionTests(unittest.TestCase):
    def test_normalize_strategy_options_coerces_string_and_numeric_values(self) -> None:
        normalized = normalize_strategy_options(
            {
                "avoid_birthday_bias": "yes",
                "include_consecutive_pair": "no",
                "avoid_popular_numbers": "0",
                "balanced_odd_even": 1,
                "balanced_high_low": 0,
                "sum_band_100_170": "true",
                "avoid_same_last_digit_cluster": "off",
                "avoid_arithmetic_sequence": "on",
            }
        )
        self.assertTrue(normalized["avoid_birthday_bias"])
        self.assertFalse(normalized["include_consecutive_pair"])
        self.assertFalse(normalized["avoid_popular_numbers"])
        self.assertTrue(normalized["balanced_odd_even"])
        self.assertFalse(normalized["balanced_high_low"])
        self.assertTrue(normalized["sum_band_100_170"])
        self.assertFalse(normalized["avoid_same_last_digit_cluster"])
        self.assertTrue(normalized["avoid_arithmetic_sequence"])

    def test_generate_games_with_options_applies_popular_number_filter(self) -> None:
        games, normalized = generate_games_with_options(
            strategy_name="uniform_random",
            game_count=8,
            seed=42,
            options={"avoid_popular_numbers": True},
        )
        self.assertTrue(normalized["avoid_popular_numbers"])
        self.assertEqual(len(games), 8)
        for game in games:
            self.assertEqual(len(game), 6)
            self.assertNotIn(7, game)


if __name__ == "__main__":
    unittest.main()
