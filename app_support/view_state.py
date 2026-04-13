"""Typed view-state helpers shared by the Streamlit entrypoint."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlencode


@dataclass(frozen=True)
class DatasetStateKeys:
    view_mode: str
    detail_scope_mode: str
    detail_single_item: str


@dataclass(frozen=True)
class DatasetViewState:
    dataset_key: str
    selected_view_mode: str
    state_keys: DatasetStateKeys
    single_scope_select_label: str
    single_scope_subject_label: str


@dataclass(frozen=True)
class DetailSelectionState:
    scope_mode: str
    selected_name: str | None = None


def safe_stat_key(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_]+", "_", str(value or "").strip()).strip("_")
    return token.lower() if token else "stat"


def resolve_dataset_state_keys(dataset_key: str) -> DatasetStateKeys:
    legacy_keys = {
        ("armors", "view_mode"): "armor_view_mode",
        ("armors", "detailed_scope_mode"): "armor_detailed_scope_mode",
        ("armors", "detail_single_item"): "armor_detail_single_item",
        ("talismans", "view_mode"): "talisman_view_mode",
        ("talismans", "detailed_scope_mode"): "talisman_detailed_scope_mode",
        ("talismans", "detail_single_item"): "talisman_detail_single_item",
    }
    normalized_key = str(dataset_key or "").strip()

    def _state_key(suffix: str) -> str:
        legacy = legacy_keys.get((normalized_key, suffix))
        if legacy:
            return legacy
        return f"{safe_stat_key(normalized_key)}_{suffix}"

    return DatasetStateKeys(
        view_mode=_state_key("view_mode"),
        detail_scope_mode=_state_key("detailed_scope_mode"),
        detail_single_item=_state_key("detail_single_item"),
    )


def resolve_single_scope_select_label(dataset_key: str) -> str:
    return {
        "armors": "Choose Piece:",
        "talismans": "Choose Talisman:",
        "weapons": "Choose Weapon:",
        "shields": "Choose Shield:",
    }.get(str(dataset_key or "").strip(), "Choose Item:")


def resolve_single_scope_subject_label(dataset_key: str) -> str:
    return {
        "armors": "armor item",
        "talismans": "talisman",
        "weapons": "weapon",
        "shields": "shield",
    }.get(str(dataset_key or "").strip(), "item")


def build_dataset_view_state(dataset_key: str, selected_view_mode: str) -> DatasetViewState:
    normalized_key = str(dataset_key or "").strip()
    return DatasetViewState(
        dataset_key=normalized_key,
        selected_view_mode=str(selected_view_mode or "").strip(),
        state_keys=resolve_dataset_state_keys(normalized_key),
        single_scope_select_label=resolve_single_scope_select_label(normalized_key),
        single_scope_subject_label=resolve_single_scope_subject_label(normalized_key),
    )


def build_compare_embed_src(
    dataset_key: str = "",
    *,
    panel_id: str = "",
) -> str:
    params = {"embed": "true"}
    if dataset_key:
        params["dataset"] = str(dataset_key)
    if panel_id:
        params["panel"] = str(panel_id)
    return f"/?{urlencode(params)}"
