from __future__ import annotations

import unittest
from pathlib import Path

from app_support import resolve_optimization_view_state


ROOT = Path(__file__).resolve().parents[1]


class OptimizationViewResolverTests(unittest.TestCase):
    def test_advanced_encounter_configuration_uses_encounter_controls(self):
        session_state = {
            "optimizer_engine": "Optimization 2.0",
            "optimizer_objective_type": "encounter_survival",
            "optimizer_encounter_profile": "Bayle_Phys_Fire_Lightning.yaml",
            "optimizer_lambda_status": 1.5,
            "optimizer_method": "maximin_normalized",
        }

        state = resolve_optimization_view_state(
            ROOT,
            "armors",
            "single_piece",
            session_state,
        )

        self.assertEqual(state.optimizer_engine, "advanced")
        self.assertEqual(state.optimizer_objective_type, "encounter_survival")
        self.assertTrue(state.show_encounter_profile)
        self.assertTrue(state.show_status_penalty_weight)
        self.assertFalse(state.show_optimization_method)
        self.assertFalse(state.show_weight_controls)
        self.assertIn("Bayle_Phys_Fire_Lightning.yaml", state.profile_options)
        self.assertEqual(session_state["optimizer_method"], "")

    def test_weighted_sum_stat_ranking_exposes_weight_controls(self):
        session_state = {
            "optimizer_engine": "legacy",
            "optimizer_objective_type": "stat_rank",
            "optimizer_method": "weighted_sum_normalized",
        }

        state = resolve_optimization_view_state(
            ROOT,
            "armors",
            "single_piece",
            session_state,
            ranking_stat_count=2,
        )

        self.assertEqual(state.optimizer_engine, "legacy")
        self.assertEqual(state.optimizer_objective_type, "stat_rank")
        self.assertTrue(state.show_optimization_method)
        self.assertTrue(state.show_weight_controls)
        self.assertGreaterEqual(len(state.engine_options), 1)
        self.assertGreaterEqual(len(state.objective_options), 1)
        self.assertEqual(state.optimizer_method, "weighted_sum_normalized")

    def test_single_stat_configuration_hides_weight_controls(self):
        session_state = {
            "optimizer_engine": "legacy",
            "optimizer_objective_type": "stat_rank",
            "optimizer_method": "weighted_sum_normalized",
        }

        state = resolve_optimization_view_state(
            ROOT,
            "armors",
            "single_piece",
            session_state,
            ranking_stat_count=1,
        )

        self.assertTrue(state.show_optimization_method)
        self.assertFalse(state.show_weight_controls)

    def test_switching_to_legacy_resets_invalid_encounter_objective(self):
        session_state = {
            "optimizer_engine": "legacy",
            "optimizer_objective_type": "encounter_survival",
            "optimizer_method": "weighted_sum_normalized",
            "optimizer_encounter_profile": "missing_profile.yaml",
        }

        state = resolve_optimization_view_state(
            ROOT,
            "armors",
            "single_piece",
            session_state,
            ranking_stat_count=2,
        )

        self.assertEqual(state.optimizer_engine, "legacy")
        self.assertEqual(state.optimizer_objective_type, "stat_rank")
        self.assertTrue(state.show_optimization_method)
        self.assertFalse(state.show_encounter_profile)
        self.assertFalse(state.show_status_penalty_weight)
        self.assertEqual(state.optimizer_method, "weighted_sum_normalized")
        self.assertEqual(session_state["optimizer_objective_type"], "stat_rank")

    def test_invalid_saved_profile_is_normalized_to_first_available_profile(self):
        session_state = {
            "optimizer_engine": "advanced",
            "optimizer_objective_type": "encounter_survival",
            "optimizer_encounter_profile": "missing_profile.yaml",
        }

        state = resolve_optimization_view_state(
            ROOT,
            "armors",
            "single_piece",
            session_state,
        )

        self.assertTrue(state.show_encounter_profile)
        self.assertGreaterEqual(len(state.profile_options), 1)
        self.assertEqual(state.optimizer_encounter_profile, state.profile_options[0])
        self.assertEqual(session_state["optimizer_encounter_profile"], state.profile_options[0])

    def test_encounter_objective_clears_method_state(self):
        session_state = {
            "optimizer_engine": "advanced",
            "optimizer_objective_type": "encounter_survival",
            "optimizer_method": "weighted_sum_normalized",
        }

        state = resolve_optimization_view_state(
            ROOT,
            "armors",
            "single_piece",
            session_state,
            ranking_stat_count=3,
        )

        self.assertFalse(state.show_optimization_method)
        self.assertFalse(state.show_weight_controls)
        self.assertEqual(state.optimizer_method, "")
        self.assertEqual(session_state["optimizer_method"], "")


if __name__ == "__main__":
    unittest.main()
