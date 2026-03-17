"""Full-set armor optimization with pruning-first enumeration (PR5)."""

from __future__ import annotations

import itertools
from typing import Dict, List, Set

import pandas as pd

from ..constraints import apply_row_constraints
from ..features.armor import SLOT_ORDER, split_armor_by_slot
from ..schema import canonical_to_df_column_map
from .encounter_survival import optimize_encounter_survival


def _aggregate_combo_rows(rows: List[pd.Series], canonical_request: dict) -> dict:
    canonical_map = canonical_to_df_column_map()
    row = {
        "set_items": [str(item.get("name", "")) for item in rows],
        "Helm": str(rows[0].get("name", "")),
        "Armor": str(rows[1].get("name", "")),
        "Gauntlets": str(rows[2].get("name", "")),
        "Greaves": str(rows[3].get("name", "")),
    }

    total_weight = 0.0
    total_poise = 0.0
    for item in rows:
        total_weight += float(pd.to_numeric(item.get("weight", 0.0), errors="coerce") or 0.0)
        poise_col = canonical_map.get("poise", "Res: Poi.")
        total_poise += float(pd.to_numeric(item.get(poise_col, 0.0), errors="coerce") or 0.0)

    row["total_weight"] = total_weight
    row["total_poise"] = total_poise

    incoming = ((canonical_request.get("encounter") or {}).get("incoming") or {})
    damage_mix = (incoming.get("damage_mix") or {})
    used_keys = set(damage_mix.keys())

    status_keys = ((canonical_request.get("encounter") or {}).get("status_threats") or {}).keys()
    from ..schema import STATUS_TO_RESISTANCE

    for status_key in status_keys:
        resistance_key = STATUS_TO_RESISTANCE.get(status_key)
        if resistance_key:
            used_keys.add(resistance_key)

    for canonical_key in used_keys:
        col = canonical_map.get(canonical_key)
        if not col:
            continue
        row[col] = sum(float(pd.to_numeric(item.get(col, 0.0), errors="coerce") or 0.0) for item in rows)

    return row


def _merge_locked_rows(
    pruned_df: pd.DataFrame,
    slot_df: pd.DataFrame,
    locked_names: Set[str],
) -> pd.DataFrame:
    if not locked_names or "name" not in slot_df.columns:
        return pruned_df.reset_index(drop=True)

    locked_rows = slot_df[slot_df["name"].astype(str).isin(locked_names)]
    if locked_rows.empty:
        return pruned_df.reset_index(drop=True)

    merged = pd.concat([pruned_df, locked_rows], ignore_index=True)
    return merged.drop_duplicates(subset=["name"], keep="first").reset_index(drop=True)


def _prune_slot(
    slot_df: pd.DataFrame,
    request: dict,
    top_k: int,
    locked_names: Set[str],
) -> pd.DataFrame:
    if slot_df.empty:
        return slot_df

    req = dict(request)
    req["scope"] = "single_piece"
    req_obj = dict(req.get("objective") or {})
    req_obj["lambda_status"] = 0.0
    req["objective"] = req_obj

    scored = optimize_encounter_survival(slot_df, req)
    return _merge_locked_rows(scored.head(top_k).copy(), slot_df, locked_names)


def optimize_encounter_survival_full_set(df: pd.DataFrame, request: dict) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    constraints = request.get("constraints") or {}
    locked_names = {
        str(name).strip()
        for name in (constraints.get("include_names") or [])
        if str(name).strip()
    }
    top_k = int(constraints.get("top_k_per_slot", 25))
    top_n = int(constraints.get("top_n", 50))

    slot_map = split_armor_by_slot(df)
    if any(slot_map[slot].empty for slot in SLOT_ORDER):
        return pd.DataFrame()

    pruned: Dict[str, pd.DataFrame] = {
        slot: _prune_slot(slot_map[slot], request, top_k, locked_names) for slot in SLOT_ORDER
    }

    combos = itertools.product(
        pruned["helm"].iterrows(),
        pruned["armor"].iterrows(),
        pruned["gauntlets"].iterrows(),
        pruned["greaves"].iterrows(),
    )

    aggregated_rows = []
    for (_, helm), (_, armor), (_, gauntlets), (_, greaves) in combos:
        aggregated_rows.append(
            _aggregate_combo_rows([helm, armor, gauntlets, greaves], request)
        )

    if not aggregated_rows:
        return pd.DataFrame()

    combo_df = pd.DataFrame(aggregated_rows)
    combo_df = apply_row_constraints(combo_df, constraints)
    if combo_df.empty:
        return combo_df

    req = dict(request)
    req["scope"] = "single_piece"
    ranked = optimize_encounter_survival(combo_df, req)
    return ranked.head(top_n).reset_index(drop=True)
