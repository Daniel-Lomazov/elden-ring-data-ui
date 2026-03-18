from __future__ import annotations

import unittest
from pathlib import Path

from app_support import load_encounter_profile_request
from optimizer import format_encounter_profile_display_name


ROOT = Path(__file__).resolve().parents[1]


class OptimizationViewSupportTests(unittest.TestCase):
    def test_profile_display_name_omits_extension_and_cleans_separators(self):
        self.assertEqual(
            format_encounter_profile_display_name("Bayle_Phys_Fire_Lightning.yaml"),
            "Bayle Phys Fire Lightning",
        )

    def test_invalid_profile_load_returns_visible_error(self):
        profile, error = load_encounter_profile_request(ROOT, "missing_profile.yaml")
        self.assertIsNone(profile)
        self.assertIsNotNone(error)
        self.assertIn("could not be found", error)


if __name__ == "__main__":
    unittest.main()
