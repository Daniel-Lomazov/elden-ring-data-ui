"""Dialect stat-rank strategy wrapper around legacy optimizer."""

from __future__ import annotations

import pandas as pd

from ..legacy import (
    DEFAULT_OPTIMIZATION_METHOD,
    OPT_SCOPE_COMPLETE_SET,
    OPT_SCOPE_FULL_SET,
    OPT_SCOPE_SINGLE_PIECE,
    optimize_complete_set,
    optimize_full_set,
    optimize_single_piece,
)

_SCOPE_FN = {
    OPT_SCOPE_SINGLE_PIECE: optimize_single_piece,
    OPT_SCOPE_FULL_SET: optimize_full_set,
    OPT_SCOPE_COMPLETE_SET: optimize_complete_set,
}


def optimize_stat_rank(df: pd.DataFrame, request: dict) -> pd.DataFrame:
    scope = request.get("scope", OPT_SCOPE_SINGLE_PIECE)
    selected_stats = request.get("selected_stats") or []
    if len(selected_stats) < 2:
        raise ValueError("Dialect stat_rank requires at least 2 selected_stats")

    objective = request.get("objective") or {}
    method = objective.get("method") or DEFAULT_OPTIMIZATION_METHOD
    config = dict(request.get("config") or {})
    if objective.get("weights"):
        config["weights"] = objective["weights"]

    fn = _SCOPE_FN.get(scope, optimize_single_piece)
    return fn(
        df,
        selected_stats=selected_stats,
        method=method,
        config=config,
    )
