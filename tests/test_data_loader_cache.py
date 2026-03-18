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


if __name__ == "__main__":
    unittest.main()
