"""Canonical optimizer schema constants for Optimizer Dialect v1.

This module is intentionally read-only scaffolding in PR1.
It does not change current ranking behavior.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Final, Tuple

CANONICAL_SCHEMA_VERSION: Final[int] = 1

# Optimization scopes
SCOPE_SINGLE_PIECE: Final[str] = "single_piece"
SCOPE_PER_SLOT: Final[str] = "per_slot"
SCOPE_FULL_SET: Final[str] = "full_set"
SCOPE_COMPLETE_LOADOUT: Final[str] = "complete_loadout"

SCOPES: Final[Tuple[str, ...]] = (
    SCOPE_SINGLE_PIECE,
    SCOPE_PER_SLOT,
    SCOPE_FULL_SET,
    SCOPE_COMPLETE_LOADOUT,
)

# Objective types currently implemented in the optimizer API
OBJECTIVE_STAT_RANK: Final[str] = "stat_rank"
OBJECTIVE_ENCOUNTER_SURVIVAL: Final[str] = "encounter_survival"

OBJECTIVE_TYPES: Final[Tuple[str, ...]] = (
    OBJECTIVE_STAT_RANK,
    OBJECTIVE_ENCOUNTER_SURVIVAL,
)

# Armor-facing core stats
STAT_WEIGHT: Final[str] = "weight"
STAT_POISE: Final[str] = "poise"

# Negation keys
NEG_PHYS: Final[str] = "neg.phys"
NEG_STD: Final[str] = "neg.std"
NEG_STR: Final[str] = "neg.str"
NEG_SLA: Final[str] = "neg.sla"
NEG_PIE: Final[str] = "neg.pie"
NEG_MAG: Final[str] = "neg.mag"
NEG_FIR: Final[str] = "neg.fir"
NEG_LIT: Final[str] = "neg.lit"
NEG_HOL: Final[str] = "neg.hol"

NEGATION_KEYS: Final[Tuple[str, ...]] = (
    NEG_PHYS,
    NEG_STD,
    NEG_STR,
    NEG_SLA,
    NEG_PIE,
    NEG_MAG,
    NEG_FIR,
    NEG_LIT,
    NEG_HOL,
)

# Resistance keys
RES_IMM: Final[str] = "res.imm"
RES_ROB: Final[str] = "res.rob"
RES_FOC: Final[str] = "res.foc"
RES_VIT: Final[str] = "res.vit"

RESISTANCE_KEYS: Final[Tuple[str, ...]] = (
    RES_IMM,
    RES_ROB,
    RES_FOC,
    RES_VIT,
)

# Encounter-facing status channels
STATUS_POISON: Final[str] = "status.poison"
STATUS_ROT: Final[str] = "status.rot"
STATUS_BLEED: Final[str] = "status.bleed"
STATUS_FROST: Final[str] = "status.frost"
STATUS_SLEEP: Final[str] = "status.sleep"
STATUS_MADNESS: Final[str] = "status.madness"
STATUS_DEATH: Final[str] = "status.death"

STATUS_KEYS: Final[Tuple[str, ...]] = (
    STATUS_POISON,
    STATUS_ROT,
    STATUS_BLEED,
    STATUS_FROST,
    STATUS_SLEEP,
    STATUS_MADNESS,
    STATUS_DEATH,
)

STATUS_TO_RESISTANCE: Final[Dict[str, str]] = {
    STATUS_POISON: RES_IMM,
    STATUS_ROT: RES_IMM,
    STATUS_BLEED: RES_ROB,
    STATUS_FROST: RES_ROB,
    STATUS_SLEEP: RES_FOC,
    STATUS_MADNESS: RES_FOC,
    STATUS_DEATH: RES_VIT,
}


@dataclass(frozen=True)
class CanonicalStat:
    key: str
    category: str
    direction: str
    label: str


CANONICAL_STATS: Final[Dict[str, CanonicalStat]] = {
    STAT_WEIGHT: CanonicalStat(STAT_WEIGHT, "armor_stat", "minimize", "Weight"),
    STAT_POISE: CanonicalStat(STAT_POISE, "armor_stat", "maximize", "Poise"),
    NEG_PHYS: CanonicalStat(NEG_PHYS, "negation", "maximize", "Physical"),
    NEG_STD: CanonicalStat(NEG_STD, "negation", "maximize", "Standard"),
    NEG_STR: CanonicalStat(NEG_STR, "negation", "maximize", "Strike"),
    NEG_SLA: CanonicalStat(NEG_SLA, "negation", "maximize", "Slash"),
    NEG_PIE: CanonicalStat(NEG_PIE, "negation", "maximize", "Pierce"),
    NEG_MAG: CanonicalStat(NEG_MAG, "negation", "maximize", "Magic"),
    NEG_FIR: CanonicalStat(NEG_FIR, "negation", "maximize", "Fire"),
    NEG_LIT: CanonicalStat(NEG_LIT, "negation", "maximize", "Lightning"),
    NEG_HOL: CanonicalStat(NEG_HOL, "negation", "maximize", "Holy"),
    RES_IMM: CanonicalStat(RES_IMM, "resistance", "maximize", "Immunity"),
    RES_ROB: CanonicalStat(RES_ROB, "resistance", "maximize", "Robustness"),
    RES_FOC: CanonicalStat(RES_FOC, "resistance", "maximize", "Focus"),
    RES_VIT: CanonicalStat(RES_VIT, "resistance", "maximize", "Vitality"),
}


def is_canonical_key(key: str) -> bool:
    return key in CANONICAL_STATS or key in STATUS_KEYS


@lru_cache(maxsize=1)
def load_armor_stat_schema() -> dict:
    schema_path = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "armor_stat_schema.json"
    )
    with schema_path.open("r", encoding="utf-8") as file:
        return json.load(file)


@lru_cache(maxsize=1)
def canonical_to_df_column_map() -> Dict[str, str]:
    mapping = load_armor_stat_schema().get("mapping", [])
    out: Dict[str, str] = {}
    for row in mapping:
        if isinstance(row, dict):
            key = row.get("canonical_key")
            col = row.get("df_column_name")
            if isinstance(key, str) and isinstance(col, str):
                out[key] = col
    return out


def resolve_df_column_for_canonical_key(canonical_key: str) -> str:
    return canonical_to_df_column_map().get(canonical_key, canonical_key)
