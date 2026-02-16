from __future__ import annotations

import unittest

from optimizer import load_request


class DialectValidationTests(unittest.TestCase):
    def test_valid_request_loads(self):
        request = load_request(
            {
                "version": 1,
                "scope": "single_piece",
                "objective": {"type": "encounter_survival"},
                "encounter": {"incoming": {"damage_mix": {"neg.mag": 1.0}}},
            }
        )
        self.assertEqual(request["objective"]["type"], "encounter_survival")

    def test_invalid_damage_mix_key_fails(self):
        with self.assertRaises(ValueError):
            load_request(
                {
                    "version": 1,
                    "scope": "single_piece",
                    "objective": {"type": "encounter_survival"},
                    "encounter": {"incoming": {"damage_mix": {"magic": 1.0}}},
                }
            )


if __name__ == "__main__":
    unittest.main()
