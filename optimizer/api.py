"""Public optimizer API for dialect-first requests."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from .dialect import load_request
from .strategies.encounter_survival import optimize_encounter_survival
from .strategies.full_set_prune import optimize_encounter_survival_full_set
from .strategies.full_set_stat_rank import optimize_stat_rank_full_set
from .strategies.stat_rank import optimize_stat_rank


def optimize(df: pd.DataFrame, request: Dict[str, Any] | str) -> pd.DataFrame:
    """Optimize candidates using canonical request dialect.

    PR3 behavior:
    - Supports `objective.type = stat_rank` by delegating to legacy optimizer methods.
    - Supports `objective.type = encounter_survival` for single_piece/per_slot.
    """
    canonical = load_request(request)

    objective = canonical["objective"]
    objective_type = objective["type"]

    if objective_type == "stat_rank":
        if canonical.get("scope") == "full_set":
            return optimize_stat_rank_full_set(df, canonical)
        return optimize_stat_rank(df, canonical)

    if objective_type == "encounter_survival":
        scope = canonical.get("scope")
        if scope in {"single_piece", "per_slot"}:
            return optimize_encounter_survival(df, canonical)
        if scope == "full_set":
            return optimize_encounter_survival_full_set(df, canonical)
        raise ValueError(
            "Encounter survival currently supports scope='single_piece', 'per_slot', or 'full_set'"
        )

    raise ValueError(
        f"Unsupported objective.type '{objective_type}' in current API iteration"
    )
