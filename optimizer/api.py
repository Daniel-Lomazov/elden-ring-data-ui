"""Public optimizer API for dialect-first requests."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from .catalog import resolve_strategy
from .dialect import load_request
from .strategies.encounter_survival import optimize_encounter_survival
from .strategies.full_set_prune import optimize_encounter_survival_full_set
from .strategies.full_set_stat_rank import optimize_stat_rank_full_set
from .strategies.stat_rank import optimize_stat_rank


_DISPATCH_BY_KEY = {
    "stat_rank_single_piece": optimize_stat_rank,
    "stat_rank_full_set": optimize_stat_rank_full_set,
    "stat_rank_complete_loadout": optimize_stat_rank,
    "encounter_survival_single_piece": optimize_encounter_survival,
    "encounter_survival_per_slot": optimize_encounter_survival,
    "encounter_survival_full_set": optimize_encounter_survival_full_set,
}


def optimize(df: pd.DataFrame, request: Dict[str, Any] | str) -> pd.DataFrame:
    """Optimize candidates using canonical request dialect.

    PR3 behavior:
    - Supports `objective.type = stat_rank` by delegating to legacy optimizer methods.
    - Supports `objective.type = encounter_survival` for single_piece/per_slot.
    """
    canonical = load_request(request)

    objective = canonical["objective"]
    route = resolve_strategy(
        canonical["engine"],
        objective["type"],
        canonical.get("scope", ""),
        dataset=canonical.get("dataset"),
    )

    strategy = _DISPATCH_BY_KEY.get(route.dispatch_key)
    if strategy is None:
        raise ValueError(
            f"Unsupported strategy dispatch key '{route.dispatch_key}' for current API iteration"
        )

    return strategy(df, canonical)
