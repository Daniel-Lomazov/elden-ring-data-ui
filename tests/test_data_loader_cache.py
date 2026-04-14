from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4
import unittest

from data_loader import DataLoader


class DataLoaderCacheTests(unittest.TestCase):
    def test_load_file_reflects_modified_csv_contents(self):
        path = Path(__file__).resolve().parent / f"sample_{uuid4().hex}.csv"
        try:
            path.write_text("name,value\nalpha,1\n", encoding="utf-8")

            first = DataLoader.load_file(str(path))
            self.assertIsNotNone(first)
            self.assertEqual(int(first.iloc[0]["value"]), 1)

            path.write_text("name,value\nalpha,2\n", encoding="utf-8")

            second = DataLoader.load_file(str(path))
            self.assertIsNotNone(second)
            self.assertEqual(int(second.iloc[0]["value"]), 2)
        finally:
            path.unlink(missing_ok=True)

    def test_load_column_instructions_reflects_modified_json(self):
        path = Path(__file__).resolve().parent / f"instructions_{uuid4().hex}.json"
        try:
            path.write_text(
                json.dumps(
                    {
                        "profiles": {
                            "basic": {
                                "include": ["value"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            first = DataLoader.load_column_instructions(str(path))
            self.assertEqual(first["profiles"]["basic"]["include"], ["value"])

            path.write_text(
                json.dumps(
                    {
                        "profiles": {
                            "basic": {
                                "include": ["value", "weight"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            second = DataLoader.load_column_instructions(str(path))
            self.assertEqual(second["profiles"]["basic"]["include"], ["value", "weight"])
        finally:
            path.unlink(missing_ok=True)

    def test_build_profile_columns_allows_dataset_specific_identity_columns(self):
        path = Path(__file__).resolve().parent / f"progression_{uuid4().hex}.json"
        try:
            path.write_text(
                json.dumps(
                    {
                        "always_include": ["id", "name"],
                        "profiles": {
                            "progression_table_visual": {
                                "include": ["upgrade", "attack power"],
                            }
                        },
                        "dataset_overrides": {
                            "weapons_upgrades": {
                                "always_include": ["id", "weapon name"],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            columns = DataLoader().build_profile_columns(
                "weapons_upgrades",
                profile_name="progression_table_visual",
                instructions_path=str(path),
            )

            self.assertEqual(columns, ("id", "weapon name", "upgrade", "attack power"))
        finally:
            path.unlink(missing_ok=True)

    def test_progression_profile_loads_real_upgrade_tables(self):
        root = Path(__file__).resolve().parents[1]
        loader = DataLoader(data_dir=str(root / "data"))

        weapons_df = loader.load_dataset_by_profile("weapons_upgrades", "progression_table_visual")
        shields_df = loader.load_dataset_by_profile("shields_upgrades", "progression_table_visual")

        self.assertIsNotNone(weapons_df)
        self.assertIsNotNone(shields_df)

        self.assertEqual(
            tuple(weapons_df.columns),
            ("id", "weapon name", "upgrade", "attack power", "stat scaling", "passive effects", "damage reduction (%)"),
        )
        self.assertEqual(
            tuple(shields_df.columns),
            ("id", "shield name", "upgrade", "attack power", "stat scaling", "passive effects", "damage reduction (%)"),
        )

        weapons_full = DataLoader.load_file(str(root / "data" / "weapons_upgrades.csv"))
        shields_full = DataLoader.load_file(str(root / "data" / "shields_upgrades.csv"))

        self.assertIsNotNone(weapons_full)
        self.assertIsNotNone(shields_full)
        self.assertEqual(len(weapons_df), len(weapons_full))
        self.assertEqual(len(shields_df), len(shields_full))


if __name__ == "__main__":
    unittest.main()
