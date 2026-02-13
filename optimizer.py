"""UI-agnostic optimization strategies for armor piece ranking."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

import pandas as pd


OptimizerStrategy = Callable[[pd.DataFrame, List[str], Optional[dict]], pd.DataFrame]

DEFAULT_OPTIMIZATION_METHOD = "maximin_normalized"


def _is_minimize_stat(stat: str) -> bool:
    return str(stat).strip().lower() == "weight"


def _normalized_view(df: pd.DataFrame, stats: List[str]) -> pd.DataFrame:
    numeric = df[stats].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    mins = numeric.min()
    maxs = numeric.max()
    ranges = (maxs - mins).replace(0, 1.0)
    normalized = (numeric - mins) / ranges

    # Objective direction: maximize everything except weight, which should be minimized.
    for stat in stats:
        if _is_minimize_stat(stat):
            normalized[stat] = 1.0 - normalized[stat]

    return normalized


def _score_maximin_normalized(
    df: pd.DataFrame, stats: List[str], config: Optional[dict] = None
) -> pd.DataFrame:
    normalized = _normalized_view(df, stats)
    score = normalized.min(axis=1)
    tiebreak = normalized.mean(axis=1)

    out = df.copy()
    out["__opt_score"] = score
    out["__opt_tiebreak"] = tiebreak
    out["__opt_method"] = DEFAULT_OPTIMIZATION_METHOD
    out["__opt_length"] = len(stats)
    for stat in stats:
        out[f"Norm: {stat}"] = normalized[stat]
    out = out.sort_values(
        by=["__opt_score", "__opt_tiebreak"], ascending=[False, False]
    ).reset_index(drop=True)
    out["__opt_rank"] = out.index + 1
    return out


def _score_weighted_sum_normalized(
    df: pd.DataFrame, stats: List[str], config: Optional[dict] = None
) -> pd.DataFrame:
    normalized = _normalized_view(df, stats)
    cfg = config or {}
    raw_weights = cfg.get("weights")
    if isinstance(raw_weights, dict):
        weights = [float(raw_weights.get(s, 1.0)) for s in stats]
    elif isinstance(raw_weights, list) and len(raw_weights) == len(stats):
        weights = [float(w) for w in raw_weights]
    else:
        weights = [1.0 for _ in stats]

    total = sum(weights) if sum(weights) > 0 else 1.0
    weighted = sum(normalized[s] * w for s, w in zip(stats, weights)) / total
    tiebreak = normalized.min(axis=1)

    out = df.copy()
    out["__opt_score"] = weighted
    out["__opt_tiebreak"] = tiebreak
    out["__opt_method"] = "weighted_sum_normalized"
    out["__opt_length"] = len(stats)
    for stat in stats:
        out[f"Norm: {stat}"] = normalized[stat]
    out = out.sort_values(
        by=["__opt_score", "__opt_tiebreak"], ascending=[False, False]
    ).reset_index(drop=True)
    out["__opt_rank"] = out.index + 1
    return out


OPTIMIZER_METHODS: Dict[str, OptimizerStrategy] = {
    "maximin_normalized": _score_maximin_normalized,
    "weighted_sum_normalized": _score_weighted_sum_normalized,
}


def optimize_single_piece(
    df: pd.DataFrame,
    selected_stats: List[str],
    method: str = DEFAULT_OPTIMIZATION_METHOD,
    config: Optional[dict] = None,
) -> pd.DataFrame:
    """Rank armor pieces using the selected optimization strategy.

    Designed for single-piece optimization today, while accepting an arbitrary
    number of selected stats to make future N-objective expansion straightforward.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    stats = [s for s in selected_stats if s in df.columns]
    if len(stats) < 2:
        raise ValueError("At least 2 valid stats are required for optimization.")

    strategy = OPTIMIZER_METHODS.get(method)
    if strategy is None:
        raise ValueError(f"Unknown optimization method: {method}")

    return strategy(df, stats, config)
