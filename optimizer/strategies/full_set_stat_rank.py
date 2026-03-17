"""Full-set stat-rank optimization via prune-first enumeration."""

from __future__ import annotations

import itertools
from typing import List

import pandas as pd

from ..constraints import apply_row_constraints
from ..features.armor import SLOT_ORDER, split_armor_by_slot
from ..legacy import (
    DEFAULT_OPTIMIZATION_METHOD,
    optimize_full_set,
    optimize_single_piece,
)


def _to_float(value) -> float:
    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric):
        return 0.0
    return float(numeric)


def _aggregate_combo_rows(rows: List[pd.Series], selected_stats: List[str]) -> dict:
    row = {
        "set_items": [str(item.get("name", "")) for item in rows],
        "Helm": str(rows[0].get("name", "")),
        "Armor": str(rows[1].get("name", "")),
        "Gauntlets": str(rows[2].get("name", "")),
        "Greaves": str(rows[3].get("name", "")),
    }

    total_weight = sum(_to_float(item.get("weight", 0.0)) for item in rows)
    row["total_weight"] = total_weight
    row["weight"] = total_weight

    total_poise = sum(_to_float(item.get("Res: Poi.", 0.0)) for item in rows)
    row["total_poise"] = total_poise

    for stat in selected_stats:
        if stat == "weight":
            continue
        row[stat] = sum(_to_float(item.get(stat, 0.0)) for item in rows)

    return row


def _prune_slot(slot_df: pd.DataFrame, request: dict, selected_stats: List[str], top_k: int) -> pd.DataFrame:
    if slot_df.empty:
        return slot_df

    objective = request.get("objective") or {}
    method = objective.get("method") or DEFAULT_OPTIMIZATION_METHOD
    config = dict(request.get("config") or {})
    if objective.get("weights"):
        config["weights"] = objective["weights"]

    slot_stats = [stat for stat in selected_stats if stat in slot_df.columns]
    if len(slot_stats) < 2:
        return slot_df.head(top_k).copy()

    ranked = optimize_single_piece(
        slot_df,
        selected_stats=slot_stats,
        method=method,
        config=config,
    )
    return ranked.head(top_k).copy()


def optimize_stat_rank_full_set(df: pd.DataFrame, request: dict) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    selected_stats = request.get("selected_stats") or []
    stats = [str(stat) for stat in selected_stats]
    if len(stats) < 2:
        raise ValueError("Full-set stat_rank requires at least 2 selected_stats")

    constraints = request.get("constraints") or {}
    top_k = int(constraints.get("top_k_per_slot", 25))
    top_n = int(constraints.get("top_n", 50))

    slot_map = split_armor_by_slot(df)
    if any(slot_map[slot].empty for slot in SLOT_ORDER):
        return pd.DataFrame()

    pruned = {
        slot: _prune_slot(slot_map[slot], request, stats, top_k)
        for slot in SLOT_ORDER
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
            _aggregate_combo_rows([helm, armor, gauntlets, greaves], stats)
        )

    if not aggregated_rows:
        return pd.DataFrame()

    combo_df = pd.DataFrame(aggregated_rows)
    combo_df = apply_row_constraints(combo_df, constraints)
    if combo_df.empty:
        return combo_df

    objective = request.get("objective") or {}
    method = objective.get("method") or DEFAULT_OPTIMIZATION_METHOD
    config = dict(request.get("config") or {})
    if objective.get("weights"):
        config["weights"] = objective["weights"]

    ranked = optimize_full_set(
        combo_df,
        selected_stats=stats,
        method=method,
        config=config,
    )
    return ranked.head(top_n).reset_index(drop=True)