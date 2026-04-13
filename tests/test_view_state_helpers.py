from __future__ import annotations

import unittest

from app_support import QueryParamAccessor, build_dataset_view_state


class _FakeStreamlit:
    def __init__(self, query_params: dict[str, str] | None = None):
        self.query_params = dict(query_params or {})


class ViewStateHelperTests(unittest.TestCase):
    def test_build_dataset_view_state_preserves_legacy_keys_and_labels(self):
        armor_state = build_dataset_view_state("armors", "Detailed view")
        weapon_state = build_dataset_view_state("weapons", "Catalog")

        self.assertEqual(armor_state.state_keys.view_mode, "armor_view_mode")
        self.assertEqual(armor_state.state_keys.detail_scope_mode, "armor_detailed_scope_mode")
        self.assertEqual(armor_state.single_scope_select_label, "Choose Piece:")
        self.assertEqual(armor_state.single_scope_subject_label, "armor item")

        self.assertEqual(weapon_state.state_keys.view_mode, "weapons_view_mode")
        self.assertEqual(weapon_state.state_keys.detail_scope_mode, "weapons_detailed_scope_mode")
        self.assertEqual(weapon_state.single_scope_select_label, "Choose Weapon:")
        self.assertEqual(weapon_state.single_scope_subject_label, "weapon")

    def test_query_param_accessor_hydrates_session_state(self):
        fake_st = _FakeStreamlit(
            {
                "dataset": "Weapons",
                "armor_mode": "single_piece",
                "talisman_mode": "full_set",
                "piece_type": "Helm",
                "stats": "weight|value",
                "lock_order": "false",
                "single_stat": "weight",
                "sort": "Lowest First",
                "rows": "10",
                "method": "weighted_sum_normalized",
                "opt_engine": "advanced",
                "objective": "encounter_survival",
                "profile": "RayaLucaria_Mages.yaml",
                "lambda_status": "2.5",
                "opt_with_weight": "true",
                "use_max_weight": "true",
                "hist_view": "Classic",
                "max_weight": "14.5",
            }
        )
        session_state: dict[str, object] = {}

        state = QueryParamAccessor(fake_st).hydrate_session_state(
            session_state,
            armor_mode_default="single_piece",
            talisman_mode_default="single",
            optimization_method_default="maximin_normalized",
            optimizer_engine_default="legacy",
            optimizer_objective_default="stat_rank",
            normalize_armor_mode=lambda value: str(value or "").strip(),
            normalize_talisman_mode=lambda value: str(value or "").strip(),
            normalize_method_id=lambda value: str(value or "").strip(),
            normalize_engine_id=lambda value: str(value or "").strip(),
            normalize_objective_id=lambda value: str(value or "").strip(),
            normalize_hist_view_mode=lambda value: str(value or "").strip(),
        )

        self.assertEqual(state.selected_dataset_label, "Weapons")
        self.assertEqual(state.highlighted_stats, ("weight", "value"))
        self.assertFalse(state.lock_stat_order)
        self.assertEqual(state.rows_to_show, 10)
        self.assertEqual(state.optimizer_engine, "advanced")
        self.assertEqual(state.optimizer_objective_type, "encounter_survival")
        self.assertEqual(state.optimizer_lambda_status, 2.5)
        self.assertTrue(state.optimize_with_weight)
        self.assertTrue(state.use_max_weight)
        self.assertEqual(state.hist_view_mode, "Classic")
        self.assertEqual(state.max_weight_limit, 14.5)

        self.assertEqual(session_state["selected_dataset_label"], "Weapons")
        self.assertEqual(session_state["hist_view_mode_widget"], "Classic")
        self.assertEqual(session_state["_qp_hydrated"], True)


if __name__ == "__main__":
    unittest.main()
