"""Detailed-scope formatting and viewport helpers."""

import re
import streamlit.components.v1 as components

DETAIL_SCOPE_ANCHOR_ID = "detail-scope-anchor"

ARMOR_FULL_SCOPE_DESCRIPTION_PLACEHOLDER = (
    "Not implemented — full set description synthesis."
)
ARMOR_CUSTOM_SCOPE_NAME_PLACEHOLDER = "Not implemented — custom set naming."
ARMOR_CUSTOM_SCOPE_DESCRIPTION_PLACEHOLDER = (
    "Not implemented — custom set description synthesis."
)


def normalize_dataset_text(value) -> str:
    """Minimal display-only normalization for dataset text.

    Keeps source data intact while standardizing whitespace and punctuation spacing.
    """
    text = str(value or "")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,;:.!?])", r"\1", text)
    text = re.sub(r"([,;:.!?])(\S)", r"\1 \2", text)
    return text


def focus_detail_anchor(anchor_id: str = DETAIL_SCOPE_ANCHOR_ID):
    """Scroll viewport to the provided detailed-view anchor."""
    components.html(
        (
            "<script>"
            f"const el = window.parent.document.getElementById('{anchor_id}');"
            "if (el) { el.scrollIntoView({behavior: 'auto', block: 'start'}); }"
            "</script>"
        ),
        height=0,
        scrolling=False,
    )
