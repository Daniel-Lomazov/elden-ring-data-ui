from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_SMOKE_TEMP_ROOT = ROOT / ".cache" / "ui-smoke"
UI_SMOKE_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
os.environ["TMP"] = str(UI_SMOKE_TEMP_ROOT)
os.environ["TEMP"] = str(UI_SMOKE_TEMP_ROOT)

_ORIGINAL_TEMP_CLEANUP = tempfile.TemporaryDirectory._cleanup.__func__


@classmethod
def _patched_temp_cleanup(cls, name, warn_message, ignore_errors=False):
    # Streamlit's test harness can leave Windows temp dirs in a locked state.
    try:
        return _ORIGINAL_TEMP_CLEANUP(cls, name, warn_message, True)
    except PermissionError:
        return None


tempfile.TemporaryDirectory._cleanup = _patched_temp_cleanup

from streamlit.testing.v1 import AppTest, element_tree
from streamlit.testing.v1 import app_test as app_test_module


def _patch_unknown_block_init(self, proto, root):
    # Streamlit 1.28 testing can emit container blocks without a typed subtype.
    self.children = {}
    self.proto = proto
    self.root = root
    if proto:
        self.type = proto.WhichOneof("type") or "unknown"
    else:
        self.type = "unknown"


def _patched_multiselect_indices(self):
    # The test harness can report internal stat keys while exposing display labels as options.
    return [self.options.index(str(v)) for v in self.value if str(v) in self.options]


class UiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._original_block_init = element_tree.Block.__init__
        cls._original_multiselect_indices = element_tree.Multiselect.indices

        element_tree.Block.__init__ = _patch_unknown_block_init
        element_tree.Multiselect.indices = property(_patched_multiselect_indices)

        tmp_dir = getattr(app_test_module, "TMP_DIR", None)
        finalizer = getattr(tmp_dir, "_finalizer", None)
        if finalizer is not None:
            finalizer.detach()

    @classmethod
    def tearDownClass(cls):
        element_tree.Block.__init__ = cls._original_block_init
        element_tree.Multiselect.indices = cls._original_multiselect_indices
        shutil.rmtree(UI_SMOKE_TEMP_ROOT, ignore_errors=True)
        tmp_dir = getattr(app_test_module, "TMP_DIR", None)
        if tmp_dir is not None:
            shutil.rmtree(tmp_dir.name, ignore_errors=True)
        tempfile.TemporaryDirectory._cleanup = classmethod(_ORIGINAL_TEMP_CLEANUP)

    def _new_app(self) -> AppTest:
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
        app.run(timeout=60)
        self.assertEqual(len(app.exception), 0)
        return app

    def test_detailed_view_loads_core_controls(self):
        app = self._new_app()

        selectboxes = {widget.label: widget.value for widget in app.selectbox}
        buttons = [widget.label for widget in app.button]

        self.assertEqual(selectboxes["Choose Dataset:"], "Armors")
        self.assertEqual(selectboxes["Choose View:"], "Detailed view")
        self.assertEqual(selectboxes["Choose Scope:"], "Single")
        self.assertIn("Choose Piece:", selectboxes)
        self.assertIn("Select Random Armor Piece", buttons)

    def test_optimization_view_supports_key_smoke_flow(self):
        app = self._new_app()

        next(widget for widget in app.selectbox if widget.label == "Choose View:").select(
            "Optimization view"
        ).run(timeout=60)
        self.assertEqual(len(app.exception), 0)

        selectboxes = {widget.label: widget.value for widget in app.selectbox}
        checkboxes = {widget.label: widget.value for widget in app.checkbox}
        buttons = [widget.label for widget in app.button]

        self.assertEqual(selectboxes["Optimization engine"], "Legacy")
        self.assertEqual(selectboxes["Objective"], "stat_rank")
        self.assertEqual(selectboxes["Optimization method"], "maximin_normalized")
        self.assertEqual(selectboxes["Choose Scope:"], "Single")
        self.assertEqual(selectboxes["Piece type:"], "Armor")
        self.assertFalse(checkboxes["Optimize with weight"])
        self.assertFalse(checkboxes["Use max weight constraint"])
        self.assertIn("Reset filters/stats", buttons)
        self.assertTrue(
            next(widget for widget in app.multiselect if widget.label == "Highlighted stats:").value
        )

        next(widget for widget in app.checkbox if widget.label == "Optimize with weight").set_value(
            True
        ).run(timeout=60)
        self.assertEqual(len(app.exception), 0)

        next(
            widget for widget in app.checkbox if widget.label == "Use max weight constraint"
        ).set_value(True).run(timeout=60)
        self.assertEqual(len(app.exception), 0)

        checkboxes = {widget.label: widget.value for widget in app.checkbox}
        number_inputs = {widget.label: widget.value for widget in app.number_input}
        self.assertTrue(checkboxes["Optimize with weight"])
        self.assertTrue(checkboxes["Use max weight constraint"])
        self.assertIn("Max weight:", number_inputs)

        next(widget for widget in app.selectbox if widget.label == "Choose Scope:").select(
            "Full"
        ).run(timeout=60)
        self.assertEqual(len(app.exception), 0)

        selectboxes = {widget.label: widget.value for widget in app.selectbox}
        self.assertEqual(selectboxes["Choose Scope:"], "Full")
        self.assertNotIn("Piece type:", selectboxes)


if __name__ == "__main__":
    unittest.main()
