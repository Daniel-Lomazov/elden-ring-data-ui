"""Dataset UI capability registry and shared dataset resolvers."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Sequence

import pandas as pd

VIEW_MODE_DETAILED = "Detailed view"
VIEW_MODE_OPTIMIZATION = "Optimization view"

DATASET_FAMILY_ARMOR = "armor"
DATASET_FAMILY_TALISMAN = "talisman"
DATASET_FAMILY_CATALOG = "catalog"
DATASET_FAMILY_PROGRESSION = "progression"
DATASET_FAMILY_UNSUPPORTED = "unsupported"

SCOPE_SINGLE = "Single"
SCOPE_FULL = "Full"
SCOPE_CUSTOM = "Custom"
SCOPE_FULL_SET = "Full Set"

_ARMOR_STATUS_RESISTANCE_COLS = (
    "status.poison",
    "status.rot",
    "status.bleed",
    "status.frost",
    "status.sleep",
    "status.madness",
    "status.death",
)

_ARMOR_PRIMARY_STAT_ORDER = (
    "Dmg: Phy",
    "Dmg: VS Str.",
    "Dmg: VS Sla.",
    "Dmg: VS Pie.",
    "Dmg: Mag",
    "Dmg: Fir",
    "Dmg: Lit",
    "Dmg: Hol",
    *_ARMOR_STATUS_RESISTANCE_COLS,
    "Res: Poi.",
)


@dataclass(frozen=True)
class DatasetUiSpec:
    dataset_key: str
    label: str
    family: str
    supported_views: tuple[str, ...]
    supported_scopes: tuple[str, ...]
    supports_ranking: bool
    supports_multi_stat_sort: bool
    supports_optimization: bool
    default_sort_field: str
    card_meta_fields: tuple[str, ...]
    detail_fields: tuple[str, ...]
    loader_profile: str | None
    unsupported_reason: str | None = None
    show_in_selector: bool = True


def _pretty_dataset_label(dataset_key: str) -> str:
    label = str(dataset_key or "").replace("/", " / ").replace("_", " ")
    label = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", label)
    return " ".join(part.capitalize() for part in label.split())


def _catalog_spec(
    dataset_key: str,
    *,
    default_sort_field: str = "name",
    supports_multi_stat_sort: bool = True,
    show_in_selector: bool = True,
) -> DatasetUiSpec:
    return DatasetUiSpec(
        dataset_key=dataset_key,
        label=_pretty_dataset_label(dataset_key),
        family=DATASET_FAMILY_CATALOG,
        supported_views=("Catalog",),
        supported_scopes=tuple(),
        supports_ranking=True,
        supports_multi_stat_sort=supports_multi_stat_sort,
        supports_optimization=False,
        default_sort_field=default_sort_field,
        card_meta_fields=("description", "effect", "type"),
        detail_fields=("description", "effect", "type", "value", "weight", "dlc"),
        loader_profile=None,
        show_in_selector=show_in_selector,
    )


_EQUIPMENT_CARD_META_FIELDS = (
    "category",
    "damage type",
    "skill",
    "passive effect",
    "description",
)


_EQUIPMENT_DETAIL_FIELDS = (
    "category",
    "damage type",
    "skill",
    "passive effect",
    "requirements",
    "FP cost",
    "weight",
    "dlc",
    "description",
)


def _equipment_spec(
    dataset_key: str,
    *,
    label: str,
) -> DatasetUiSpec:
    return DatasetUiSpec(
        dataset_key=dataset_key,
        label=label,
        family=DATASET_FAMILY_CATALOG,
        supported_views=(VIEW_MODE_DETAILED, "Catalog"),
        supported_scopes=(SCOPE_SINGLE,),
        supports_ranking=True,
        supports_multi_stat_sort=True,
        supports_optimization=False,
        default_sort_field="weight",
        card_meta_fields=_EQUIPMENT_CARD_META_FIELDS,
        detail_fields=_EQUIPMENT_DETAIL_FIELDS,
        loader_profile=None,
    )


def _progression_spec(
    dataset_key: str,
    *,
    label: str,
    default_sort_field: str,
) -> DatasetUiSpec:
    return DatasetUiSpec(
        dataset_key=dataset_key,
        label=label,
        family=DATASET_FAMILY_PROGRESSION,
        supported_views=("Catalog",),
        supported_scopes=tuple(),
        supports_ranking=False,
        supports_multi_stat_sort=False,
        supports_optimization=False,
        default_sort_field=default_sort_field,
        card_meta_fields=("upgrade", "attack power", "damage reduction (%)"),
        detail_fields=(
            "upgrade",
            "attack power",
            "damage reduction (%)",
            "stat scaling",
            "passive effects",
        ),
        loader_profile="progression_table_visual",
    )


_DATASET_UI_REGISTRY: dict[str, DatasetUiSpec] = {
    "armors": DatasetUiSpec(
        dataset_key="armors",
        label="Armors",
        family=DATASET_FAMILY_ARMOR,
        supported_views=(VIEW_MODE_DETAILED, VIEW_MODE_OPTIMIZATION),
        supported_scopes=(SCOPE_SINGLE, SCOPE_FULL, SCOPE_CUSTOM),
        supports_ranking=True,
        supports_multi_stat_sort=True,
        supports_optimization=True,
        default_sort_field="Dmg: Phy",
        card_meta_fields=("description", "special effect"),
        detail_fields=(
            "description",
            "special effect",
            "how to acquire",
            "in-game section",
            "type",
            "weight",
            "dlc",
        ),
        loader_profile="single_piece_visual",
    ),
    "talismans": DatasetUiSpec(
        dataset_key="talismans",
        label="Talismans",
        family=DATASET_FAMILY_TALISMAN,
        supported_views=(VIEW_MODE_DETAILED, VIEW_MODE_OPTIMIZATION),
        supported_scopes=(SCOPE_SINGLE, SCOPE_CUSTOM, SCOPE_FULL_SET),
        supports_ranking=True,
        supports_multi_stat_sort=True,
        supports_optimization=True,
        default_sort_field="value",
        card_meta_fields=("effect", "description"),
        detail_fields=("effect", "description", "value", "weight", "dlc"),
        loader_profile=None,
    ),
    "ashesOfWar": _catalog_spec("ashesOfWar"),
    "bosses": _catalog_spec("bosses"),
    "creatures": _catalog_spec("creatures"),
    "incantations": _catalog_spec("incantations"),
    "locations": _catalog_spec("locations"),
    "npcs": _catalog_spec("npcs"),
    "shields": _equipment_spec("shields", label="Shields"),
    "skills": _catalog_spec("skills"),
    "sorceries": _catalog_spec("sorceries"),
    "spiritAshes": _catalog_spec("spiritAshes"),
    "weapons": _equipment_spec("weapons", label="Weapons"),
    "items/ammos": _catalog_spec("items/ammos", show_in_selector=False),
    "items/bells": _catalog_spec("items/bells", show_in_selector=False),
    "items/consumables": _catalog_spec("items/consumables", show_in_selector=False),
    "items/cookbooks": _catalog_spec("items/cookbooks", show_in_selector=False),
    "items/crystalTears": _catalog_spec("items/crystalTears", show_in_selector=False),
    "items/greatRunes": _catalog_spec("items/greatRunes", show_in_selector=False),
    "items/keyItems": _catalog_spec("items/keyItems", show_in_selector=False),
    "items/materials": _catalog_spec("items/materials", show_in_selector=False),
    "items/multi": _catalog_spec("items/multi", show_in_selector=False),
    "items/remembrances": _catalog_spec(
        "items/remembrances",
        default_sort_field="value",
        show_in_selector=False,
    ),
    "items/tools": _catalog_spec("items/tools", show_in_selector=False),
    "items/upgradeMaterials": _catalog_spec("items/upgradeMaterials", show_in_selector=False),
    "items/whetblades": _catalog_spec("items/whetblades", show_in_selector=False),
    "shields_upgrades": _progression_spec(
        "shields_upgrades",
        label="Shields Upgrades",
        default_sort_field="shield name",
    ),
    "weapons_upgrades": _progression_spec(
        "weapons_upgrades",
        label="Weapons Upgrades",
        default_sort_field="weapon name",
    ),
}


def _list_registered_dataset_keys(
    available_datasets: Sequence[str] | None = None,
) -> tuple[str, ...]:
    if available_datasets is None:
        keys = list(_DATASET_UI_REGISTRY.keys())
    else:
        keys = [str(key).strip() for key in available_datasets if str(key).strip()]
    return tuple(key for key in keys if key in _DATASET_UI_REGISTRY)


def list_visible_datasets(available_datasets: Sequence[str] | None = None) -> tuple[str, ...]:
    keys = _list_registered_dataset_keys(available_datasets)
    return tuple(
        key for key in keys if bool(_DATASET_UI_REGISTRY[key].show_in_selector)
    )


def list_supported_datasets(available_datasets: Sequence[str] | None = None) -> tuple[str, ...]:
    keys = _list_registered_dataset_keys(available_datasets)
    supported = []
    for key in keys:
        spec = _DATASET_UI_REGISTRY.get(key)
        if spec is None or spec.unsupported_reason:
            continue
        supported.append(key)
    return tuple(supported)


def format_dataset_selector_label(
    spec: DatasetUiSpec | None,
    dataset_key: str = "",
) -> str:
    if spec is None:
        return _pretty_dataset_label(dataset_key)
    if spec.unsupported_reason:
        return f"{spec.label} (Not implemented yet)"
    return spec.label


def resolve_dataset_ui_spec(dataset_key: str) -> DatasetUiSpec | None:
    token = str(dataset_key or "").strip()
    if not token:
        return None
    return _DATASET_UI_REGISTRY.get(token)


def resolve_rankable_numeric_fields(
    df: pd.DataFrame,
    spec: DatasetUiSpec | None,
) -> tuple[str, ...]:
    if spec is None or df is None or df.empty or not spec.supports_ranking:
        return tuple()

    numeric_cols = [str(col) for col in df.select_dtypes(include=["number"]).columns.tolist()]
    if spec.family == DATASET_FAMILY_ARMOR:
        stat_options = [
            col
            for col in numeric_cols
            if col.startswith("Dmg:") or col.startswith("status.")
        ]
        if "Res: Poi." in numeric_cols and "Res: Poi." not in stat_options:
            stat_options.append("Res: Poi.")
        ordered = [stat for stat in _ARMOR_PRIMARY_STAT_ORDER if stat in stat_options]
        ordered.extend([stat for stat in stat_options if stat not in ordered])
        return tuple(ordered)

    if spec.family == DATASET_FAMILY_TALISMAN:
        return tuple(
            col
            for col in numeric_cols
            if str(col).strip().lower() not in {"id", "dlc", "weight"}
        )

    return tuple(
        col
        for col in numeric_cols
        if str(col).strip().lower() not in {"id", "dlc"}
    )


def resolve_default_view(spec: DatasetUiSpec | None) -> str:
    if spec is None or not spec.supported_views:
        return ""
    return str(spec.supported_views[0])
