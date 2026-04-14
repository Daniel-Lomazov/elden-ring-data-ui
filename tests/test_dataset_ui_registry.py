from __future__ import annotations

import unittest

import pandas as pd

from app_support import (
    DATASET_FAMILY_ARMOR,
    DATASET_FAMILY_CATALOG,
    DATASET_FAMILY_PROGRESSION,
    DATASET_FAMILY_TALISMAN,
    DatasetUiSpec,
    format_dataset_selector_label,
    list_supported_datasets,
    list_visible_datasets,
    resolve_dataset_ui_spec,
    resolve_default_view,
    resolve_rankable_numeric_fields,
)


class DatasetUiRegistryTests(unittest.TestCase):
    def test_visible_dataset_list_hides_untouched_item_catalogs(self):
        available = [
            "armors",
            "talismans",
            "items/bells",
            "items/remembrances",
            "weapons_upgrades",
        ]

        visible = list_visible_datasets(available)

        self.assertEqual(
            visible,
            (
                "armors",
                "talismans",
                "weapons_upgrades",
            ),
        )

    def test_supported_dataset_list_includes_upgrade_tables(self):
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
            (
                "armors",
                "talismans",
                "weapons",
                "weapons_upgrades",
                "shields_upgrades",
                "items/remembrances",
            ),
        )

    def test_selector_label_marks_deferred_registry_entries(self):
        unsupported_spec = DatasetUiSpec(
            dataset_key="future_dataset",
            label="Future Dataset",
            family="unsupported",
            supported_views=tuple(),
            supported_scopes=tuple(),
            supports_ranking=False,
            supports_multi_stat_sort=False,
            supports_optimization=False,
            default_sort_field="id",
            card_meta_fields=tuple(),
            detail_fields=tuple(),
            loader_profile=None,
            unsupported_reason="Renderer pending.",
        )

        self.assertEqual(
            format_dataset_selector_label(unsupported_spec),
            "Future Dataset (Not implemented yet)",
        )

    def test_registry_exposes_expected_families_and_capabilities(self):
        armor_spec = resolve_dataset_ui_spec("armors")
        talisman_spec = resolve_dataset_ui_spec("talismans")
        weapons_spec = resolve_dataset_ui_spec("weapons")
        shields_spec = resolve_dataset_ui_spec("shields")
        catalog_spec = resolve_dataset_ui_spec("items/bells")
        progression_spec = resolve_dataset_ui_spec("weapons_upgrades")

        self.assertIsNotNone(armor_spec)
        self.assertEqual(armor_spec.family, DATASET_FAMILY_ARMOR)
        self.assertTrue(armor_spec.supports_optimization)

        self.assertIsNotNone(talisman_spec)
        self.assertEqual(talisman_spec.family, DATASET_FAMILY_TALISMAN)
        self.assertTrue(talisman_spec.supports_optimization)

        self.assertIsNotNone(weapons_spec)
        self.assertEqual(weapons_spec.family, DATASET_FAMILY_CATALOG)
        self.assertFalse(weapons_spec.supports_optimization)
        self.assertEqual(weapons_spec.supported_views, ("Detailed view", "Catalog"))
        self.assertEqual(weapons_spec.supported_scopes, ("Single",))

        self.assertIsNotNone(shields_spec)
        self.assertEqual(shields_spec.family, DATASET_FAMILY_CATALOG)
        self.assertFalse(shields_spec.supports_optimization)
        self.assertEqual(shields_spec.supported_views, ("Detailed view", "Catalog"))
        self.assertEqual(shields_spec.supported_scopes, ("Single",))

        self.assertIsNotNone(catalog_spec)
        self.assertEqual(catalog_spec.family, DATASET_FAMILY_CATALOG)
        self.assertFalse(catalog_spec.supports_optimization)

        self.assertIsNotNone(progression_spec)
        self.assertEqual(progression_spec.family, DATASET_FAMILY_PROGRESSION)
        self.assertFalse(progression_spec.supports_ranking)
        self.assertIsNone(progression_spec.unsupported_reason)
        self.assertEqual(progression_spec.loader_profile, "progression_table_visual")

    def test_default_view_resolver_matches_dataset_family(self):
        self.assertEqual(resolve_default_view(resolve_dataset_ui_spec("armors")), "Detailed view")
        self.assertEqual(resolve_default_view(resolve_dataset_ui_spec("talismans")), "Detailed view")
        self.assertEqual(resolve_default_view(resolve_dataset_ui_spec("weapons")), "Detailed view")
        self.assertEqual(resolve_default_view(resolve_dataset_ui_spec("shields")), "Detailed view")
        self.assertEqual(resolve_default_view(resolve_dataset_ui_spec("weapons_upgrades")), "Catalog")

    def test_progression_dataset_profiles_are_shared_and_explicit(self):
        weapons_progression = resolve_dataset_ui_spec("weapons_upgrades")
        shields_progression = resolve_dataset_ui_spec("shields_upgrades")

        self.assertIsNotNone(weapons_progression)
        self.assertIsNotNone(shields_progression)
        self.assertEqual(weapons_progression.loader_profile, "progression_table_visual")
        self.assertEqual(shields_progression.loader_profile, "progression_table_visual")
        self.assertEqual(weapons_progression.default_sort_field, "weapon name")
        self.assertEqual(shields_progression.default_sort_field, "shield name")

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

    def test_progression_datasets_are_browse_only(self):
        spec = resolve_dataset_ui_spec("weapons_upgrades")
        frame = pd.DataFrame(
            {
                "id": [1, 2],
                "weapon name": ["A", "A"],
                "upgrade": ["Standard", "Standard +1"],
                "some_numeric": [10, 20],
            }
        )

        fields = resolve_rankable_numeric_fields(frame, spec)

        self.assertEqual(fields, tuple())


if __name__ == "__main__":
    unittest.main()
