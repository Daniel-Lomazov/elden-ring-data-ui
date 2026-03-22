from __future__ import annotations

import unittest

import pandas as pd

from app_support import (
    DATASET_FAMILY_ARMOR,
    DATASET_FAMILY_CATALOG,
    DATASET_FAMILY_TALISMAN,
    list_supported_datasets,
    resolve_dataset_ui_spec,
    resolve_default_view,
    resolve_rankable_numeric_fields,
)


class DatasetUiRegistryTests(unittest.TestCase):
    def test_supported_dataset_list_excludes_upgrade_tables(self):
        available = [
            "armors",
            "talismans",
            "weapons",
            "weapons_upgrades",
            "shields_upgrades",
            "items/remembrances",
        ]

        supported = list_supported_datasets(available)

        self.assertEqual(
            supported,
            ("armors", "talismans", "weapons", "items/remembrances"),
        )

    def test_registry_exposes_expected_families_and_capabilities(self):
        armor_spec = resolve_dataset_ui_spec("armors")
        talisman_spec = resolve_dataset_ui_spec("talismans")
        catalog_spec = resolve_dataset_ui_spec("items/bells")
        unsupported_spec = resolve_dataset_ui_spec("weapons_upgrades")

        self.assertIsNotNone(armor_spec)
        self.assertEqual(armor_spec.family, DATASET_FAMILY_ARMOR)
        self.assertTrue(armor_spec.supports_optimization)

        self.assertIsNotNone(talisman_spec)
        self.assertEqual(talisman_spec.family, DATASET_FAMILY_TALISMAN)
        self.assertTrue(talisman_spec.supports_optimization)

        self.assertIsNotNone(catalog_spec)
        self.assertEqual(catalog_spec.family, DATASET_FAMILY_CATALOG)
        self.assertFalse(catalog_spec.supports_optimization)

        self.assertIsNotNone(unsupported_spec)
        self.assertIsNotNone(unsupported_spec.unsupported_reason)

    def test_default_view_resolver_matches_dataset_family(self):
        self.assertEqual(resolve_default_view(resolve_dataset_ui_spec("armors")), "Detailed view")
        self.assertEqual(resolve_default_view(resolve_dataset_ui_spec("talismans")), "Detailed view")
        self.assertEqual(resolve_default_view(resolve_dataset_ui_spec("weapons")), "Catalog")

    def test_generic_rankable_numeric_fields_exclude_id_and_dlc(self):
        spec = resolve_dataset_ui_spec("items/remembrances")
        frame = pd.DataFrame(
            {
                "id": [1, 2],
                "name": ["A", "B"],
                "value": [100, 200],
                "weight": [1.0, 2.0],
                "dlc": [0, 0],
            }
        )

        fields = resolve_rankable_numeric_fields(frame, spec)

        self.assertEqual(fields, ("value", "weight"))

    def test_armor_rankable_numeric_fields_follow_curated_order(self):
        spec = resolve_dataset_ui_spec("armors")
        frame = pd.DataFrame(
            {
                "id": [1],
                "Dmg: Hol": [4.0],
                "Dmg: Phy": [5.0],
                "Res: Poi.": [10.0],
                "status.poison": [8.0],
                "weight": [7.0],
            }
        )

        fields = resolve_rankable_numeric_fields(frame, spec)

        self.assertEqual(fields, ("Dmg: Phy", "Dmg: Hol", "status.poison", "Res: Poi."))


if __name__ == "__main__":
    unittest.main()
