# Preserved Flow Matrix

Last refreshed: `2026-04-13`

| Flow | Expected behavior | Primary coverage |
| --- | --- | --- |
| Documented app launch | Streamlit app starts and serves HTTP on localhost | `tests/test_ui_smoke.py::test_app_starts_headless_and_serves_http`, `tools.final_check` |
| Dataset selector | Visible top-level datasets remain visible; deferred item catalogs stay hidden | `tests/test_ui_smoke.py::test_dataset_chooser_lists_visible_registry_datasets` |
| Side-by-side mode | Dual embedded panes and pane-specific dataset controls remain available | `tests/test_ui_smoke.py::test_side_by_side_mode_exposes_dual_pane_controls` |
| Armor detailed view | `Single`, `Full`, and `Custom` detailed flows remain intact | `tests/test_ui_smoke.py`, `tests/test_dataset_ui_registry.py` |
| Talisman detailed / optimization flow | `Single` and `Custom` detailed flow plus optimization mode remain intact | `tests/test_ui_smoke.py::test_talisman_flows_hide_unimplemented_family_scope` |
| Weapons / Shields detailed flow | Default to `Detailed view` with `Single` scope and can switch back to `Catalog` | `tests/test_ui_smoke.py::test_equipment_datasets_default_to_single_scope_detailed_flow`, `test_equipment_datasets_can_switch_back_to_catalog_flow` |
| Progression datasets | Upgrade datasets stay browse-only and do not expose ranking/optimizer controls | `tests/test_ui_smoke.py::test_upgrade_dataset_uses_progression_browser_without_ranking_controls` |
| Advanced optimizer | `Stat Ranking` and `Encounter Survival` controls remain human-readable and correctly gated | `tests/test_ui_smoke.py::test_optimization_view_control_transitions`, `tools.optimizer_smoke` |
| Runtime controller lifecycle | Start/status/open/stop/restart/recover remain compatible with current CLI and persisted state | `tests/test_runtime_controller.py`, `tools.workspace_verify --tests-subset runtime` |
