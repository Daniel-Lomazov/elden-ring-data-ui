"""File-backed optimizer preset helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .catalog import ENGINE_ADVANCED, ENGINE_LEGACY, normalize_engine_id, normalize_scope_id
from .schema import OBJECTIVE_STAT_RANK

PRESET_KIND_WEIGHTED_STAT = "weighted_stat_preset"
PRESET_VERSION = 1
PRESET_METHOD_WEIGHTED_SUM = "weighted_sum_normalized"


@dataclass(frozen=True)
class WeightedStatPreset:
    preset_id: str
    label: str
    description: str
    datasets: tuple[str, ...]
    engines: tuple[str, ...]
    scopes: tuple[str, ...]
    preferred_engine: str
    selected_stats: tuple[str, ...]
    weights: dict[str, float]
    optimize_with_weight: bool


def _preset_dir(root: Path) -> Path:
    return root / "data" / "optimization_presets"


def _slugify(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    return token or "preset"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    return loaded if isinstance(loaded, dict) else {}


def _parse_weighted_preset(payload: dict) -> WeightedStatPreset:
    if str(payload.get("kind", "")).strip() != PRESET_KIND_WEIGHTED_STAT:
        raise ValueError("Unsupported preset kind")
    if int(payload.get("version", PRESET_VERSION)) != PRESET_VERSION:
        raise ValueError("Unsupported preset version")

    preset_id = str(payload.get("id", "")).strip()
    label = str(payload.get("label", "")).strip()
    if not preset_id or not label:
        raise ValueError("Preset id and label are required")

    compatibility = payload.get("compatibility") if isinstance(payload.get("compatibility"), dict) else {}
    datasets = tuple(str(v).strip().lower() for v in compatibility.get("datasets", []) if str(v).strip())
    engines = tuple(normalize_engine_id(v) for v in compatibility.get("engines", []) if str(v).strip())
    scopes = tuple(normalize_scope_id(v) for v in compatibility.get("scopes", []) if str(v).strip())

    defaults = payload.get("defaults") if isinstance(payload.get("defaults"), dict) else {}
    preferred_engine = normalize_engine_id(defaults.get("preferred_engine", ENGINE_LEGACY))

    payload_section = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    raw_selected_stats = payload_section.get("selected_stats", [])
    selected_stats = tuple(str(stat).strip() for stat in raw_selected_stats if str(stat).strip())
    raw_weights = payload_section.get("weights", {})
    weights = {
        str(key).strip(): float(value)
        for key, value in raw_weights.items()
        if str(key).strip() and float(value) > 0
    }
    optimize_with_weight = bool(payload_section.get("optimize_with_weight", False))

    if len(selected_stats) < 2:
        raise ValueError("Weighted stat preset requires at least two selected stats")
    if not weights:
        raise ValueError("Weighted stat preset requires at least one positive weight")

    return WeightedStatPreset(
        preset_id=preset_id,
        label=label,
        description=str(payload.get("description", "")).strip(),
        datasets=datasets,
        engines=engines or (ENGINE_LEGACY, ENGINE_ADVANCED),
        scopes=scopes or ("single_piece", "full_set", "complete_loadout"),
        preferred_engine=preferred_engine,
        selected_stats=selected_stats,
        weights=weights,
        optimize_with_weight=optimize_with_weight,
    )


def list_weighted_stat_presets(root: Path, dataset: str | None = None) -> list[WeightedStatPreset]:
    preset_dir = _preset_dir(root)
    if not preset_dir.exists():
        return []
    dataset_token = str(dataset or "").strip().lower()
    presets: list[WeightedStatPreset] = []
    for path in sorted(preset_dir.glob("*.json")):
        try:
            preset = _parse_weighted_preset(_load_json(path))
        except Exception:
            continue
        if dataset_token and preset.datasets and dataset_token not in preset.datasets:
            continue
        presets.append(preset)
    return sorted(presets, key=lambda item: item.label.lower())


def load_weighted_stat_preset(root: Path, preset_id: str) -> tuple[WeightedStatPreset | None, str | None]:
    token = _slugify(preset_id)
    if not token:
        return None, "Select a preset to load."
    path = _preset_dir(root) / f"{token}.json"
    if not path.exists():
        return None, f"Preset '{preset_id}' could not be found."
    try:
        return _parse_weighted_preset(_load_json(path)), None
    except Exception as exc:
        return None, f"Preset '{preset_id}' could not be loaded: {exc}"


def save_weighted_stat_preset(
    root: Path,
    *,
    label: str,
    dataset: str,
    selected_stats: list[str],
    weights: dict[str, float],
    optimize_with_weight: bool,
    preferred_engine: str = ENGINE_LEGACY,
    description: str = "",
) -> tuple[WeightedStatPreset | None, str | None]:
    clean_label = str(label or "").strip()
    if not clean_label:
        return None, "Enter a preset name before saving."

    filtered_stats = [str(stat).strip() for stat in selected_stats if str(stat).strip()]
    if len(filtered_stats) < 2:
        return None, "Choose at least two stats before saving a weighted preset."

    positive_weights = {
        str(key).strip(): float(value)
        for key, value in (weights or {}).items()
        if str(key).strip() and float(value) > 0
    }
    if not positive_weights:
        return None, "Set at least one positive weight before saving a preset."

    preset_id = _slugify(clean_label)
    payload = {
        "version": PRESET_VERSION,
        "kind": PRESET_KIND_WEIGHTED_STAT,
        "preset_type": "stat_rank_weights",
        "id": preset_id,
        "label": clean_label,
        "description": str(description or "").strip(),
        "compatibility": {
            "datasets": [str(dataset or "").strip().lower()],
            "engines": [ENGINE_LEGACY, ENGINE_ADVANCED],
            "objectives": [OBJECTIVE_STAT_RANK],
            "methods": [PRESET_METHOD_WEIGHTED_SUM],
            "scopes": ["single_piece", "full_set", "complete_loadout"],
        },
        "defaults": {
            "preferred_engine": normalize_engine_id(preferred_engine),
            "objective": OBJECTIVE_STAT_RANK,
            "method": PRESET_METHOD_WEIGHTED_SUM,
        },
        "payload": {
            "selected_stats": filtered_stats,
            "weights": positive_weights,
            "optimize_with_weight": bool(optimize_with_weight),
        },
    }
    preset_dir = _preset_dir(root)
    preset_dir.mkdir(parents=True, exist_ok=True)
    target_path = preset_dir / f"{preset_id}.json"
    with target_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return _parse_weighted_preset(payload), None
