"""Schema-driven dataset presentation metadata and formatting helpers."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import re
from typing import Any, Iterable

import pandas as pd


STYLE_LABEL = "label"
STYLE_CAPTION = "caption"

DISPLAY_VARIANT_ITEM_CARD = "item_card"
DISPLAY_VARIANT_PROGRESSION_TABLE = "progression_table"

DETAIL_MODE_SINGLE = "single_row"
DETAIL_MODE_GROUPED = "grouped_rows"

NUMERIC_MISSING_TOKENS = {"???", "n/a", "na", "unknown"}


@dataclass(frozen=True)
class FieldPresentation:
    key: str
    label: str
    formatter: str = "auto"
    source_key: str | None = None
    style: str = STYLE_LABEL
    hide_if_empty: bool = True


@dataclass(frozen=True)
class SectionPresentation:
    title: str
    fields: tuple[FieldPresentation, ...]


@dataclass(frozen=True)
class DatasetPresentationSpec:
    dataset_key: str
    name_field: str = "name"
    display_variant: str = DISPLAY_VARIANT_ITEM_CARD
    detail_mode: str = DETAIL_MODE_SINGLE
    numeric_like_columns: tuple[str, ...] = ()
    card_meta_fields: tuple[FieldPresentation, ...] = ()
    card_metric_fields: tuple[FieldPresentation, ...] = ()
    detail_summary_fields: tuple[FieldPresentation, ...] = ()
    detail_sections: tuple[SectionPresentation, ...] = ()


def _field(
    key: str,
    label: str,
    *,
    formatter: str = "auto",
    source_key: str | None = None,
    style: str = STYLE_LABEL,
    hide_if_empty: bool = True,
) -> FieldPresentation:
    return FieldPresentation(
        key=key,
        label=label,
        formatter=formatter,
        source_key=source_key,
        style=style,
        hide_if_empty=hide_if_empty,
    )


def _section(title: str, *fields: FieldPresentation) -> SectionPresentation:
    return SectionPresentation(title=title, fields=tuple(fields))


def is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except Exception:
        pass
    if isinstance(value, str) and value.strip().lower() in {"", "nan", "none", "null"}:
        return True
    return False


def clean_text(value: Any) -> str:
    if is_missing_value(value):
        return ""
    return str(value).strip()


def coerce_plain_number(value: Any) -> float | None:
    if is_missing_value(value):
        return None
    if isinstance(value, (int, float)):
        try:
            num = float(value)
        except Exception:
            return None
        return num if pd.notna(num) else None

    text = clean_text(value).replace(",", "")
    if not text:
        return None
    if not re.fullmatch(r"[-+]?\d+(?:\.\d+)?", text):
        return None
    try:
        num = float(text)
    except Exception:
        return None
    return num if pd.notna(num) else None


def format_number(value: Any, *, decimals: int = 1, trim_integer: bool = False) -> str:
    num = coerce_plain_number(value)
    if num is None:
        return clean_text(value)
    if trim_integer and float(num).is_integer():
        return str(int(num))
    return f"{num:.{decimals}f}"


def parse_serialized_structure(value: Any) -> Any:
    if is_missing_value(value):
        return None
    if isinstance(value, (dict, list, tuple)):
        return value
    text = clean_text(value)
    if not text or text[0] not in {"{", "["}:
        return None
    try:
        return ast.literal_eval(text)
    except Exception:
        return None


def stringify_structure(value: Any) -> str:
    parsed = parse_serialized_structure(value)
    if parsed is None:
        return clean_text(value)
    return stringify_parsed_structure(parsed)


def stringify_parsed_structure(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            rendered = stringify_parsed_structure(item)
            if rendered:
                parts.append(f"{clean_text(key)}: {rendered}")
        return "; ".join(part for part in parts if part)
    if isinstance(value, (list, tuple, set)):
        rendered_items = [stringify_parsed_structure(item) for item in value]
        cleaned = [item for item in rendered_items if item]
        return ", ".join(cleaned)
    return clean_text(value)


def normalize_talisman_effect_type(effect_value: Any) -> str:
    text = clean_text(effect_value)
    if not text:
        return ""
    text = re.sub(r"^effect\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+by\s+[-+]?\d+(?:\.\d+)?%?\s*$", "", text, flags=re.IGNORECASE)
    return text.strip().rstrip(".:")


def extract_talisman_effect_magnitude(effect_value: Any) -> str:
    text = clean_text(effect_value)
    if not text:
        return ""
    match = re.search(r"\bby\s+([-+]?\d+(?:\.\d+)?%?)\s*$", text, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"([-+]?\d+(?:\.\d+)?%)", text)
    if match:
        return match.group(1)
    return ""


def format_dlc_flag(value: Any) -> str:
    if is_missing_value(value):
        return ""
    if isinstance(value, bool):
        return "DLC" if value else "Base game"
    if isinstance(value, (int, float)):
        return "DLC" if float(value) != 0.0 else "Base game"
    token = clean_text(value).lower()
    return "DLC" if token in {"1", "true", "yes", "y", "dlc"} else "Base game"


def format_requirements_map(value: Any) -> str:
    parsed = parse_serialized_structure(value)
    if not isinstance(parsed, dict):
        return clean_text(value)
    parts = []
    for key, item in parsed.items():
        label = clean_text(key).upper() or clean_text(key)
        rendered = format_number(item, decimals=1, trim_integer=True)
        if rendered:
            parts.append(f"{label} {rendered}")
    return ", ".join(parts)


def infer_formatter(field_key: str, value: Any) -> str:
    token = clean_text(field_key).lower()
    if token == "weight":
        return "weight"
    if token == "dlc":
        return "dlc"
    if token in {"value", "slot", "int", "fai", "arc", "hp cost", "id", "weapon_id", "shield_id"}:
        return "integer"
    if token in {"fp", "fp cost"}:
        return "fp_cost"
    if token == "stamina cost":
        return "stamina_cost"
    if token == "requirements":
        return "requirements_map"
    if parse_serialized_structure(value) is not None:
        return "structured"
    return "text"


def format_presentation_value(value: Any, formatter: str, *, field_key: str = "") -> str:
    formatter_key = formatter if formatter != "auto" else infer_formatter(field_key, value)
    if formatter_key == "text":
        return clean_text(value)
    if formatter_key == "integer":
        return format_number(value, decimals=0, trim_integer=True)
    if formatter_key == "raw_number":
        return format_number(value, decimals=1, trim_integer=True)
    if formatter_key == "weight":
        return format_number(value, decimals=1, trim_integer=False)
    if formatter_key == "fp_cost":
        numeric = coerce_plain_number(value)
        return str(int(numeric)) if numeric is not None and float(numeric).is_integer() else clean_text(value)
    if formatter_key == "stamina_cost":
        numeric = coerce_plain_number(value)
        return str(int(numeric)) if numeric is not None and float(numeric).is_integer() else clean_text(value)
    if formatter_key == "dlc":
        return format_dlc_flag(value)
    if formatter_key == "requirements_map":
        return format_requirements_map(value)
    if formatter_key == "structured":
        return stringify_structure(value)
    if formatter_key == "effect_type":
        return normalize_talisman_effect_type(value)
    if formatter_key == "effect_magnitude":
        return extract_talisman_effect_magnitude(value)
    return clean_text(value)


def resolve_field_source_key(field: FieldPresentation) -> str:
    return field.source_key or field.key


def field_matches_column(field: FieldPresentation, column: str) -> bool:
    token = clean_text(column).lower()
    if not token:
        return False
    return token in {
        clean_text(field.key).lower(),
        clean_text(resolve_field_source_key(field)).lower(),
    }


def format_field_entry(row: pd.Series, field: FieldPresentation) -> str:
    source_key = resolve_field_source_key(field)
    raw_value = row.get(source_key) if source_key in row.index else None
    return format_presentation_value(raw_value, field.formatter, field_key=field.key)


def iter_presented_fields(
    row: pd.Series,
    fields: Iterable[FieldPresentation],
) -> Iterable[tuple[FieldPresentation, str]]:
    for field in fields:
        text = format_field_entry(row, field)
        if field.hide_if_empty and not text:
            continue
        yield field, text


def normalize_numeric_like_columns(
    frame: pd.DataFrame,
    spec: DatasetPresentationSpec | None,
) -> pd.DataFrame:
    if frame is None or frame.empty or spec is None or not spec.numeric_like_columns:
        return frame
    normalized = frame.copy()
    for column in spec.numeric_like_columns:
        if column not in normalized.columns:
            continue
        series = normalized[column]
        if pd.api.types.is_numeric_dtype(series):
            continue
        text_series = series.map(clean_text)
        normalized_text = text_series.mask(text_series.str.lower().isin(NUMERIC_MISSING_TOKENS), "")
        non_empty_mask = normalized_text != ""
        if not non_empty_mask.any():
            continue
        parsed = pd.to_numeric(
            normalized_text[non_empty_mask].str.replace(",", "", regex=False),
            errors="coerce",
        )
        if not parsed.notna().all():
            continue
        normalized[column] = pd.to_numeric(
            normalized_text.str.replace(",", "", regex=False),
            errors="coerce",
        )
    return normalized


def build_default_presentation_spec(dataset_key: str) -> DatasetPresentationSpec:
    return DatasetPresentationSpec(
        dataset_key=dataset_key,
        card_meta_fields=(
            _field("type", "Type"),
            _field("effect", "Effect"),
            _field("description", "Description", style=STYLE_CAPTION),
        ),
        card_metric_fields=(
            _field("weight", "Weight", formatter="weight"),
            _field("value", "Value", formatter="integer"),
        ),
        detail_summary_fields=(
            _field("effect", "Effect"),
            _field("description", "Description", style=STYLE_CAPTION),
        ),
        detail_sections=(
            _section(
                "Details",
                _field("type", "Type"),
                _field("value", "Value", formatter="integer"),
                _field("weight", "Weight", formatter="weight"),
                _field("dlc", "Edition", formatter="dlc"),
            ),
        ),
    )


_EQUIPMENT_CARD_META_FIELDS = (
    _field("category", "Category"),
    _field("damage type", "Damage Type"),
    _field("skill", "Skill"),
    _field("passive effect", "Passive Effect"),
    _field("description", "Description", style=STYLE_CAPTION),
)


_EQUIPMENT_CARD_METRIC_FIELDS = (
    _field("weight", "Weight", formatter="weight"),
    _field("FP cost", "FP Cost", formatter="fp_cost"),
)


_EQUIPMENT_DETAIL_SUMMARY_FIELDS = (
    _field("description", "Description", style=STYLE_CAPTION),
)


_EQUIPMENT_DETAIL_SECTIONS = (
    _section(
        "Combat",
        _field("category", "Category"),
        _field("damage type", "Damage Type"),
        _field("skill", "Skill"),
        _field("passive effect", "Passive Effect"),
        _field("FP cost", "FP Cost", formatter="fp_cost"),
    ),
    _section(
        "Requirements",
        _field("requirements", "Requirements", formatter="requirements_map"),
    ),
    _section(
        "Item",
        _field("weight", "Weight", formatter="weight"),
        _field("dlc", "Edition", formatter="dlc"),
    ),
)


def _equipment_presentation_spec(dataset_key: str) -> DatasetPresentationSpec:
    return DatasetPresentationSpec(
        dataset_key=dataset_key,
        card_meta_fields=_EQUIPMENT_CARD_META_FIELDS,
        card_metric_fields=_EQUIPMENT_CARD_METRIC_FIELDS,
        detail_summary_fields=_EQUIPMENT_DETAIL_SUMMARY_FIELDS,
        detail_sections=_EQUIPMENT_DETAIL_SECTIONS,
    )


_PROGRESSION_CARD_META_FIELDS = (
    _field("upgrade", "Upgrade"),
    _field("attack power", "Attack Power", formatter="structured"),
    _field("damage reduction (%)", "Damage Reduction", formatter="structured"),
)


_PROGRESSION_DETAIL_SECTIONS = (
    _section(
        "Upgrade Path",
        _field("upgrade", "Upgrade"),
        _field("attack power", "Attack Power", formatter="structured"),
        _field("damage reduction (%)", "Damage Reduction", formatter="structured"),
        _field("stat scaling", "Stat Scaling", formatter="structured"),
        _field("passive effects", "Passive Effects", formatter="structured"),
    ),
)


def _progression_presentation_spec(
    dataset_key: str,
    *,
    name_field: str,
) -> DatasetPresentationSpec:
    return DatasetPresentationSpec(
        dataset_key=dataset_key,
        name_field=name_field,
        display_variant=DISPLAY_VARIANT_PROGRESSION_TABLE,
        detail_mode=DETAIL_MODE_GROUPED,
        card_meta_fields=_PROGRESSION_CARD_META_FIELDS,
        detail_sections=_PROGRESSION_DETAIL_SECTIONS,
    )


_DATASET_PRESENTATION_REGISTRY: dict[str, DatasetPresentationSpec] = {
    "armors": DatasetPresentationSpec(
        dataset_key="armors",
        card_meta_fields=(
            _field("special effect", "Special Effect"),
            _field("description", "Description", style=STYLE_CAPTION),
        ),
        card_metric_fields=(
            _field("weight", "Weight", formatter="weight"),
        ),
        detail_summary_fields=(
            _field("special effect", "Special Effect"),
            _field("description", "Description", style=STYLE_CAPTION),
        ),
        detail_sections=(
            _section(
                "Item",
                _field("type", "Type"),
                _field("how to acquire", "How To Acquire"),
                _field("in-game section", "In-Game Section", formatter="integer"),
                _field("weight", "Weight", formatter="weight"),
                _field("dlc", "Edition", formatter="dlc"),
            ),
        ),
    ),
    "talismans": DatasetPresentationSpec(
        dataset_key="talismans",
        numeric_like_columns=("value",),
        card_meta_fields=(
            _field("effect_type", "Effect Type", formatter="effect_type", source_key="effect"),
            _field("effect_magnitude", "Effect Magnitude", formatter="effect_magnitude", source_key="effect"),
            _field("description", "Description", style=STYLE_CAPTION),
        ),
        card_metric_fields=(
            _field("value", "Value", formatter="integer"),
            _field("weight", "Weight", formatter="weight"),
        ),
        detail_summary_fields=(
            _field("effect", "Effect"),
            _field("description", "Description", style=STYLE_CAPTION),
        ),
        detail_sections=(
            _section(
                "Effect",
                _field("effect_type", "Effect Type", formatter="effect_type", source_key="effect"),
                _field("effect_magnitude", "Effect Magnitude", formatter="effect_magnitude", source_key="effect"),
                _field("value", "Value", formatter="integer"),
            ),
            _section(
                "Item",
                _field("weight", "Weight", formatter="weight"),
                _field("dlc", "Edition", formatter="dlc"),
            ),
        ),
    ),
    "incantations": DatasetPresentationSpec(
        dataset_key="incantations",
        numeric_like_columns=("FP",),
        card_meta_fields=(
            _field("effect", "Effect"),
            _field("bonus", "Bonus"),
            _field("group", "Group"),
            _field("description", "Description", style=STYLE_CAPTION),
        ),
        card_metric_fields=(
            _field("FP", "FP", formatter="fp_cost"),
            _field("stamina cost", "Stamina Cost", formatter="stamina_cost"),
            _field("slot", "Slots", formatter="integer"),
            _field("INT", "INT", formatter="integer"),
            _field("FAI", "FAI", formatter="integer"),
            _field("ARC", "ARC", formatter="integer"),
        ),
        detail_summary_fields=(
            _field("effect", "Effect"),
            _field("description", "Description", style=STYLE_CAPTION),
        ),
        detail_sections=(
            _section(
                "Costs",
                _field("FP", "FP", formatter="fp_cost"),
                _field("stamina cost", "Stamina Cost", formatter="stamina_cost"),
                _field("slot", "Slots", formatter="integer"),
            ),
            _section(
                "Requirements",
                _field("INT", "INT", formatter="integer"),
                _field("FAI", "FAI", formatter="integer"),
                _field("ARC", "ARC", formatter="integer"),
            ),
            _section(
                "Spell",
                _field("bonus", "Bonus"),
                _field("group", "Group"),
                _field("location", "Location"),
                _field("dlc", "Edition", formatter="dlc"),
            ),
        ),
    ),
    "sorceries": DatasetPresentationSpec(
        dataset_key="sorceries",
        numeric_like_columns=("FP",),
        card_meta_fields=(
            _field("effect", "Effect"),
            _field("bonus", "Bonus"),
            _field("description", "Description", style=STYLE_CAPTION),
        ),
        card_metric_fields=(
            _field("FP", "FP", formatter="fp_cost"),
            _field("stamina cost", "Stamina Cost", formatter="stamina_cost"),
            _field("slot", "Slots", formatter="integer"),
            _field("INT", "INT", formatter="integer"),
            _field("FAI", "FAI", formatter="integer"),
            _field("ARC", "ARC", formatter="integer"),
        ),
        detail_summary_fields=(
            _field("effect", "Effect"),
            _field("description", "Description", style=STYLE_CAPTION),
        ),
        detail_sections=(
            _section(
                "Costs",
                _field("FP", "FP", formatter="fp_cost"),
                _field("stamina cost", "Stamina Cost", formatter="stamina_cost"),
                _field("slot", "Slots", formatter="integer"),
            ),
            _section(
                "Requirements",
                _field("INT", "INT", formatter="integer"),
                _field("FAI", "FAI", formatter="integer"),
                _field("ARC", "ARC", formatter="integer"),
            ),
            _section(
                "Spell",
                _field("bonus", "Bonus"),
                _field("location", "Location"),
                _field("dlc", "Edition", formatter="dlc"),
            ),
        ),
    ),
    "weapons": _equipment_presentation_spec("weapons"),
    "shields": _equipment_presentation_spec("shields"),
    "ashesOfWar": DatasetPresentationSpec(
        dataset_key="ashesOfWar",
        card_meta_fields=(
            _field("affinity", "Affinity"),
            _field("skill", "Skill"),
            _field("description", "Description", style=STYLE_CAPTION),
        ),
        detail_summary_fields=(
            _field("description", "Description", style=STYLE_CAPTION),
        ),
        detail_sections=(
            _section(
                "Details",
                _field("affinity", "Affinity"),
                _field("skill", "Skill"),
                _field("dlc", "Edition", formatter="dlc"),
            ),
        ),
    ),
    "skills": DatasetPresentationSpec(
        dataset_key="skills",
        card_meta_fields=(
            _field("type", "Type"),
            _field("equipament", "Equipment"),
            _field("charge", "Charge"),
            _field("effect", "Effect", style=STYLE_CAPTION),
        ),
        card_metric_fields=(
            _field("FP", "FP", formatter="text"),
        ),
        detail_summary_fields=(
            _field("effect", "Effect", style=STYLE_CAPTION),
        ),
        detail_sections=(
            _section(
                "Details",
                _field("type", "Type"),
                _field("equipament", "Equipment"),
                _field("charge", "Charge"),
                _field("FP", "FP", formatter="text"),
                _field("locations", "Location"),
                _field("dlc", "Edition", formatter="dlc"),
            ),
        ),
    ),
    "spiritAshes": DatasetPresentationSpec(
        dataset_key="spiritAshes",
        numeric_like_columns=("FP cost",),
        card_meta_fields=(
            _field("type", "Type"),
            _field("effect", "Effect"),
            _field("description", "Description", style=STYLE_CAPTION),
        ),
        card_metric_fields=(
            _field("FP cost", "FP Cost", formatter="fp_cost"),
            _field("HP cost", "HP Cost", formatter="integer"),
        ),
        detail_summary_fields=(
            _field("effect", "Effect"),
            _field("description", "Description", style=STYLE_CAPTION),
        ),
        detail_sections=(
            _section(
                "Summon Costs",
                _field("FP cost", "FP Cost", formatter="fp_cost"),
                _field("HP cost", "HP Cost", formatter="integer"),
                _field("dlc", "Edition", formatter="dlc"),
            ),
        ),
    ),
    "bosses": DatasetPresentationSpec(
        dataset_key="bosses",
        card_meta_fields=(
            _field("HP", "HP"),
            _field("blockquote", "Lore", style=STYLE_CAPTION),
        ),
        detail_summary_fields=(
            _field("blockquote", "Lore", style=STYLE_CAPTION),
        ),
        detail_sections=(
            _section(
                "Encounter",
                _field("HP", "HP"),
                _field("Locations & Drops", "Locations And Drops", formatter="structured"),
                _field("dlc", "Edition", formatter="dlc"),
            ),
        ),
    ),
    "creatures": DatasetPresentationSpec(
        dataset_key="creatures",
        card_meta_fields=(
            _field("blockquote", "Lore", style=STYLE_CAPTION),
        ),
        detail_sections=(
            _section(
                "Encounter",
                _field("locations", "Locations", formatter="structured"),
                _field("drops", "Drops", formatter="structured"),
                _field("dlc", "Edition", formatter="dlc"),
            ),
            _section(
                "Lore",
                _field("blockquote", "Lore"),
            ),
        ),
    ),
    "locations": DatasetPresentationSpec(
        dataset_key="locations",
        card_meta_fields=(
            _field("region", "Region"),
            _field("description", "Description", style=STYLE_CAPTION),
        ),
        detail_summary_fields=(
            _field("description", "Description", style=STYLE_CAPTION),
        ),
        detail_sections=(
            _section(
                "Area",
                _field("region", "Region"),
                _field("items", "Items", formatter="structured"),
                _field("npcs", "NPCs", formatter="structured"),
                _field("creatures", "Creatures", formatter="structured"),
                _field("bosses", "Bosses", formatter="structured"),
                _field("dlc", "Edition", formatter="dlc"),
            ),
        ),
    ),
    "npcs": DatasetPresentationSpec(
        dataset_key="npcs",
        card_meta_fields=(
            _field("role", "Role"),
            _field("location", "Location"),
            _field("voiced by", "Voiced By"),
            _field("description", "Description", style=STYLE_CAPTION),
        ),
        detail_summary_fields=(
            _field("description", "Description", style=STYLE_CAPTION),
        ),
        detail_sections=(
            _section(
                "Profile",
                _field("role", "Role"),
                _field("location", "Location"),
                _field("voiced by", "Voiced By"),
                _field("dlc", "Edition", formatter="dlc"),
            ),
        ),
    ),
    "weapons_upgrades": _progression_presentation_spec(
        "weapons_upgrades",
        name_field="weapon name",
    ),
    "shields_upgrades": _progression_presentation_spec(
        "shields_upgrades",
        name_field="shield name",
    ),
}


def resolve_dataset_presentation_spec(dataset_key: str) -> DatasetPresentationSpec:
    token = clean_text(dataset_key)
    if not token:
        return build_default_presentation_spec("")
    if token in _DATASET_PRESENTATION_REGISTRY:
        return _DATASET_PRESENTATION_REGISTRY[token]
    if token.startswith("items/"):
        return build_default_presentation_spec(token)
    return build_default_presentation_spec(token)