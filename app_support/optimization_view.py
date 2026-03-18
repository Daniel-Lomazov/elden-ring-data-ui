"""Optimization-view support helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import MutableMapping, Any

from optimizer import (
    DEFAULT_OPTIMIZATION_METHOD,
    ENGINE_LEGACY,
    format_encounter_profile_display_name,
    get_available_engine_ids,
    get_available_method_ids,
    get_available_objective_ids,
    get_default_objective_id,
    load_request,
    normalize_engine_id,
    normalize_method_id,
    normalize_objective_id,
    objective_requires_encounter_profile,
    objective_requires_status_penalty_weight,
    objective_supports_methods,
)


@dataclass(frozen=True)
class OptimizationViewState:
    engine_options: tuple[str, ...]
    optimizer_engine: str
    objective_options: tuple[str, ...]
    optimizer_objective_type: str
    profile_options: tuple[str, ...]
    optimizer_encounter_profile: str
    method_options: tuple[str, ...]
    optimizer_method: str
    optimizer_lambda_status: float
    show_encounter_profile: bool
    show_status_penalty_weight: bool
    show_optimization_method: bool
    show_weight_controls: bool


def list_encounter_profiles(root: Path) -> list[str]:
    profile_dir = root / "data" / "profiles"
    if not profile_dir.exists():
        return []
    names = []
    for path in sorted(profile_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in {".yaml", ".yml", ".json"}:
            names.append(path.name)
    return names


def resolve_optimization_view_state(
    root: Path,
    dataset: str,
    optimization_scope_key: str,
    session_state: MutableMapping[str, Any],
    ranking_stat_count: int | None = None,
) -> OptimizationViewState:
    engine_options = tuple(get_available_engine_ids(dataset, optimization_scope_key))
    engine_fallback = ENGINE_LEGACY if ENGINE_LEGACY in engine_options else (engine_options[0] if engine_options else ENGINE_LEGACY)
    optimizer_engine = normalize_engine_id(session_state.get("optimizer_engine", engine_fallback))
    if engine_options and optimizer_engine not in engine_options:
        optimizer_engine = engine_fallback
    session_state["optimizer_engine"] = optimizer_engine

    objective_options = tuple(
        get_available_objective_ids(optimizer_engine, dataset, optimization_scope_key)
    )
    default_objective = get_default_objective_id(
        optimizer_engine,
        dataset,
        optimization_scope_key,
    ) if objective_options else ""
    optimizer_objective_type = normalize_objective_id(
        session_state.get("optimizer_objective_type", default_objective)
    )
    if objective_options and optimizer_objective_type not in objective_options:
        optimizer_objective_type = default_objective
    session_state["optimizer_objective_type"] = optimizer_objective_type

    profile_options = tuple(list_encounter_profiles(root))
    if profile_options:
        optimizer_encounter_profile = str(
            session_state.get("optimizer_encounter_profile", profile_options[0])
        ).strip()
        if optimizer_encounter_profile not in profile_options:
            optimizer_encounter_profile = profile_options[0]
        session_state["optimizer_encounter_profile"] = optimizer_encounter_profile
    else:
        optimizer_encounter_profile = str(
            session_state.get("optimizer_encounter_profile", "")
        ).strip()

    if "optimizer_lambda_status" not in session_state:
        session_state["optimizer_lambda_status"] = 1.0
    optimizer_lambda_status = float(session_state.get("optimizer_lambda_status", 1.0))
    session_state["optimizer_lambda_status"] = optimizer_lambda_status

    if objective_supports_methods(optimizer_objective_type):
        method_options = tuple(get_available_method_ids(optimizer_objective_type))
        optimizer_method = normalize_method_id(
            session_state.get("optimizer_method", DEFAULT_OPTIMIZATION_METHOD)
        )
        if method_options and optimizer_method not in method_options:
            optimizer_method = DEFAULT_OPTIMIZATION_METHOD if DEFAULT_OPTIMIZATION_METHOD in method_options else method_options[0]
        session_state["optimizer_method"] = optimizer_method
    else:
        method_options = tuple()
        optimizer_method = ""
        session_state["optimizer_method"] = ""

    show_optimization_method = objective_supports_methods(optimizer_objective_type)
    show_weight_controls = (
        show_optimization_method
        and optimizer_method == "weighted_sum_normalized"
        and (ranking_stat_count is None or int(ranking_stat_count) >= 2)
    )
    return OptimizationViewState(
        engine_options=engine_options,
        optimizer_engine=optimizer_engine,
        objective_options=objective_options,
        optimizer_objective_type=optimizer_objective_type,
        profile_options=profile_options,
        optimizer_encounter_profile=optimizer_encounter_profile,
        method_options=method_options,
        optimizer_method=optimizer_method,
        optimizer_lambda_status=optimizer_lambda_status,
        show_encounter_profile=objective_requires_encounter_profile(optimizer_objective_type),
        show_status_penalty_weight=objective_requires_status_penalty_weight(
            optimizer_objective_type
        ),
        show_optimization_method=show_optimization_method,
        show_weight_controls=show_weight_controls,
    )


def load_encounter_profile_request(root: Path, profile_name: str) -> tuple[dict | None, str | None]:
    token = str(profile_name or "").strip()
    if not token:
        return None, "Select an encounter profile to run Encounter Survival."

    profile_path = root / "data" / "profiles" / token
    display_name = format_encounter_profile_display_name(token) or token
    if not profile_path.exists() or not profile_path.is_file():
        return None, f"Encounter profile '{display_name}' could not be found."

    try:
        return load_request(profile_path), None
    except Exception as exc:
        return None, f"Encounter profile '{display_name}' could not be loaded: {exc}"
