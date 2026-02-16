"""Public optimizer API for dialect-first requests."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from .dialect import load_request
from .strategies.encounter_survival import optimize_encounter_survival
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
        return optimize_stat_rank(df, canonical)

    if objective_type == "encounter_survival":
        scope = canonical.get("scope")
        if scope not in {"single_piece", "per_slot"}:
            raise ValueError(
                "PR3 encounter_survival supports only scope='single_piece' or 'per_slot'. "
                "Full-set support is added in PR5."
            )
        return optimize_encounter_survival(df, canonical)

    raise ValueError(
        f"Unsupported objective.type '{objective_type}' in current API iteration"
    )
