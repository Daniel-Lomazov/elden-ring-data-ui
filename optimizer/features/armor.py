"""Armor feature helpers for set-based optimization."""

from __future__ import annotations

from typing import Dict

import pandas as pd

SLOT_ORDER = ("helm", "armor", "gauntlets", "greaves")

_SLOT_ALIASES = {
    "helm": "helm",
    "head": "helm",
    "chest armor": "armor",
    "armor": "armor",
    "chest": "armor",
    "gauntlets": "gauntlets",
    "arms": "gauntlets",
    "leg armor": "greaves",
    "greaves": "greaves",
    "legs": "greaves",
}


def normalize_slot(raw_value: str) -> str | None:
    key = str(raw_value or "").strip().lower()
    return _SLOT_ALIASES.get(key)


def split_armor_by_slot(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    if "type" not in df.columns:
        return {slot: pd.DataFrame() for slot in SLOT_ORDER}

    tmp = df.copy()
    tmp["__slot_norm"] = tmp["type"].apply(normalize_slot)

    return {
        slot: tmp[tmp["__slot_norm"] == slot].drop(columns=["__slot_norm"])
        for slot in SLOT_ORDER
    }
