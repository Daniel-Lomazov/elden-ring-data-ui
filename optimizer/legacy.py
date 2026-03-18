"""UI-agnostic optimization core for armor ranking scopes.

This module centralizes objective handling and scoring strategies in one place,
with explicit optimization scopes:
- single_piece
- full_set
- complete_set

Current behavior is preserved by keeping single-piece defaults unchanged.
"""

from __future__ import annotations

from typing import Callable, Dict, Iterable, List, Optional

import pandas as pd


OptimizerStrategy = Callable[[pd.DataFrame, List[str], Optional[dict]], pd.DataFrame]

DEFAULT_OPTIMIZATION_METHOD = "maximin_normalized"
DEFAULT_OPTIMIZATION_SCOPE = "single_piece"

OPT_SCOPE_SINGLE_PIECE = "single_piece"
OPT_SCOPE_FULL_SET = "full_set"
OPT_SCOPE_COMPLETE_SET = "complete_set"


def _normalize_stat_name(stat: str) -> str:
    return str(stat).strip().lower()


def _resolve_minimize_stats(config: Optional[dict] = None) -> set[str]:
    cfg = config or {}
    configured = cfg.get("minimize_stats")
    if isinstance(configured, Iterable) and not isinstance(configured, (str, bytes)):
        values = {_normalize_stat_name(item) for item in configured}
        if values:
            return values
    return {"weight"}


def _is_minimize_stat(stat: str, config: Optional[dict] = None) -> bool:
    return _normalize_stat_name(stat) in _resolve_minimize_stats(config)


def _normalized_view(
    df: pd.DataFrame,
    stats: List[str],
    config: Optional[dict] = None,
) -> pd.DataFrame:
    numeric = df[stats].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    mins = numeric.min()
    maxs = numeric.max()
    ranges = (maxs - mins).replace(0, 1.0)
    normalized = (numeric - mins) / ranges

    for stat in stats:
        if _is_minimize_stat(stat, config=config):
            normalized[stat] = 1.0 - normalized[stat]

    return normalized


def _score_maximin_normalized(
    df: pd.DataFrame, stats: List[str], config: Optional[dict] = None
) -> pd.DataFrame:
    normalized = _normalized_view(df, stats, config=config)
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
    normalized = _normalized_view(df, stats, config=config)
    cfg = config or {}
    raw_weights = cfg.get("weights")
    if isinstance(raw_weights, dict):
        weights = [float(raw_weights.get(s, 1.0)) for s in stats]
    elif isinstance(raw_weights, list) and len(raw_weights) == len(stats):
        weights = [float(w) for w in raw_weights]
    else:
        weights = [1.0 for _ in stats]

    active_stats = [s for s, w in zip(stats, weights) if float(w) > 0]
    active_weights = [float(w) for w in weights if float(w) > 0]
    if not active_stats:
        raise ValueError("Weighted Sum requires at least one stat with a weight greater than zero.")

    total = sum(active_weights)
    weighted = sum(normalized[s] * w for s, w in zip(active_stats, active_weights)) / total
    tiebreak = normalized[active_stats].min(axis=1)

    out = df.copy()
    out["__opt_score"] = weighted
    out["__opt_tiebreak"] = tiebreak
    out["__opt_method"] = "weighted_sum_normalized"
    out["__opt_length"] = len(active_stats)
    for stat in stats:
        out[f"Norm: {stat}"] = normalized[stat]
    out = out.sort_values(
        by=["__opt_score", "__opt_tiebreak"], ascending=[False, False]
    ).reset_index(drop=True)
    out["__opt_rank"] = out.index + 1
    return out


_BASE_OPTIMIZER_METHODS: Dict[str, OptimizerStrategy] = {
    "maximin_normalized": _score_maximin_normalized,
    "weighted_sum_normalized": _score_weighted_sum_normalized,
}


OPTIMIZER_METHODS_BY_SCOPE: Dict[str, Dict[str, OptimizerStrategy]] = {
    OPT_SCOPE_SINGLE_PIECE: dict(_BASE_OPTIMIZER_METHODS),
    OPT_SCOPE_FULL_SET: dict(_BASE_OPTIMIZER_METHODS),
    OPT_SCOPE_COMPLETE_SET: dict(_BASE_OPTIMIZER_METHODS),
}


OPTIMIZER_METHODS: Dict[str, OptimizerStrategy] = OPTIMIZER_METHODS_BY_SCOPE[
    OPT_SCOPE_SINGLE_PIECE
]


def get_optimizer_methods(scope: str = DEFAULT_OPTIMIZATION_SCOPE) -> Dict[str, OptimizerStrategy]:
    scope_key = str(scope or DEFAULT_OPTIMIZATION_SCOPE)
    methods = OPTIMIZER_METHODS_BY_SCOPE.get(scope_key)
    if methods is None:
        raise ValueError(f"Unknown optimization scope: {scope}")
    return methods


def register_optimizer_method(scope: str, method_name: str, strategy: OptimizerStrategy) -> None:
    if not method_name:
        raise ValueError("method_name cannot be empty")
    scope_key = str(scope or "").strip()
    if scope_key not in OPTIMIZER_METHODS_BY_SCOPE:
        raise ValueError(f"Unknown optimization scope: {scope}")
    OPTIMIZER_METHODS_BY_SCOPE[scope_key][method_name] = strategy


def optimize_candidates(
    df: pd.DataFrame,
    selected_stats: List[str],
    scope: str = DEFAULT_OPTIMIZATION_SCOPE,
    method: str = DEFAULT_OPTIMIZATION_METHOD,
    config: Optional[dict] = None,
) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    stats = [stat for stat in selected_stats if stat in df.columns]
    if len(stats) < 2:
        raise ValueError("At least 2 valid stats are required for optimization.")

    methods = get_optimizer_methods(scope)
    strategy = methods.get(method)
    if strategy is None:
        raise ValueError(
            f"Unknown optimization method: {method} for scope: {scope}"
        )

    return strategy(df, stats, config)


def optimize_single_piece(
    df: pd.DataFrame,
    selected_stats: List[str],
    method: str = DEFAULT_OPTIMIZATION_METHOD,
    config: Optional[dict] = None,
) -> pd.DataFrame:
    return optimize_candidates(
        df=df,
        selected_stats=selected_stats,
        scope=OPT_SCOPE_SINGLE_PIECE,
        method=method,
        config=config,
    )


def optimize_full_set(
    df: pd.DataFrame,
    selected_stats: List[str],
    method: str = DEFAULT_OPTIMIZATION_METHOD,
    config: Optional[dict] = None,
) -> pd.DataFrame:
    return optimize_candidates(
        df=df,
        selected_stats=selected_stats,
        scope=OPT_SCOPE_FULL_SET,
        method=method,
        config=config,
    )


def optimize_complete_set(
    df: pd.DataFrame,
    selected_stats: List[str],
    method: str = DEFAULT_OPTIMIZATION_METHOD,
    config: Optional[dict] = None,
) -> pd.DataFrame:
    return optimize_candidates(
        df=df,
        selected_stats=selected_stats,
        scope=OPT_SCOPE_COMPLETE_SET,
        method=method,
        config=config,
    )
