"""Constraint helpers for dialect optimization."""

from __future__ import annotations

import pandas as pd

DEFAULT_ROLL_LIMITS = {
    "light": 30.0,
    "medium": 70.0,
    "heavy": 100.0,
}


def resolve_max_weight(constraints: dict) -> float | None:
    if not isinstance(constraints, dict):
        return None
    if constraints.get("max_weight") is not None:
        return float(constraints["max_weight"])
    roll_class = str(constraints.get("roll_class") or "").strip().lower()
    return DEFAULT_ROLL_LIMITS.get(roll_class)


def apply_row_constraints(df: pd.DataFrame, constraints: dict) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    max_weight = resolve_max_weight(constraints)
    if max_weight is not None and "total_weight" in out.columns:
        out = out[out["total_weight"] <= max_weight]

    min_poise = constraints.get("min_poise") if isinstance(constraints, dict) else None
    if min_poise is not None and "total_poise" in out.columns:
        out = out[out["total_poise"] >= float(min_poise)]

    include_names = constraints.get("include_names") if isinstance(constraints, dict) else None
    if isinstance(include_names, list) and include_names and "set_items" in out.columns:
        include_set = {str(name) for name in include_names}
        out = out[
            out["set_items"].apply(
                lambda names: include_set.issubset(set(names)) if isinstance(names, list) else False
            )
        ]

    exclude_names = constraints.get("exclude_names") if isinstance(constraints, dict) else None
    if isinstance(exclude_names, list) and exclude_names and "set_items" in out.columns:
        exclude_set = {str(name) for name in exclude_names}
        out = out[
            out["set_items"].apply(
                lambda names: exclude_set.isdisjoint(set(names)) if isinstance(names, list) else True
            )
        ]

    return out.reset_index(drop=True)
