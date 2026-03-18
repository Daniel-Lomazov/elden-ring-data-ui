"""Support utilities for the Streamlit app."""

from .detail_scope import (
    DETAIL_SCOPE_ANCHOR_ID,
    ARMOR_FULL_SCOPE_DESCRIPTION_PLACEHOLDER,
    ARMOR_CUSTOM_SCOPE_NAME_PLACEHOLDER,
    ARMOR_CUSTOM_SCOPE_DESCRIPTION_PLACEHOLDER,
    normalize_dataset_text,
    focus_detail_anchor,
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
    "OptimizationViewState",
    "list_encounter_profiles",
    "list_weighted_preset_options",
    "load_encounter_profile_request",
    "load_weighted_preset_option",
    "resolve_optimization_view_state",
    "save_weighted_preset",
]
