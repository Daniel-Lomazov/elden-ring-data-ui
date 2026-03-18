"""Shared optimizer capability catalog for UI and backend wiring."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .schema import (
    OBJECTIVE_ENCOUNTER_SURVIVAL,
    OBJECTIVE_STAT_RANK,
    SCOPE_COMPLETE_LOADOUT,
    SCOPE_FULL_SET,
    SCOPE_PER_SLOT,
    SCOPE_SINGLE_PIECE,
)

ENGINE_LEGACY = "legacy"
ENGINE_ADVANCED = "advanced"

METHOD_MAXIMIN_NORMALIZED = "maximin_normalized"
METHOD_WEIGHTED_SUM_NORMALIZED = "weighted_sum_normalized"


@dataclass(frozen=True)
class EngineCapability:
    id: str
    label: str
    description: str
    supported_objectives: tuple[str, ...]
    default_objective: str
    supported_datasets: tuple[str, ...]
    supported_scopes: tuple[str, ...]


@dataclass(frozen=True)
class ObjectiveCapability:
    id: str
    label: str
    supported_engines: tuple[str, ...]
    supported_datasets: tuple[str, ...]
    supported_scopes: tuple[str, ...]
    supports_methods: bool
    requires_encounter_profile: bool
    requires_status_penalty_weight: bool


@dataclass(frozen=True)
class MethodCapability:
    id: str
    label: str
    supported_objectives: tuple[str, ...]


@dataclass(frozen=True)
class StrategyResolution:
    engine_id: str
    objective_id: str
    scope: str
    dispatch_key: str
    strategy_family: str


ENGINE_CAPABILITIES = {
    ENGINE_LEGACY: EngineCapability(
        id=ENGINE_LEGACY,
        label="Legacy Ranking",
        description="Established normalized stat-ranking pipeline.",
        supported_objectives=(OBJECTIVE_STAT_RANK,),
        default_objective=OBJECTIVE_STAT_RANK,
        supported_datasets=("armors", "talismans"),
        supported_scopes=(SCOPE_SINGLE_PIECE, SCOPE_FULL_SET, SCOPE_COMPLETE_LOADOUT),
    ),
    ENGINE_ADVANCED: EngineCapability(
        id=ENGINE_ADVANCED,
        label="Advanced Optimizer",
        description="Extensible optimizer for shared stat ranking and encounter-aware objectives.",
        supported_objectives=(OBJECTIVE_STAT_RANK, OBJECTIVE_ENCOUNTER_SURVIVAL),
        default_objective=OBJECTIVE_STAT_RANK,
        supported_datasets=("armors", "talismans"),
        supported_scopes=(
            SCOPE_SINGLE_PIECE,
            SCOPE_PER_SLOT,
            SCOPE_FULL_SET,
            SCOPE_COMPLETE_LOADOUT,
        ),
    ),
}

OBJECTIVE_CAPABILITIES = {
    OBJECTIVE_STAT_RANK: ObjectiveCapability(
        id=OBJECTIVE_STAT_RANK,
        label="Stat Ranking",
        supported_engines=(ENGINE_LEGACY, ENGINE_ADVANCED),
        supported_datasets=("armors", "talismans"),
        supported_scopes=(SCOPE_SINGLE_PIECE, SCOPE_FULL_SET, SCOPE_COMPLETE_LOADOUT),
        supports_methods=True,
        requires_encounter_profile=False,
        requires_status_penalty_weight=False,
    ),
    OBJECTIVE_ENCOUNTER_SURVIVAL: ObjectiveCapability(
        id=OBJECTIVE_ENCOUNTER_SURVIVAL,
        label="Encounter Survival",
        supported_engines=(ENGINE_ADVANCED,),
        supported_datasets=("armors",),
        supported_scopes=(SCOPE_SINGLE_PIECE, SCOPE_PER_SLOT, SCOPE_FULL_SET),
        supports_methods=False,
        requires_encounter_profile=True,
        requires_status_penalty_weight=True,
    ),
}

METHOD_CAPABILITIES = {
    METHOD_MAXIMIN_NORMALIZED: MethodCapability(
        id=METHOD_MAXIMIN_NORMALIZED,
        label="Maximin",
        supported_objectives=(OBJECTIVE_STAT_RANK,),
    ),
    METHOD_WEIGHTED_SUM_NORMALIZED: MethodCapability(
        id=METHOD_WEIGHTED_SUM_NORMALIZED,
        label="Weighted Sum",
        supported_objectives=(OBJECTIVE_STAT_RANK,),
    ),
}

_ENGINE_ALIASES = {
    "legacy": ENGINE_LEGACY,
    "legacy ranking": ENGINE_LEGACY,
    "optimization 2.0": ENGINE_ADVANCED,
    "advanced optimizer": ENGINE_ADVANCED,
    "advanced": ENGINE_ADVANCED,
}

_OBJECTIVE_ALIASES = {
    OBJECTIVE_STAT_RANK: OBJECTIVE_STAT_RANK,
    "stat ranking": OBJECTIVE_STAT_RANK,
    OBJECTIVE_ENCOUNTER_SURVIVAL: OBJECTIVE_ENCOUNTER_SURVIVAL,
    "encounter survival": OBJECTIVE_ENCOUNTER_SURVIVAL,
}

_METHOD_ALIASES = {
    METHOD_MAXIMIN_NORMALIZED: METHOD_MAXIMIN_NORMALIZED,
    "maximin": METHOD_MAXIMIN_NORMALIZED,
    METHOD_WEIGHTED_SUM_NORMALIZED: METHOD_WEIGHTED_SUM_NORMALIZED,
    "weighted sum": METHOD_WEIGHTED_SUM_NORMALIZED,
}

_SCOPE_ALIASES = {
    SCOPE_SINGLE_PIECE: SCOPE_SINGLE_PIECE,
    SCOPE_PER_SLOT: SCOPE_PER_SLOT,
    SCOPE_FULL_SET: SCOPE_FULL_SET,
    SCOPE_COMPLETE_LOADOUT: SCOPE_COMPLETE_LOADOUT,
    "complete_set": SCOPE_COMPLETE_LOADOUT,
}

_STRATEGY_DISPATCH_KEYS = {
    (ENGINE_LEGACY, OBJECTIVE_STAT_RANK, SCOPE_SINGLE_PIECE): "stat_rank_single_piece",
    (ENGINE_LEGACY, OBJECTIVE_STAT_RANK, SCOPE_FULL_SET): "stat_rank_full_set",
    (ENGINE_LEGACY, OBJECTIVE_STAT_RANK, SCOPE_COMPLETE_LOADOUT): "stat_rank_complete_loadout",
    (ENGINE_ADVANCED, OBJECTIVE_STAT_RANK, SCOPE_SINGLE_PIECE): "stat_rank_single_piece",
    (ENGINE_ADVANCED, OBJECTIVE_STAT_RANK, SCOPE_FULL_SET): "stat_rank_full_set",
    (ENGINE_ADVANCED, OBJECTIVE_STAT_RANK, SCOPE_COMPLETE_LOADOUT): "stat_rank_complete_loadout",
    (ENGINE_ADVANCED, OBJECTIVE_ENCOUNTER_SURVIVAL, SCOPE_SINGLE_PIECE): "encounter_survival_single_piece",
    (ENGINE_ADVANCED, OBJECTIVE_ENCOUNTER_SURVIVAL, SCOPE_PER_SLOT): "encounter_survival_per_slot",
    (ENGINE_ADVANCED, OBJECTIVE_ENCOUNTER_SURVIVAL, SCOPE_FULL_SET): "encounter_survival_full_set",
}


def _normalize_alias(value: str, aliases: dict[str, str], fallback: str) -> str:
    token = str(value or "").strip().lower()
    if not token:
        return fallback
    return aliases.get(token, token)


def normalize_engine_id(value: str | None) -> str:
    return _normalize_alias(value or "", _ENGINE_ALIASES, ENGINE_LEGACY)


def normalize_objective_id(value: str | None) -> str:
    return _normalize_alias(value or "", _OBJECTIVE_ALIASES, OBJECTIVE_STAT_RANK)


def normalize_method_id(value: str | None) -> str:
    return _normalize_alias(value or "", _METHOD_ALIASES, METHOD_MAXIMIN_NORMALIZED)


def normalize_scope_id(value: str | None) -> str:
    return _normalize_alias(value or "", _SCOPE_ALIASES, SCOPE_SINGLE_PIECE)


def get_engine_capability(engine_id: str) -> EngineCapability:
    token = normalize_engine_id(engine_id)
    capability = ENGINE_CAPABILITIES.get(token)
    if capability is None:
        raise ValueError(f"Unsupported engine '{engine_id}'")
    return capability


def get_objective_capability(objective_id: str) -> ObjectiveCapability:
    token = normalize_objective_id(objective_id)
    capability = OBJECTIVE_CAPABILITIES.get(token)
    if capability is None:
        raise ValueError(f"Unsupported objective '{objective_id}'")
    return capability


def get_method_capability(method_id: str) -> MethodCapability:
    token = normalize_method_id(method_id)
    capability = METHOD_CAPABILITIES.get(token)
    if capability is None:
        raise ValueError(f"Unsupported method '{method_id}'")
    return capability


def get_engine_label(engine_id: str) -> str:
    return get_engine_capability(engine_id).label


def get_engine_description(engine_id: str) -> str:
    return get_engine_capability(engine_id).description


def get_objective_label(objective_id: str) -> str:
    return get_objective_capability(objective_id).label


def get_method_label(method_id: str) -> str:
    return get_method_capability(method_id).label


def get_available_engine_ids(dataset: str, scope: str) -> list[str]:
    normalized_scope = normalize_scope_id(scope)
    dataset_token = str(dataset or "").strip().lower()
    return [
        engine_id
        for engine_id, capability in ENGINE_CAPABILITIES.items()
        if dataset_token in capability.supported_datasets
        and normalized_scope in capability.supported_scopes
    ]


def get_available_objective_ids(engine_id: str, dataset: str, scope: str) -> list[str]:
    engine = get_engine_capability(engine_id)
    normalized_scope = normalize_scope_id(scope)
    dataset_token = str(dataset or "").strip().lower()
    return [
        objective_id
        for objective_id in engine.supported_objectives
        if dataset_token in OBJECTIVE_CAPABILITIES[objective_id].supported_datasets
        and normalized_scope in OBJECTIVE_CAPABILITIES[objective_id].supported_scopes
    ]


def get_default_objective_id(engine_id: str, dataset: str, scope: str) -> str:
    engine = get_engine_capability(engine_id)
    options = get_available_objective_ids(engine.id, dataset, scope)
    if engine.default_objective in options:
        return engine.default_objective
    if not options:
        raise ValueError(
            f"No supported objectives for engine='{engine.id}', dataset='{dataset}', scope='{scope}'"
        )
    return options[0]


def get_available_method_ids(objective_id: str) -> list[str]:
    objective = get_objective_capability(objective_id)
    if not objective.supports_methods:
        return []
    return [
        method_id
        for method_id, capability in METHOD_CAPABILITIES.items()
        if objective.id in capability.supported_objectives
    ]


def objective_supports_methods(objective_id: str) -> bool:
    return get_objective_capability(objective_id).supports_methods


def objective_requires_encounter_profile(objective_id: str) -> bool:
    return get_objective_capability(objective_id).requires_encounter_profile


def objective_requires_status_penalty_weight(objective_id: str) -> bool:
    return get_objective_capability(objective_id).requires_status_penalty_weight


def validate_engine_objective_scope(
    engine_id: str,
    objective_id: str,
    scope: str,
    dataset: str | None = None,
) -> None:
    normalized_engine = normalize_engine_id(engine_id)
    normalized_objective = normalize_objective_id(objective_id)
    normalized_scope = normalize_scope_id(scope)
    normalized_dataset = str(dataset or "").strip().lower()

    engine = get_engine_capability(normalized_engine)
    objective = get_objective_capability(normalized_objective)

    if normalized_scope not in engine.supported_scopes:
        raise ValueError(
            f"Engine '{normalized_engine}' does not support scope '{normalized_scope}'"
        )
    if normalized_objective not in engine.supported_objectives:
        raise ValueError(
            f"Objective '{normalized_objective}' is not supported by engine '{normalized_engine}'"
        )
    if normalized_engine not in objective.supported_engines:
        raise ValueError(
            f"Objective '{normalized_objective}' is not supported by engine '{normalized_engine}'"
        )
    if normalized_scope not in objective.supported_scopes:
        raise ValueError(
            f"Objective '{normalized_objective}' does not support scope '{normalized_scope}'"
        )
    if normalized_dataset:
        if normalized_dataset not in engine.supported_datasets:
            raise ValueError(
                f"Engine '{normalized_engine}' does not support dataset '{normalized_dataset}'"
            )
        if normalized_dataset not in objective.supported_datasets:
            raise ValueError(
                f"Objective '{normalized_objective}' does not support dataset '{normalized_dataset}'"
            )


def validate_objective_method(objective_id: str, method_id: str | None) -> None:
    normalized_objective = normalize_objective_id(objective_id)
    normalized_method = normalize_method_id(method_id) if method_id else ""
    objective = get_objective_capability(normalized_objective)

    if not objective.supports_methods:
        if normalized_method:
            raise ValueError(
                f"Objective '{normalized_objective}' does not support optimization methods"
            )
        return

    if not normalized_method:
        raise ValueError(
            f"Objective '{normalized_objective}' requires an optimization method"
        )
    method = get_method_capability(normalized_method)
    if normalized_objective not in method.supported_objectives:
        raise ValueError(
            f"Method '{normalized_method}' is not supported for objective '{normalized_objective}'"
        )


def resolve_strategy(
    engine_id: str,
    objective_id: str,
    scope: str,
    dataset: str | None = None,
) -> StrategyResolution:
    if engine_id is None or not str(engine_id).strip():
        raise ValueError("engine is required for strategy resolution")
    normalized_engine = normalize_engine_id(engine_id)

    normalized_objective = normalize_objective_id(objective_id)
    normalized_scope = normalize_scope_id(scope)

    validate_engine_objective_scope(
        normalized_engine,
        normalized_objective,
        normalized_scope,
        dataset=dataset,
    )

    dispatch_key = _STRATEGY_DISPATCH_KEYS.get(
        (normalized_engine, normalized_objective, normalized_scope)
    )
    if dispatch_key is None:
        raise ValueError(
            "No strategy dispatch is registered for "
            f"engine='{normalized_engine}', objective='{normalized_objective}', scope='{normalized_scope}'"
        )

    return StrategyResolution(
        engine_id=normalized_engine,
        objective_id=normalized_objective,
        scope=normalized_scope,
        dispatch_key=dispatch_key,
        strategy_family=normalized_objective,
    )


def format_encounter_profile_display_name(filename: str) -> str:
    stem = Path(str(filename or "").strip()).stem
    if not stem:
        return ""
    cleaned = re.sub(r"[_\-]+", " ", stem).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.title()
