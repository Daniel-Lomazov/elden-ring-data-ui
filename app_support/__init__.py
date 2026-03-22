"""Support utilities for the Streamlit app."""

from .detail_scope import (
    DETAIL_SCOPE_ANCHOR_ID,
    ARMOR_FULL_SCOPE_DESCRIPTION_PLACEHOLDER,
    ARMOR_CUSTOM_SCOPE_NAME_PLACEHOLDER,
    ARMOR_CUSTOM_SCOPE_DESCRIPTION_PLACEHOLDER,
    normalize_dataset_text,
    focus_detail_anchor,
)
from .dataset_ui import (
    DATASET_FAMILY_ARMOR,
    DATASET_FAMILY_CATALOG,
    DATASET_FAMILY_TALISMAN,
    DATASET_FAMILY_UNSUPPORTED,
    DatasetUiSpec,
    list_supported_datasets,
    resolve_dataset_ui_spec,
    resolve_default_view,
    resolve_rankable_numeric_fields,
)
from .optimization_view import (
    OptimizationViewState,
    list_encounter_profiles,
    list_weighted_preset_options,
    load_encounter_profile_request,
    load_weighted_preset_option,
    resolve_optimization_view_state,
    save_weighted_preset,
)

__all__ = [
    "DETAIL_SCOPE_ANCHOR_ID",
    "ARMOR_FULL_SCOPE_DESCRIPTION_PLACEHOLDER",
    "ARMOR_CUSTOM_SCOPE_NAME_PLACEHOLDER",
    "ARMOR_CUSTOM_SCOPE_DESCRIPTION_PLACEHOLDER",
    "normalize_dataset_text",
    "focus_detail_anchor",
    "DATASET_FAMILY_ARMOR",
    "DATASET_FAMILY_CATALOG",
    "DATASET_FAMILY_TALISMAN",
    "DATASET_FAMILY_UNSUPPORTED",
    "DatasetUiSpec",
    "list_supported_datasets",
    "resolve_dataset_ui_spec",
    "resolve_default_view",
    "resolve_rankable_numeric_fields",
    "OptimizationViewState",
    "list_encounter_profiles",
    "list_weighted_preset_options",
    "load_encounter_profile_request",
    "load_weighted_preset_option",
    "resolve_optimization_view_state",
    "save_weighted_preset",
]
