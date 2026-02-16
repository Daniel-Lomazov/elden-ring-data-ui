"""Public optimizer API for dialect-first requests."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from .dialect import load_request
from .legacy import (
    DEFAULT_OPTIMIZATION_METHOD,
    OPT_SCOPE_COMPLETE_SET,
    OPT_SCOPE_FULL_SET,
    OPT_SCOPE_SINGLE_PIECE,
    optimize_complete_set,
    optimize_full_set,
    optimize_single_piece,
)


ScopeFn = {
    OPT_SCOPE_SINGLE_PIECE: optimize_single_piece,
    OPT_SCOPE_FULL_SET: optimize_full_set,
    OPT_SCOPE_COMPLETE_SET: optimize_complete_set,
}


def optimize(df: pd.DataFrame, request: Dict[str, Any] | str) -> pd.DataFrame:
    """Optimize candidates using canonical request dialect.

    PR2 behavior:
    - Supports `objective.type = stat_rank` by delegating to legacy optimizer methods.
    - Encounter/objective extensions are wired in later PRs.
    """
    canonical = load_request(request)

    objective = canonical["objective"]
    objective_type = objective["type"]

    if objective_type != "stat_rank":
        raise ValueError(
            "Only objective.type='stat_rank' is available in PR2. "
            "Encounter strategies are added in later PRs."
        )

    scope = canonical["scope"]
    scope_key = scope if scope in ScopeFn else OPT_SCOPE_SINGLE_PIECE
    selected_stats = canonical.get("selected_stats") or []
    if len(selected_stats) < 2:
        raise ValueError("Dialect stat_rank requires at least 2 selected_stats")

    method = objective.get("method") or DEFAULT_OPTIMIZATION_METHOD
    config = dict(canonical.get("config") or {})
    if objective.get("weights"):
        config["weights"] = objective["weights"]

    return ScopeFn[scope_key](
        df,
        selected_stats=selected_stats,
        method=method,
        config=config,
    )
