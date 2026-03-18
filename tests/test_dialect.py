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
        self.assertEqual(request["engine"], "advanced")

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

    def test_missing_engine_infers_legacy_for_stat_rank(self):
        request = load_request(
            {
                "version": 1,
                "scope": "single_piece",
                "objective": {"type": "stat_rank", "method": "maximin_normalized"},
                "selected_stats": ["Dmg: Phy", "Dmg: Mag"],
            }
        )
        self.assertEqual(request["engine"], "legacy")

    def test_legacy_engine_rejects_encounter_survival(self):
        with self.assertRaises(ValueError):
            load_request(
                {
                    "version": 1,
                    "engine": "legacy",
                    "scope": "single_piece",
                    "objective": {"type": "encounter_survival"},
                    "encounter": {"incoming": {"damage_mix": {"neg.mag": 1.0}}},
                }
            )


if __name__ == "__main__":
    unittest.main()
