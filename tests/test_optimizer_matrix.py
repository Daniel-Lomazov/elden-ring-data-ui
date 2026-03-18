from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import pandas as pd

from optimizer.api import optimize
from optimizer.catalog import resolve_strategy
from optimizer.dialect import load_request


class OptimizerMatrixTests(unittest.TestCase):
    def test_resolve_strategy_matrix(self):
        cases = [
            ("legacy", "stat_rank", "single_piece", "stat_rank_single_piece"),
            ("legacy", "stat_rank", "full_set", "stat_rank_full_set"),
            ("legacy", "stat_rank", "complete_loadout", "stat_rank_complete_loadout"),
            ("advanced", "stat_rank", "single_piece", "stat_rank_single_piece"),
            ("advanced", "stat_rank", "full_set", "stat_rank_full_set"),
            ("advanced", "encounter_survival", "single_piece", "encounter_survival_single_piece"),
            ("advanced", "encounter_survival", "per_slot", "encounter_survival_per_slot"),
            ("advanced", "encounter_survival", "full_set", "encounter_survival_full_set"),
        ]

        for engine, objective, scope, expected_key in cases:
            with self.subTest(engine=engine, objective=objective, scope=scope):
                route = resolve_strategy(engine, objective, scope)
                self.assertEqual(route.engine_id, engine)
                self.assertEqual(route.objective_id, objective)
                self.assertEqual(route.scope, scope if scope != "complete_loadout" else "complete_loadout")
                self.assertEqual(route.dispatch_key, expected_key)

    def test_invalid_matrix_combinations_reject(self):
        cases = [
            (
                {
                    "version": 1,
                    "engine": "legacy",
                    "scope": "single_piece",
                    "objective": {"type": "encounter_survival"},
                    "encounter": {"incoming": {"damage_mix": {"neg.mag": 1.0}}},
                },
                "not supported by engine",
            ),
            (
                {
                    "version": 1,
                    "engine": "advanced",
                    "scope": "single_piece",
                    "objective": {"type": "encounter_survival", "method": "maximin_normalized"},
                    "encounter": {"incoming": {"damage_mix": {"neg.mag": 1.0}}},
                },
                "does not support optimization methods",
            ),
            (
                {
                    "version": 1,
                    "engine": "advanced",
                    "scope": "single_piece",
                    "objective": {
                        "type": "stat_rank",
                        "method": "not_a_method",
                    },
                    "selected_stats": ["Dmg: Phy", "Dmg: Mag"],
                },
                "Unsupported method",
            ),
            (
                {
                    "version": 1,
                    "dataset": "talismans",
                    "engine": "advanced",
                    "scope": "single_piece",
                    "objective": {"type": "encounter_survival"},
                    "encounter": {"incoming": {"damage_mix": {"neg.mag": 1.0}}},
                },
                "does not support dataset",
            ),
            (
                {
                    "version": 1,
                    "engine": "advanced",
                    "scope": "complete_loadout",
                    "objective": {
                        "type": "encounter_survival",
                        "lambda_status": 0.5,
                    },
                    "encounter": {"incoming": {"damage_mix": {"neg.mag": 1.0}}},
                },
                "does not support scope",
            ),
        ]

        for request, expected_message in cases:
            with self.subTest(request=request):
                with self.assertRaises(ValueError) as ctx:
                    load_request(request)
                self.assertIn(expected_message, str(ctx.exception))

    def test_dispatch_matrix_uses_resolved_strategy(self):
        df = pd.DataFrame([{"name": "alpha", "Dmg: Phy": 10.0, "Dmg: Mag": 5.0}])
        single_result = pd.DataFrame([{"marker": "stat-rank-single"}])
        full_result = pd.DataFrame([{"marker": "stat-rank-full"}])
        encounter_result = pd.DataFrame([{"marker": "encounter-single"}])
        cases = [
            (
                {
                    "version": 1,
                    "engine": "legacy",
                    "scope": "single_piece",
                    "objective": {
                        "type": "stat_rank",
                        "method": "maximin_normalized",
                    },
                    "selected_stats": ["Dmg: Phy", "Dmg: Mag"],
                },
                "stat_rank_single_piece",
                "stat-rank-single",
            ),
            (
                {
                    "version": 1,
                    "engine": "advanced",
                    "scope": "full_set",
                    "objective": {
                        "type": "stat_rank",
                        "method": "maximin_normalized",
                    },
                    "selected_stats": ["Dmg: Phy", "Dmg: Mag"],
                },
                "stat_rank_full_set",
                "stat-rank-full",
            ),
            (
                {
                    "version": 1,
                    "engine": "advanced",
                    "scope": "per_slot",
                    "objective": {
                        "type": "encounter_survival",
                        "lambda_status": 0.25,
                    },
                    "encounter": {"incoming": {"damage_mix": {"neg.mag": 1.0}}},
                },
                "encounter_survival_per_slot",
                "encounter-single",
            ),
        ]

        single_mock = Mock(side_effect=lambda *_: single_result.copy())
        full_mock = Mock(side_effect=lambda *_: full_result.copy())
        encounter_mock = Mock(side_effect=lambda *_: encounter_result.copy())
        encounter_full_mock = Mock(side_effect=lambda *_: pd.DataFrame([{"marker": "encounter-full"}]))

        with patch.dict(
            "optimizer.api._DISPATCH_BY_KEY",
            {
                "stat_rank_single_piece": single_mock,
                "stat_rank_full_set": full_mock,
                "stat_rank_complete_loadout": single_mock,
                "encounter_survival_single_piece": encounter_mock,
                "encounter_survival_per_slot": encounter_mock,
                "encounter_survival_full_set": encounter_full_mock,
            },
            clear=False,
        ):
            for request, expected_key, expected_marker in cases:
                with self.subTest(expected_key=expected_key):
                    route = resolve_strategy(request["engine"], request["objective"]["type"], request["scope"])
                    self.assertEqual(route.dispatch_key, expected_key)
                    result = optimize(df, request)
                    self.assertEqual(result.iloc[0]["marker"], expected_marker)

            self.assertEqual(single_mock.call_count, 1)
            self.assertEqual(full_mock.call_count, 1)
            self.assertEqual(encounter_mock.call_count, 1)
            self.assertEqual(encounter_full_mock.call_count, 0)


if __name__ == "__main__":
    unittest.main()
