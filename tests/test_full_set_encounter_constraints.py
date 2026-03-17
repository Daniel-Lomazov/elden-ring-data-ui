from __future__ import annotations

import unittest

import pandas as pd

from optimizer import optimize


class FullSetEncounterConstraintTests(unittest.TestCase):
    def test_include_names_survives_top_k_pruning(self):
        df = pd.DataFrame(
            [
                {"name": "H_Low", "type": "helm", "Dmg: Mag": 5.0, "weight": 1.0},
                {"name": "H_High", "type": "helm", "Dmg: Mag": 20.0, "weight": 3.0},
                {"name": "A_Low", "type": "chest armor", "Dmg: Mag": 5.0, "weight": 1.0},
                {"name": "A_High", "type": "chest armor", "Dmg: Mag": 20.0, "weight": 3.0},
                {"name": "G_Low", "type": "gauntlets", "Dmg: Mag": 5.0, "weight": 1.0},
                {"name": "G_High", "type": "gauntlets", "Dmg: Mag": 20.0, "weight": 3.0},
                {"name": "R_Low", "type": "leg armor", "Dmg: Mag": 5.0, "weight": 1.0},
                {"name": "R_High", "type": "leg armor", "Dmg: Mag": 20.0, "weight": 3.0},
            ]
        )

        req = {
            "version": 1,
            "scope": "full_set",
            "objective": {
                "type": "encounter_survival",
                "hp": 1000,
                "lambda_status": 0.0,
            },
            "encounter": {
                "incoming": {"damage_mix": {"neg.mag": 1.0}},
                "status_threats": {},
            },
            "constraints": {
                "include_names": ["A_Low", "G_Low"],
                "top_k_per_slot": 1,
                "top_n": 5,
            },
        }

        ranked = optimize(df, req)

        self.assertFalse(ranked.empty)
        self.assertTrue((ranked["Armor"] == "A_Low").all())
        self.assertTrue((ranked["Gauntlets"] == "G_Low").all())


if __name__ == "__main__":
    unittest.main()
