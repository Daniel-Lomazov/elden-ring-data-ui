from __future__ import annotations

import unittest

import pandas as pd

from optimizer import optimize


class MonotonicityTests(unittest.TestCase):
    def test_higher_relevant_negation_improves_m(self):
        df = pd.DataFrame(
            [
                {"name": "low", "Dmg: Mag": 5.0},
                {"name": "high", "Dmg: Mag": 15.0},
            ]
        )
        req = {
            "version": 1,
            "scope": "single_piece",
            "objective": {"type": "encounter_survival", "lambda_status": 0.0},
            "encounter": {"incoming": {"damage_mix": {"neg.mag": 1.0}}},
        }
        ranked = optimize(df, req)
        self.assertEqual(str(ranked.iloc[0]["name"]), "high")

    def test_higher_resistance_reduces_status_penalty(self):
        df = pd.DataFrame(
            [
                {"name": "low_rob", "Dmg: VS Sla.": 10.0, "Res: Rob.": 5.0},
                {"name": "high_rob", "Dmg: VS Sla.": 10.0, "Res: Rob.": 35.0},
            ]
        )
        req = {
            "version": 1,
            "scope": "single_piece",
            "objective": {"type": "encounter_survival", "lambda_status": 1.0},
            "encounter": {
                "incoming": {"damage_mix": {"neg.sla": 1.0}},
                "status_threats": {
                    "status.bleed": {
                        "buildup_per_hit": 45,
                        "proc_penalty": 150,
                        "weight": 1.0,
                    }
                },
            },
        }
        ranked = optimize(df, req)
        self.assertEqual(str(ranked.iloc[0]["name"]), "high_rob")


if __name__ == "__main__":
    unittest.main()
