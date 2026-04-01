from __future__ import annotations

import unittest

import pandas as pd

from app_support.dataset_presentations import (
    iter_presented_fields,
    normalize_numeric_like_columns,
    resolve_dataset_presentation_spec,
)


class DatasetPresentationTests(unittest.TestCase):
    def test_talisman_presentation_exposes_effect_metadata_and_numeric_value(self):
        spec = resolve_dataset_presentation_spec("talismans")
        frame = pd.DataFrame(
            [
                {
                    "name": "Crimson Amber Medallion",
                    "effect": "Effect Raises maximum HP by 6%",
                    "weight": 0.3,
                    "value": "100",
                    "description": "Boosts maximum HP.",
                    "dlc": 0,
                }
            ]
        )

        normalized = normalize_numeric_like_columns(frame, spec)
        row = normalized.iloc[0]
        card_rows = {field.label: text for field, text in iter_presented_fields(row, spec.card_meta_fields)}
        metric_rows = {field.label: text for field, text in iter_presented_fields(row, spec.card_metric_fields)}

        self.assertTrue(pd.api.types.is_numeric_dtype(normalized["value"]))
        self.assertEqual(card_rows["Effect Type"], "Raises maximum HP")
        self.assertEqual(card_rows["Effect Magnitude"], "6%")
        self.assertEqual(metric_rows["Value"], "100")
        self.assertEqual(metric_rows["Weight"], "0.3")

    def test_spell_presentation_promotes_fp_cost_and_requirements(self):
        spec = resolve_dataset_presentation_spec("incantations")
        frame = pd.DataFrame(
            [
                {
                    "name": "Heal from Afar",
                    "effect": "Greatly heals HP for distant allies the spell reaches",
                    "description": "An Erdtree incantation discovered in the realm of shadow.",
                    "FP": "45",
                    "slot": 1,
                    "INT": 0,
                    "FAI": 18,
                    "ARC": 0,
                    "stamina cost": 40,
                    "bonus": "Two Fingers",
                    "group": "Healing",
                    "location": "Realm of Shadow",
                    "dlc": 1,
                }
            ]
        )

        normalized = normalize_numeric_like_columns(frame, spec)
        row = normalized.iloc[0]
        metric_rows = {field.label: text for field, text in iter_presented_fields(row, spec.card_metric_fields)}

        self.assertTrue(pd.api.types.is_numeric_dtype(normalized["FP"]))
        self.assertEqual(metric_rows["FP"], "45")
        self.assertEqual(metric_rows["Stamina Cost"], "40")
        self.assertEqual(metric_rows["FAI"], "18")

    def test_numeric_normalization_ignores_placeholder_tokens(self):
        spec = resolve_dataset_presentation_spec("talismans")
        frame = pd.DataFrame(
            [
                {"name": "Known", "value": "100"},
                {"name": "Unknown", "value": "???"},
            ]
        )

        normalized = normalize_numeric_like_columns(frame, spec)

        self.assertTrue(pd.api.types.is_numeric_dtype(normalized["value"]))
        self.assertEqual(normalized.loc[0, "value"], 100)
        self.assertTrue(pd.isna(normalized.loc[1, "value"]))

    def test_equipment_presentation_formats_requirements_map(self):
        spec = resolve_dataset_presentation_spec("weapons")
        row = pd.Series(
            {
                "name": "Dueling Shield",
                "category": "Thrusting Shields",
                "damage type": "Standard/Pierce",
                "requirements": "{'Str': 15, 'Dex': 14}",
                "skill": "Shield Strike",
                "passive effect": "No passive effects",
                "weight": 9.0,
                "FP cost": "9",
                "dlc": 1,
            }
        )

        sections = []
        for section in spec.detail_sections:
            sections.extend(list(iter_presented_fields(row, section.fields)))
        section_rows = {field.label: text for field, text in sections}

        self.assertEqual(section_rows["Requirements"], "STR 15, DEX 14")
        self.assertEqual(section_rows["Weight"], "9.0")
        self.assertEqual(section_rows["FP Cost"], "9")

    def test_world_dataset_presentation_parses_serialized_relationships(self):
        spec = resolve_dataset_presentation_spec("locations")
        row = pd.Series(
            {
                "name": "Abandoned Ailing Village",
                "region": "Gravesite Plain",
                "items": "['Broken Rune', 'Golden Rune (1)']",
                "npcs": "['Spirit NPC']",
                "creatures": "['Man-Fly']",
                "bosses": "['Field Boss']",
                "description": "A dilapidated village.",
                "dlc": 1,
            }
        )

        sections = []
        for section in spec.detail_sections:
            sections.extend(list(iter_presented_fields(row, section.fields)))
        section_rows = {field.label: text for field, text in sections}

        self.assertEqual(section_rows["Items"], "Broken Rune, Golden Rune (1)")
        self.assertEqual(section_rows["NPCs"], "Spirit NPC")
        self.assertEqual(section_rows["Edition"], "DLC")


if __name__ == "__main__":
    unittest.main()