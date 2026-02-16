"""Encounter-survival strategy (PR3: HP channel only).

Scoring model:
- m_t = 1 - N_t
- M = sum_t w_t * m_t
- eHP = HP / max(M, eps)

Ranking objective minimizes M (ascending).
"""

from __future__ import annotations

import math
import json
from typing import Dict

import pandas as pd

from ..schema import (
    NEGATION_KEYS,
    STATUS_TO_RESISTANCE,
    resolve_df_column_for_canonical_key,
)


def _to_ratio(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce").fillna(0.0)
    if float(numeric.max()) > 1.0:
        numeric = numeric / 100.0
    return numeric.clip(lower=0.0, upper=0.99)


def _normalize_weights(damage_mix: Dict[str, float]) -> Dict[str, float]:
    filtered = {
        str(key): float(value)
        for key, value in damage_mix.items()
        if str(key) in NEGATION_KEYS and float(value) > 0
    }
    if not filtered:
        return {"neg.phys": 1.0}
    total = sum(filtered.values())
    return {key: value / total for key, value in filtered.items()} if total > 0 else filtered


def optimize_encounter_survival(df: pd.DataFrame, request: dict) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    objective = request.get("objective") or {}
    hp_raw = objective.get("hp", 1.0)
    hp = float(hp_raw) if hp_raw is not None else 1.0
    eps = float(objective.get("eps", 1e-9))
    lambda_status = float(objective.get("lambda_status", 0.0))

    encounter = request.get("encounter") or {}
    incoming = encounter.get("incoming") or {}
    weights = _normalize_weights(incoming.get("damage_mix") or {})

    output = df.copy()
    weighted_terms = pd.Series(0.0, index=output.index, dtype=float)
    taken_by_type: Dict[str, pd.Series] = {}

    for canonical_key, weight in weights.items():
        df_column = resolve_df_column_for_canonical_key(canonical_key)
        if df_column in output.columns:
            neg = _to_ratio(output[df_column])
        else:
            neg = pd.Series(0.0, index=output.index, dtype=float)

        taken = 1.0 - neg
        taken_by_type[canonical_key] = taken
        output[f"Taken: {canonical_key}"] = taken
        weighted_terms = weighted_terms + (weight * taken)

    output["expected_taken_M"] = weighted_terms
    output["effective_hp"] = hp / output["expected_taken_M"].clip(lower=eps)

    status_penalty = pd.Series(0.0, index=output.index, dtype=float)
    status_details_per_row: Dict[int, Dict[str, dict]] = {int(i): {} for i in output.index}
    status_threats = (encounter.get("status_threats") or {}) if isinstance(encounter, dict) else {}

    for status_key, cfg in status_threats.items():
        if status_key not in STATUS_TO_RESISTANCE:
            continue

        payload = cfg if isinstance(cfg, dict) else {}
        buildup_per_hit = max(float(payload.get("buildup_per_hit", 0.0)), eps)
        proc_penalty = max(float(payload.get("proc_penalty", 0.0)), 0.0)
        threat_weight = max(float(payload.get("weight", 1.0)), 0.0)
        coef_a = float(payload.get("a", 1.0))
        coef_b = float(payload.get("b", 0.0))

        resistance_key = STATUS_TO_RESISTANCE[status_key]
        resistance_col = resolve_df_column_for_canonical_key(resistance_key)
        if resistance_col in output.columns:
            resistance = pd.to_numeric(output[resistance_col], errors="coerce").fillna(0.0)
        else:
            resistance = pd.Series(0.0, index=output.index, dtype=float)

        threshold = (coef_a * resistance + coef_b).clip(lower=eps)
        hits_to_proc = (threshold / buildup_per_hit).apply(lambda v: max(1, int(math.ceil(v))))
        penalty_per_hit = proc_penalty / hits_to_proc
        weighted_penalty = threat_weight * penalty_per_hit
        status_penalty = status_penalty + weighted_penalty

        output[f"StatusHits: {status_key}"] = hits_to_proc
        output[f"StatusPen: {status_key}"] = weighted_penalty

        for idx in output.index:
            status_details_per_row[int(idx)][status_key] = {
                "resistance_key": resistance_key,
                "threshold": float(threshold.loc[idx]),
                "buildup_per_hit": float(buildup_per_hit),
                "k_hits": int(hits_to_proc.loc[idx]),
                "pen_per_hit": float(penalty_per_hit.loc[idx]),
                "weighted_penalty": float(weighted_penalty.loc[idx]),
            }

    output["status_penalty"] = status_penalty
    output["final_score_J"] = output["expected_taken_M"] + (lambda_status * output["status_penalty"])

    explains = []
    for idx in output.index:
        explain = {
            "taken_by_type": {
                key: float(series.loc[idx]) for key, series in taken_by_type.items()
            },
            "expected_taken_M": float(output.loc[idx, "expected_taken_M"]),
            "effective_hp": float(output.loc[idx, "effective_hp"]),
            "status": status_details_per_row[int(idx)],
            "status_penalty": float(output.loc[idx, "status_penalty"]),
            "final_score_J": float(output.loc[idx, "final_score_J"]),
        }
        explains.append(json.dumps(explain, separators=(",", ":")))

    output["__explain"] = explains
    output["__opt_score"] = output["final_score_J"]
    output["__opt_tiebreak"] = output["effective_hp"]
    output["__opt_method"] = "encounter_survival"
    output["__opt_length"] = len(weights)

    output = output.sort_values(
        by=["__opt_score", "__opt_tiebreak"], ascending=[True, False]
    ).reset_index(drop=True)
    output["__opt_rank"] = output.index + 1
    return output
