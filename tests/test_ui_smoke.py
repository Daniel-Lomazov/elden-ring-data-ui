from __future__ import annotations

import json
import os
import socket
import subprocess
import time
import unittest
import urllib.request
from functools import lru_cache
from pathlib import Path

from optimizer import (
    format_encounter_profile_display_name,
    get_available_objective_ids,
    get_engine_label,
    get_method_label,
    get_objective_label,
)
from tools.temp_support import (
    ensure_temp_root,
    patched_temporary_directory_cleanup,
    temporary_env_root,
)

_TEMP_CLEANUP_PATCH = patched_temporary_directory_cleanup()
_TEMP_CLEANUP_PATCH.__enter__()

from streamlit.testing.v1 import AppTest, element_tree  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT.parent / "anaconda3" / "envs" / "elden_ring_ui" / "python.exe"
TEST_TEMP_ROOT = ensure_temp_root("ui-smoke")


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@lru_cache(maxsize=1)
def _load_stat_ui_map() -> dict[str, dict[str, str]]:
    path = ROOT / "data" / "stat_ui_map.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    out: dict[str, dict[str, str]] = {}
    stats = payload.get("stats", []) if isinstance(payload, dict) else []
    for row in stats:
        if isinstance(row, dict):
            key = str(row.get("column", "")).strip()
            if key:
                out[key] = {
                    "display_name": str(row.get("display_name", key)).strip() or key,
                    "emoji": str(row.get("emoji", "📊")).strip() or "📊",
                }
    return out


def _format_stat_option_label(stat_name: str) -> str:
    meta = _load_stat_ui_map().get(str(stat_name or "").strip(), {})
    display = str(meta.get("display_name", stat_name)).strip() or str(stat_name)
    emoji = str(meta.get("emoji", "📊")).strip() or "📊"
    return f"{emoji} {display}"


def _patch_unknown_block_init(self, proto, root):
    self.children = {}
    self.proto = proto
    self.root = root
    if proto:
        self.type = proto.WhichOneof("type") or "unknown"
    else:
        self.type = "unknown"


def _patched_selectbox_index(self):
    token = str(self.value or "")
    if token in self.options:
        return self.options.index(token)

    candidates = []
    if self.label == "Optimization engine" and token in {"legacy", "advanced"}:
        candidates.append(get_engine_label(token))
    elif self.label == "Objective" and token in {"stat_rank", "encounter_survival"}:
        candidates.append(get_objective_label(token))
    elif self.label == "Optimization method" and token in {
        "maximin_normalized",
        "weighted_sum_normalized",
    }:
        candidates.append(get_method_label(token))
    elif self.label == "Encounter profile":
        candidates.append(format_encounter_profile_display_name(token) or token)

    for candidate in candidates:
        if candidate and candidate in self.options:
            return self.options.index(candidate)

    return 0 if self.options else None


def _patched_multiselect_indices(self):
    indices = []
    for value in self.value:
        token = str(value or "")
        if token in self.options:
            indices.append(self.options.index(token))
            continue
        mapped = _format_stat_option_label(token)
        if mapped in self.options:
            indices.append(self.options.index(mapped))
        else:
            indices.append(0 if self.options else 0)
    return indices


class UiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._temp_env = temporary_env_root(TEST_TEMP_ROOT)
        cls._temp_env.__enter__()
        cls._original_block_init = element_tree.Block.__init__
        cls._original_selectbox_index = element_tree.Selectbox.index
        cls._original_multiselect_indices = element_tree.Multiselect.indices

        element_tree.Block.__init__ = _patch_unknown_block_init
        element_tree.Selectbox.index = property(_patched_selectbox_index)
        element_tree.Multiselect.indices = property(_patched_multiselect_indices)

    @classmethod
    def tearDownClass(cls):
        element_tree.Block.__init__ = cls._original_block_init
        element_tree.Selectbox.index = cls._original_selectbox_index
        element_tree.Multiselect.indices = cls._original_multiselect_indices
        cls._temp_env.__exit__(None, None, None)

    def _new_app(self) -> AppTest:
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
        app.run(timeout=60)
        self.assertEqual(len(app.exception), 0)
        return app

    def _select_dataset(self, app: AppTest, dataset_label: str) -> AppTest:
        next(widget for widget in app.selectbox if widget.label == "Choose Dataset:").select(
            dataset_label
        ).run(timeout=60)
        self.assertEqual(len(app.exception), 0)
        return app

    def test_app_starts_headless_and_serves_http(self):
        port = _get_free_port()
        env = os.environ.copy()
        env["TMP"] = str(ROOT / ".cache" / "ui-smoke")
        env["TEMP"] = str(ROOT / ".cache" / "ui-smoke")
        Path(env["TMP"]).mkdir(parents=True, exist_ok=True)

        process = subprocess.Popen(
            [
                str(PYTHON),
                "-m",
                "streamlit",
                "run",
                "app.py",
                "--server.headless",
                "true",
                "--server.port",
                str(port),
            ],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            deadline = time.time() + 45
            last_error = None
            while time.time() < deadline:
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as response:
                        self.assertEqual(response.status, 200)
                        return
                except Exception as exc:  # pragma: no cover - polling loop
                    last_error = exc
                    time.sleep(1)
            self.fail(f"Streamlit app did not become ready: {last_error}")
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    def test_selector_hides_item_catalogs_and_shows_stack_layout_for_armor_custom_scope(self):
        app = self._new_app()

        dataset_select = next(widget for widget in app.selectbox if widget.label == "Choose Dataset:")
        self.assertNotIn("Items / Bells", dataset_select.options)
        self.assertNotIn("Items / Remembrances", dataset_select.options)

        next(widget for widget in app.selectbox if widget.label == "Choose Scope:").select(
            "Custom"
        ).run(timeout=60)
        self.assertEqual(len(app.exception), 0)

        stack_layout = next(widget for widget in app.selectbox if widget.label == "Stack layout:")
        self.assertEqual(stack_layout.options, ["Horizontal", "Vertical"])

        stack_layout.select("Vertical").run(timeout=60)
        self.assertEqual(len(app.exception), 0)

    def test_optimization_capability_labels_and_rules_are_human_readable(self):
        self.assertEqual(get_engine_label("legacy"), "Legacy Ranking")
        self.assertEqual(get_engine_label("advanced"), "Advanced Optimizer")
        self.assertEqual(get_objective_label("stat_rank"), "Stat Ranking")
        self.assertEqual(get_objective_label("encounter_survival"), "Encounter Survival")
        self.assertEqual(get_method_label("maximin_normalized"), "Maximin")
        self.assertEqual(get_method_label("weighted_sum_normalized"), "Weighted Sum")
        self.assertEqual(
            get_available_objective_ids("legacy", "armors", "single_piece"),
            ["stat_rank"],
        )
        self.assertEqual(
            get_available_objective_ids("advanced", "armors", "single_piece"),
            ["stat_rank", "encounter_survival"],
        )

    def test_optimization_view_control_transitions(self):
        app = self._new_app()

        next(widget for widget in app.selectbox if widget.label == "Choose View:").select(
            "Optimization view"
        ).run(timeout=60)
        self.assertEqual(len(app.exception), 0)

        selectboxes = {widget.label: widget for widget in app.selectbox}
        self.assertEqual(
            selectboxes["Optimization engine"].options,
            ["Legacy Ranking", "Advanced Optimizer"],
        )
        self.assertEqual(selectboxes["Objective"].options, ["Stat Ranking"])
        self.assertEqual(selectboxes["Optimization method"].options, ["Maximin", "Weighted Sum"])

        selectboxes["Optimization engine"].select("Advanced Optimizer").run(timeout=60)
        self.assertEqual(len(app.exception), 0)

        selectboxes = {widget.label: widget for widget in app.selectbox}
        self.assertEqual(
            selectboxes["Objective"].options,
            ["Stat Ranking", "Encounter Survival"],
        )
        self.assertEqual(selectboxes["Objective"].value, "stat_rank")

        selectboxes["Objective"].select("Encounter Survival").run(timeout=60)
        self.assertEqual(len(app.exception), 0)

        selectboxes = {widget.label: widget for widget in app.selectbox}
        number_inputs = {widget.label: widget for widget in app.number_input}
        self.assertNotIn("Optimization method", selectboxes)
        self.assertIn("Encounter profile", selectboxes)
        self.assertIn("Status Penalty Weight", number_inputs)
        profile_dir = ROOT / "data" / "profiles"
        expected_profiles = [
            format_encounter_profile_display_name(path.name)
            for path in sorted(profile_dir.iterdir())
            if path.is_file() and path.suffix.lower() in {".yaml", ".yml", ".json"}
        ]
        self.assertEqual(selectboxes["Encounter profile"].options, expected_profiles)

        selectboxes["Optimization engine"].select("Legacy Ranking").run(timeout=60)
        self.assertEqual(len(app.exception), 0)

        selectboxes = {widget.label: widget for widget in app.selectbox}
        number_inputs = {widget.label: widget for widget in app.number_input}
        self.assertEqual(selectboxes["Objective"].options, ["Stat Ranking"])
        self.assertEqual(selectboxes["Objective"].value, "stat_rank")
        self.assertIn("Optimization method", selectboxes)
        self.assertNotIn("Encounter profile", selectboxes)
        self.assertNotIn("Status Penalty Weight", number_inputs)

    def test_dataset_chooser_lists_visible_registry_datasets(self):
        app = self._new_app()

        dataset_selectbox = next(
            widget for widget in app.selectbox if widget.label == "Choose Dataset:"
        )

        self.assertEqual(dataset_selectbox.options[:2], ["Armors", "Talismans"])
        self.assertIn("Armors", dataset_selectbox.options)
        self.assertIn("Talismans", dataset_selectbox.options)
        self.assertIn("Ashes Of War", dataset_selectbox.options)
        self.assertIn("Weapons Upgrades", dataset_selectbox.options)
        self.assertIn("Shields Upgrades", dataset_selectbox.options)
        self.assertNotIn("Items / Remembrances", dataset_selectbox.options)
        self.assertFalse(any(option.startswith("Items /") for option in dataset_selectbox.options))
        self.assertTrue(
            all("Not implemented yet" not in option for option in dataset_selectbox.options)
        )

    def test_side_by_side_mode_exposes_dual_pane_controls(self):
        app = self._new_app()

        next(widget for widget in app.selectbox if widget.label == "Layout:").select(
            "Side by side"
        ).run(timeout=60)
        self.assertEqual(len(app.exception), 0)

        selectboxes = {widget.label: widget for widget in app.selectbox}
        number_inputs = {widget.label: widget for widget in app.number_input}

        self.assertNotIn("Layout:", {widget.label: widget for widget in app.radio})
        self.assertIn("Left pane dataset:", selectboxes)
        self.assertIn("Right pane dataset:", selectboxes)
        self.assertIn("Pane height:", number_inputs)
        self.assertNotIn("Choose Dataset:", selectboxes)
        self.assertIn("Armors", selectboxes["Left pane dataset:"].options)
        self.assertIn("Talismans", selectboxes["Right pane dataset:"].options)

    def test_equipment_datasets_default_to_single_scope_detailed_flow(self):
        expectations = [
            ("Weapons", "Choose Weapon:"),
            ("Shields", "Choose Shield:"),
        ]

        for dataset_label, item_label in expectations:
            with self.subTest(dataset=dataset_label):
                app = self._select_dataset(self._new_app(), dataset_label)

                selectboxes = {widget.label: widget for widget in app.selectbox}
                multiselects = {widget.label: widget for widget in app.multiselect}
                radios = {widget.label: widget for widget in app.radio}

                self.assertIn("Choose View:", selectboxes)
                self.assertEqual(selectboxes["Choose View:"].options, ["Detailed view", "Catalog"])
                self.assertEqual(selectboxes["Choose View:"].value, "Detailed view")
                self.assertIn("Choose Scope:", selectboxes)
                self.assertEqual(selectboxes["Choose Scope:"].options, ["Single"])
                self.assertEqual(selectboxes["Choose Scope:"].value, "Single")
                self.assertIn(item_label, selectboxes)
                self.assertNotIn("Highlighted stats:", multiselects)
                self.assertNotIn("Sort order:", selectboxes)
                self.assertNotIn("Rows to show:", selectboxes)
                self.assertNotIn("Optimization engine", selectboxes)
                self.assertNotIn("Mode:", radios)
                self.assertFalse(any(label.startswith("Slot ") for label in selectboxes))

                markdown_values = [widget.value for widget in app.markdown]
                self.assertTrue(any("#### Requirements" in value for value in markdown_values))
                self.assertTrue(any("**Requirements:**" in value for value in markdown_values))
                self.assertTrue(any("**Edition:**" in value for value in markdown_values))

    def test_equipment_datasets_can_switch_back_to_catalog_flow(self):
        expectations = [
            ("Weapons", "Choose Weapon:"),
            ("Shields", "Choose Shield:"),
        ]

        for dataset_label, item_label in expectations:
            with self.subTest(dataset=dataset_label):
                app = self._select_dataset(self._new_app(), dataset_label)

                next(widget for widget in app.selectbox if widget.label == "Choose View:").select(
                    "Catalog"
                ).run(timeout=60)
                self.assertEqual(len(app.exception), 0)

                selectboxes = {widget.label: widget for widget in app.selectbox}
                multiselects = {widget.label: widget for widget in app.multiselect}
                radios = {widget.label: widget for widget in app.radio}

                self.assertIn("Choose View:", selectboxes)
                self.assertNotIn("Choose Scope:", selectboxes)
                self.assertNotIn(item_label, selectboxes)
                self.assertIn("Highlighted stats:", multiselects)
                self.assertIn("Sort order:", selectboxes)
                self.assertIn("Rows to show:", selectboxes)
                self.assertNotIn("Optimization engine", selectboxes)
                self.assertNotIn("Mode:", radios)
                self.assertFalse(any(label.startswith("Slot ") for label in selectboxes))

    def test_generic_browse_only_dataset_hides_ranking_controls(self):
        app = self._select_dataset(self._new_app(), "Bosses")

        selectboxes = {widget.label: widget for widget in app.selectbox}
        multiselects = {widget.label: widget for widget in app.multiselect}

        self.assertNotIn("Choose View:", selectboxes)
        self.assertNotIn("Choose Scope:", selectboxes)
        self.assertNotIn("Highlighted stats:", multiselects)
        self.assertNotIn("Highlight stat:", selectboxes)
        self.assertNotIn("Sort order:", selectboxes)
        self.assertNotIn("Rows to show:", selectboxes)

    def test_talisman_flows_hide_unimplemented_family_scope(self):
        app = self._select_dataset(self._new_app(), "Talismans")

        selectboxes = {widget.label: widget for widget in app.selectbox}
        self.assertEqual(selectboxes["Choose Scope:"].options, ["Single", "Custom"])
        self.assertNotIn("Choose family:", selectboxes)

        selectboxes["Choose Scope:"].select("Custom").run(timeout=60)
        self.assertEqual(len(app.exception), 0)

        next(widget for widget in app.selectbox if widget.label == "Choose View:").select(
            "Optimization view"
        ).run(timeout=60)
        self.assertEqual(len(app.exception), 0)

        radios = {widget.label: widget for widget in app.radio}
        self.assertIn("Mode:", radios)
        self.assertEqual(radios["Mode:"].options, ["Single", "Full Set"])

    def test_talismans_expose_value_as_rankable_stat(self):
        app = self._select_dataset(self._new_app(), "Talismans")

        next(widget for widget in app.selectbox if widget.label == "Choose View:").select(
            "Optimization view"
        ).run(timeout=60)
        self.assertEqual(len(app.exception), 0)

        stat_picker = next(widget for widget in app.multiselect if widget.label == "Highlighted stats:")
        option_text = [str(option).lower() for option in stat_picker.options]

        self.assertTrue(any("value" in option for option in option_text))

    def test_incantations_expose_spell_cost_and_requirement_stats(self):
        app = self._select_dataset(self._new_app(), "Incantations")

        multiselects = {widget.label: widget for widget in app.multiselect}
        selectboxes = {widget.label: widget for widget in app.selectbox}
        option_text = [str(option).lower() for option in multiselects["Highlighted stats:"].options]

        self.assertIn("Rows to show:", selectboxes)
        self.assertTrue(any("slot" in option for option in option_text))
        self.assertTrue(any("fai" in option for option in option_text))
        self.assertTrue(any("stamina" in option for option in option_text))

    def test_item_catalog_datasets_are_hidden_from_main_selector(self):
        app = self._new_app()

        dataset_selectbox = next(
            widget for widget in app.selectbox if widget.label == "Choose Dataset:"
        )

        self.assertNotIn("Items / Bells", dataset_selectbox.options)
        self.assertNotIn("Items / Remembrances", dataset_selectbox.options)

    def test_upgrade_dataset_uses_progression_browser_without_ranking_controls(self):
        for dataset_label in ("Weapons Upgrades", "Shields Upgrades"):
            with self.subTest(dataset=dataset_label):
                app = self._select_dataset(self._new_app(), dataset_label)

                selectboxes = {widget.label: widget for widget in app.selectbox}
                multiselects = {widget.label: widget for widget in app.multiselect}
                radios = {widget.label: widget for widget in app.radio}

                self.assertIn("Rows to preview:", selectboxes)
                self.assertIn("Open item:", selectboxes)
                self.assertNotIn("Choose View:", selectboxes)
                self.assertNotIn("Choose Scope:", selectboxes)
                self.assertNotIn("Highlighted stats:", multiselects)
                self.assertNotIn("Highlight stat:", selectboxes)
                self.assertNotIn("Sort order:", selectboxes)
                self.assertNotIn("Rows to show:", selectboxes)
                self.assertNotIn("Optimization engine", selectboxes)
                self.assertFalse(any(label.startswith("Slot ") for label in selectboxes))
                self.assertNotIn("Mode:", radios)

    def test_optimizer_smoke_script_runs_successfully(self):
        env = os.environ.copy()
        env["TMP"] = str(ROOT / ".cache" / "optimizer-smoke")
        env["TEMP"] = str(ROOT / ".cache" / "optimizer-smoke")
        Path(env["TMP"]).mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [str(PYTHON), "-m", "tools.optimizer_smoke"],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + "\n" + result.stderr)
        self.assertIn("optimizer_smoke: SUCCESS", result.stdout)


if __name__ == "__main__":
    unittest.main()
