from __future__ import annotations

import unittest
from pathlib import Path
import shutil

from optimizer import (
    list_weighted_stat_presets,
    load_weighted_stat_preset,
    save_weighted_stat_preset,
)

ROOT = Path(__file__).resolve().parents[1]
TEST_TEMP_ROOT = ROOT / ".cache" / "optimizer-presets-tests"


class OptimizerPresetTests(unittest.TestCase):
    def setUp(self):
        TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(TEST_TEMP_ROOT, ignore_errors=True)

    def test_save_and_load_weighted_stat_preset_round_trip(self):
        root = TEST_TEMP_ROOT / "round-trip"
        preset, error = save_weighted_stat_preset(
            root,
            label="Fire Defense Weighted",
            dataset="armors",
            selected_stats=["Dmg: Fir", "Res: Poi.", "weight"],
            weights={"Dmg: Fir": 2.0, "Res: Poi.": 1.0, "weight": 0.5},
            optimize_with_weight=True,
        )
        self.assertIsNone(error)
        self.assertIsNotNone(preset)

        loaded, load_error = load_weighted_stat_preset(root, "fire-defense-weighted")
        self.assertIsNone(load_error)
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded.label, "Fire Defense Weighted")
        self.assertEqual(loaded.datasets, ("armors",))
        self.assertEqual(loaded.selected_stats, ("Dmg: Fir", "Res: Poi.", "weight"))
        self.assertTrue(loaded.optimize_with_weight)
        self.assertAlmostEqual(loaded.weights["Dmg: Fir"], 2.0)

    def test_list_weighted_stat_presets_filters_by_dataset(self):
        root = TEST_TEMP_ROOT / "dataset-filter"
        save_weighted_stat_preset(
            root,
            label="Armor Weight Mix",
            dataset="armors",
            selected_stats=["Dmg: Mag", "weight"],
            weights={"Dmg: Mag": 1.0, "weight": 0.4},
            optimize_with_weight=True,
        )
        save_weighted_stat_preset(
            root,
            label="Talisman Damage Mix",
            dataset="talismans",
            selected_stats=["Dmg: Mag", "Dmg: Hol"],
            weights={"Dmg: Mag": 1.0, "Dmg: Hol": 2.0},
            optimize_with_weight=False,
        )

        armor_presets = list_weighted_stat_presets(root, dataset="armors")
        talisman_presets = list_weighted_stat_presets(root, dataset="talismans")

        self.assertEqual([preset.label for preset in armor_presets], ["Armor Weight Mix"])
        self.assertEqual([preset.label for preset in talisman_presets], ["Talisman Damage Mix"])


if __name__ == "__main__":
    unittest.main()
