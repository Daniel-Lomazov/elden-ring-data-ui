"""Optimization request dialect loading/validation/canonicalization.

Supports dict input directly and JSON/YAML files from disk.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .schema import (
    CANONICAL_SCHEMA_VERSION,
    NEGATION_KEYS,
    OBJECTIVE_STAT_RANK,
    OBJECTIVE_TYPES,
    SCOPES,
    STATUS_KEYS,
)


def _load_raw_request(request: Dict[str, Any] | str | Path) -> Dict[str, Any]:
    if isinstance(request, dict):
        return dict(request)

    req_path = Path(request)
    if not req_path.exists():
        raise FileNotFoundError(f"Request file not found: {req_path}")

    suffix = req_path.suffix.lower()
    text = req_path.read_text(encoding="utf-8")

    if suffix in {".json"}:
        return json.loads(text)

    if suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "YAML request parsing requires PyYAML. Install with: pip install pyyaml"
            ) from exc
        loaded = yaml.safe_load(text)
        return loaded if isinstance(loaded, dict) else {}

    raise ValueError(f"Unsupported request file format: {suffix}")


def _ensure_dict(value: Any, field_name: str) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    raise ValueError(f"{field_name} must be an object")


def canonicalize_request(request: Dict[str, Any]) -> Dict[str, Any]:
    raw = dict(request)

    version = int(raw.get("version", CANONICAL_SCHEMA_VERSION))
    if version != CANONICAL_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported request version {version}; expected {CANONICAL_SCHEMA_VERSION}"
        )

    scope = str(raw.get("scope", "single_piece"))
    if scope not in SCOPES:
        raise ValueError(f"Unsupported scope '{scope}'. Expected one of: {SCOPES}")

    objective = _ensure_dict(raw.get("objective"), "objective")
    objective_type = str(objective.get("type", OBJECTIVE_STAT_RANK))
    if objective_type not in OBJECTIVE_TYPES:
        raise ValueError(
            f"Unsupported objective.type '{objective_type}'. Expected one of: {OBJECTIVE_TYPES}"
        )

    selected_stats = raw.get("selected_stats", objective.get("selected_stats", []))
    if selected_stats is None:
        selected_stats = []
    if not isinstance(selected_stats, list):
        raise ValueError("selected_stats must be a list")

    constraints = _ensure_dict(raw.get("constraints"), "constraints")
    encounter = _ensure_dict(raw.get("encounter"), "encounter")
    incoming = _ensure_dict(encounter.get("incoming"), "encounter.incoming")
    status_threats = _ensure_dict(encounter.get("status_threats"), "encounter.status_threats")
    damage_mix = _ensure_dict(incoming.get("damage_mix"), "encounter.incoming.damage_mix")

    for key in damage_mix.keys():
        if str(key) not in NEGATION_KEYS:
            raise ValueError(
                f"Unsupported encounter.incoming.damage_mix key '{key}'. "
                f"Expected canonical negation keys: {NEGATION_KEYS}"
            )

    canonical_status_threats: Dict[str, Dict[str, float]] = {}
    for status_key, status_value in status_threats.items():
        status_name = str(status_key)
        if status_name not in STATUS_KEYS:
            raise ValueError(
                f"Unsupported encounter.status_threats key '{status_name}'. "
                f"Expected canonical status keys: {STATUS_KEYS}"
            )
        payload = _ensure_dict(status_value, f"encounter.status_threats.{status_name}")
        canonical_status_threats[status_name] = {
            "buildup_per_hit": float(payload.get("buildup_per_hit", 0.0)),
            "proc_penalty": float(payload.get("proc_penalty", 0.0)),
            "weight": float(payload.get("weight", 1.0)),
            "a": float(payload.get("a", 10.0)),
            "b": float(payload.get("b", 0.0)),
        }

    canonical = {
        "version": CANONICAL_SCHEMA_VERSION,
        "scope": scope,
        "slot": raw.get("slot"),
        "objective": {
            "type": objective_type,
            "method": objective.get("method"),
            "hp": float(objective.get("hp", 1.0)) if objective.get("hp") is not None else None,
            "eps": float(objective.get("eps", 1e-9)),
            "lambda_status": float(objective.get("lambda_status", 0.0)),
            "weights": objective.get("weights", {}),
        },
        "selected_stats": [str(s) for s in selected_stats],
        "constraints": constraints,
        "encounter": {
            "name": encounter.get("name"),
            "incoming": {
                "damage_mix": {str(k): float(v) for k, v in damage_mix.items()}
            },
            "status_threats": canonical_status_threats,
        },
        "config": _ensure_dict(raw.get("config"), "config"),
    }

    return canonical


def load_request(request: Dict[str, Any] | str | Path) -> Dict[str, Any]:
    raw = _load_raw_request(request)
    return canonicalize_request(raw)
