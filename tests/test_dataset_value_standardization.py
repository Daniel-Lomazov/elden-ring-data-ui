from __future__ import annotations

import unittest

from app_support.dataset_presentations import (
    extract_talisman_effect_magnitude,
    format_presentation_value,
    normalize_talisman_effect_type,
)


class DatasetValueStandardizationTests(unittest.TestCase):
    def test_weight_stays_raw_numeric_not_percentage(self):
        self.assertEqual(format_presentation_value("0.3", "weight", field_key="weight"), "0.3")
        self.assertEqual(format_presentation_value(9.0, "weight", field_key="weight"), "9.0")

    def test_fp_cost_preserves_composite_strings_when_needed(self):
        self.assertEqual(format_presentation_value("18", "fp_cost", field_key="FP"), "18")
        self.assertEqual(format_presentation_value("9 (-/-)", "fp_cost", field_key="FP"), "9 (-/-)")

    def test_requirements_map_formats_cleanly(self):
        rendered = format_presentation_value(
            "{'Str': 15, 'Dex': 14}",
            "requirements_map",
            field_key="requirements",
        )
        self.assertEqual(rendered, "STR 15, DEX 14")

    def test_structured_values_flatten_into_readable_text(self):
        rendered_list = format_presentation_value(
            "['Broken Rune', 'Golden Rune (1)']",
            "structured",
            field_key="items",
        )
        rendered_dict = format_presentation_value(
            "{'Belurat': ['120000', 'Remembrance of the Dancing Lion']}",
            "structured",
            field_key="Locations & Drops",
        )
        self.assertEqual(rendered_list, "Broken Rune, Golden Rune (1)")
        self.assertEqual(rendered_dict, "Belurat: 120000, Remembrance of the Dancing Lion")

    def test_talisman_effect_helpers_extract_type_and_magnitude(self):
        effect = "Effect Raises maximum HP by 6%"
        self.assertEqual(normalize_talisman_effect_type(effect), "Raises maximum HP")
        self.assertEqual(extract_talisman_effect_magnitude(effect), "6%")
        self.assertEqual(extract_talisman_effect_magnitude("Effect Raises maximum FP by 7"), "7")


if __name__ == "__main__":
    unittest.main()