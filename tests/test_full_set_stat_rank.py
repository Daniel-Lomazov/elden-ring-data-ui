from __future__ import annotations

import unittest

import pandas as pd

from optimizer import optimize


class FullSetStatRankTests(unittest.TestCase):
    def test_full_set_stat_rank_respects_total_weight_constraint(self):
        df = pd.DataFrame(
            [
                {"name": "H_Light", "type": "helm", "weight": 2.0, "Dmg: Fir": 10.0},
                {"name": "H_Heavy", "type": "helm", "weight": 6.0, "Dmg: Fir": 18.0},
                {"name": "A_Light", "type": "chest armor", "weight": 6.0, "Dmg: Fir": 20.0},
                {"name": "A_Heavy", "type": "chest armor", "weight": 14.0, "Dmg: Fir": 35.0},
                {"name": "G_Light", "type": "gauntlets", "weight": 2.0, "Dmg: Fir": 8.0},
                {"name": "G_Heavy", "type": "gauntlets", "weight": 5.0, "Dmg: Fir": 15.0},
                {"name": "R_Light", "type": "leg armor", "weight": 3.0, "Dmg: Fir": 12.0},
                {"name": "R_Heavy", "type": "leg armor", "weight": 8.0, "Dmg: Fir": 24.0},
            ]
        )

        request = {
            "version": 1,
            "scope": "full_set",
            "objective": {
                "type": "stat_rank",
                "method": "maximin_normalized",
                "weights": {"weight": 1.0, "Dmg: Fir": 1.0},
            },
            "selected_stats": ["weight", "Dmg: Fir"],
            "constraints": {
                "max_weight": 13.0,
                "top_k_per_slot": 2,
                "top_n": 3,
            },
            "config": {"minimize_stats": ["weight"]},
        }

        ranked = optimize(df, request)

        self.assertFalse(ranked.empty)
        self.assertIn("Helm", ranked.columns)
        self.assertIn("Armor", ranked.columns)
        self.assertIn("Gauntlets", ranked.columns)
        self.assertIn("Greaves", ranked.columns)
        self.assertIn("__opt_score", ranked.columns)
        self.assertLessEqual(len(ranked), 3)

        top = ranked.iloc[0]
        self.assertEqual(str(top["Helm"]), "H_Light")
        self.assertEqual(str(top["Armor"]), "A_Light")
        self.assertEqual(str(top["Gauntlets"]), "G_Light")
        self.assertEqual(str(top["Greaves"]), "R_Light")
        self.assertAlmostEqual(float(top["total_weight"]), 13.0)


if __name__ == "__main__":
    unittest.main()