from __future__ import annotations

import unittest

import pandas as pd

from optimizer import optimize, optimize_single_piece


class WeightedSumBehaviorTests(unittest.TestCase):
    def test_zero_weight_stat_matches_active_stat_set(self):
        df = pd.DataFrame(
            [
                {"name": "alpha", "Dmg: Phy": 10.0, "Dmg: Mag": 1.0, "status.poison": 0.0},
                {"name": "beta", "Dmg: Phy": 6.0, "Dmg: Mag": 10.0, "status.poison": 100.0},
                {"name": "gamma", "Dmg: Phy": 9.0, "Dmg: Mag": 9.0, "status.poison": 50.0},
            ]
        )

        with_zero_weight = optimize_single_piece(
            df,
            selected_stats=["Dmg: Phy", "Dmg: Mag", "status.poison"],
            method="weighted_sum_normalized",
            config={
                "weights": {
                    "Dmg: Phy": 1.0,
                    "Dmg: Mag": 1.0,
                    "status.poison": 0.0,
                }
            },
        )
        active_only = optimize_single_piece(
            df,
            selected_stats=["Dmg: Phy", "Dmg: Mag"],
            method="weighted_sum_normalized",
            config={"weights": {"Dmg: Phy": 1.0, "Dmg: Mag": 1.0}},
        )

        self.assertEqual(
            with_zero_weight["name"].tolist(),
            active_only["name"].tolist(),
        )
        self.assertEqual(with_zero_weight["__opt_length"].tolist(), [2, 2, 2])
        self.assertEqual(
            with_zero_weight["__opt_tiebreak"].round(6).tolist(),
            active_only["__opt_tiebreak"].round(6).tolist(),
        )
        self.assertEqual(
            with_zero_weight["__opt_score"].round(6).tolist(),
            active_only["__opt_score"].round(6).tolist(),
        )

    def test_all_zero_weights_fail_validation(self):
        df = pd.DataFrame(
            [
                {"name": "alpha", "Dmg: Phy": 10.0, "Dmg: Mag": 5.0},
                {"name": "beta", "Dmg: Phy": 9.0, "Dmg: Mag": 6.0},
            ]
        )

        with self.assertRaises(ValueError):
            optimize_single_piece(
                df,
                selected_stats=["Dmg: Phy", "Dmg: Mag"],
                method="weighted_sum_normalized",
                config={"weights": {"Dmg: Phy": 0.0, "Dmg: Mag": 0.0}},
            )

    def test_advanced_stat_rank_matches_legacy_backend(self):
        df = pd.DataFrame(
            [
                {"name": "alpha", "Dmg: Phy": 11.0, "Dmg: Mag": 3.0, "weight": 5.0},
                {"name": "beta", "Dmg: Phy": 8.0, "Dmg: Mag": 8.0, "weight": 4.0},
                {"name": "gamma", "Dmg: Phy": 4.0, "Dmg: Mag": 11.0, "weight": 8.0},
            ]
        )

        legacy = optimize_single_piece(
            df,
            selected_stats=["Dmg: Phy", "Dmg: Mag", "weight"],
            method="weighted_sum_normalized",
            config={
                "weights": {"Dmg: Phy": 2.0, "Dmg: Mag": 1.0, "weight": 1.0},
                "minimize_stats": ["weight"],
            },
        )
        advanced = optimize(
            df,
            {
                "version": 1,
                "engine": "advanced",
                "scope": "single_piece",
                "objective": {
                    "type": "stat_rank",
                    "method": "weighted_sum_normalized",
                    "weights": {"Dmg: Phy": 2.0, "Dmg: Mag": 1.0, "weight": 1.0},
                },
                "selected_stats": ["Dmg: Phy", "Dmg: Mag", "weight"],
                "config": {"minimize_stats": ["weight"]},
            },
        )

        self.assertEqual(advanced["name"].tolist(), legacy["name"].tolist())
        self.assertEqual(
            advanced["__opt_score"].round(6).tolist(),
            legacy["__opt_score"].round(6).tolist(),
        )
        self.assertEqual(
            advanced["__opt_tiebreak"].round(6).tolist(),
            legacy["__opt_tiebreak"].round(6).tolist(),
        )


if __name__ == "__main__":
    unittest.main()
