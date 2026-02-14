"""Minimal app for ranking/sorting armors and similar datasets."""

import streamlit as st
import pandas as pd
import re
import json
import hashlib
import subprocess
import sys
import html
import copy
from pathlib import Path

try:
    import plotly.graph_objects as go
except Exception:
    go = None

try:
    from streamlit_plotly_events import plotly_events
except Exception:
    plotly_events = None

from data_loader import DataLoader
from ui_components import parse_armor_stats
from optimizer import (
    optimize_single_piece,
    DEFAULT_OPTIMIZATION_METHOD,
    OPTIMIZER_METHODS,
)
from histogram_views import (
    HISTOGRAM_CONFIG,
    build_histogram_spec,
    render_classic_histogram,
    build_interactive_histogram_figure,
    get_clicked_weight,
)
from histogram_layout import resolve_auto_render_layer

st.set_page_config(page_title="Elden Ring - Ranking UI", page_icon="🏆", layout="wide")

MULTI_STAT_METHOD = DEFAULT_OPTIMIZATION_METHOD

ARMOR_MODE_SINGLE_PIECE = "single_piece"
ARMOR_MODE_FULL_ARMOR_SET = "full_armor_set"
ARMOR_MODE_COMPLETE_ARMOR_SET = "complete_armor_set"
ARMOR_MODE_LABELS = {
    ARMOR_MODE_SINGLE_PIECE: "Single piece",
    ARMOR_MODE_FULL_ARMOR_SET: "Full armor set",
    ARMOR_MODE_COMPLETE_ARMOR_SET: "Complete armor set",
}

TALISMAN_MODE_SINGLE = "single"
TALISMAN_MODE_FULL_SET = "full_set"
TALISMAN_MODE_LABELS = {
    TALISMAN_MODE_SINGLE: "Single",
    TALISMAN_MODE_FULL_SET: "Full set",
}
TALISMAN_SLOT_LABELS = ["Slot 1", "Slot 2", "Slot 3", "Slot 4"]

VIEW_MODE_OPTIMIZATION = "Optimization view"
VIEW_MODE_DETAILED = "Detailed view"
DETAILED_SCOPE_SINGLE = "Single"
DETAILED_SCOPE_FULL = "Full"
DETAILED_SCOPE_CUSTOM = "Custom"
STACK_VIEW_VERTICAL = "Vertical"
STACK_VIEW_HORIZONTAL = "Horizontal"

ARMOR_PIECE_ORDER = [
    "Helm",
    "Armor",
    "Gauntlets",
    "Greaves",
]

FULL_SET_LABELS = {
    "Helm": "Helm",
    "Armor": "Armor",
    "Gauntlets": "Gauntlets",
    "Greaves": "Greaves",
    "Overall": "Overall",
}

TALISMAN_FULL_SET_LABELS = {
    "Slot 1": "Slot 1",
    "Slot 2": "Slot 2",
    "Slot 3": "Slot 3",
    "Slot 4": "Slot 4",
    "Overall": "Overall",
}

FULL_SET_COLUMN_COUNT = 5
FULL_SET_PIECE_COLUMN_COUNT = 4
FULL_SET_CARD_HEIGHT_PX = 380
FULL_SET_IMAGE_SIZE_PX = 160
FULL_SET_PHANTOM_IMAGE_HEIGHT_PX = 159
FULL_SET_COLUMN_GAP_RATIO = 0.12
FULL_SET_ROW_GAP_PX = 0

HIST_VIEW_OPTIONS = [
    "Classic",
    "Interactive (click-to-set)",
]

DEFAULT_ACTIVE_DATASET_KEYS = ["armors", "talismans"]

# Post-parse pruning rules to reduce memory pressure without affecting visible UI.
POST_PARSE_DROP_COLUMNS_BY_DATASET = {
    "armors": ["damage negation", "resistance"],
}


def normalize_hist_view_mode(value: str) -> str:
    normalized = str(value or "").strip()
    if normalized == "Side-by-side":
        return "Interactive (click-to-set)"
    if normalized in HIST_VIEW_OPTIONS:
        return normalized
    return "Interactive (click-to-set)"


def build_hist_click_key(
    scope: str,
    dataset: str,
    armor_piece_type,
    hist_view_mode: str,
    max_weight_limit,
) -> str:
    piece = str(armor_piece_type or "all")
    safe_piece = re.sub(r"[^A-Za-z0-9_\-]+", "_", piece)
    safe_dataset = re.sub(r"[^A-Za-z0-9_\-]+", "_", str(dataset or "dataset"))
    safe_mode = re.sub(r"[^A-Za-z0-9_\-]+", "_", normalize_hist_view_mode(hist_view_mode))
    try:
        weight_token = f"{float(max_weight_limit):.3f}"
    except Exception:
        weight_token = "na"
    return f"weight_hist_click_{scope}_{safe_dataset}_{safe_piece}_{safe_mode}_{weight_token}"


def safe_stat_key(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_]+", "_", str(value or "").strip()).strip("_")
    return token.lower() if token else "stat"


def apply_post_parse_column_pruning(dataset_key: str, frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return frame
    drop_columns = POST_PARSE_DROP_COLUMNS_BY_DATASET.get(str(dataset_key), [])
    if not drop_columns:
        return frame
    return DataLoader.drop_columns(frame, drop_columns)


@st.cache_resource
def get_loader(loader_version: str = "v2_profile_loader"):
    _ = loader_version
    return DataLoader(data_dir="data")


def main():
    # Integrity check: verify data files against data_checksums.json (generate if missing)
    ROOT = Path(__file__).parent
    manifest_path = ROOT / "data_checksums.json"

    def sha256_of_file(p: Path, buf_size: int = 65536) -> str:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(buf_size), b""):
                h.update(chunk)
        return h.hexdigest()

    def generate_manifest():
        # run the secure_data helper to (re)generate manifest + backup
        try:
            subprocess.run([sys.executable, str(ROOT / "secure_data.py")], check=True)
        except Exception:
            pass

    def generate_armor_map():
        # run the mapping helper to (re)generate armor_column_map.json
        try:
            subprocess.run(
                ["python", str(ROOT / "check_armor_mappings.py")], check=True
            )
        except Exception:
            pass

    def load_manifest():
        if not manifest_path.exists():
            return None
        try:
            with manifest_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def verify_manifest():
        m = load_manifest()
        if not m:
            return None
        missing = []
        mismatches = []
        for it in m.get("files", []):
            p = ROOT / it["path"]
            if not p.exists():
                missing.append(it["path"])
                continue
            actual = sha256_of_file(p)
            if actual != it.get("sha256"):
                mismatches.append(
                    {"path": it["path"], "expected": it.get("sha256"), "actual": actual}
                )
        return {"missing": missing, "mismatches": mismatches}

    def format_metric_value(value):
        try:
            if value is None:
                return "0.00"

            if isinstance(value, str):
                token = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", value)
                if token:
                    num = float(token.group(0))
                else:
                    return str(value)
            else:
                num = float(value)

            if not pd.notna(num) or num in (float("inf"), float("-inf")):
                return "0.00"

            return f"{num:.2f}"
        except Exception:
            return str(value)

    def is_truthy_flag(value) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            try:
                return float(value) != 0.0
            except Exception:
                return False
        token = str(value).strip().lower()
        return token in {"1", "true", "yes", "y", "dlc"}

    def talisman_dlc_label(value) -> str:
        return "🧩 DLC" if is_truthy_flag(value) else "🛡️ Base game"

    def normalize_talisman_effect_type(effect_value) -> str:
        token = str(effect_value or "").strip()
        if not token:
            return ""
        token = re.sub(r"^effect\s+", "", token, flags=re.IGNORECASE)
        token = token.split(" by ")[0]
        token = token.split(".")[0]
        return token.strip()

    def abbreviate_talisman_effect_label(effect_type: str, max_len: int = 34) -> str:
        token = str(effect_type or "").strip()
        if not token:
            return token
        if len(token) <= max_len:
            return token
        words = token.split()
        compressed = " ".join(
            word if len(word) <= 6 else f"{word[:4]}."
            for word in words
        )
        if len(compressed) <= max_len:
            return compressed
        return compressed[: max_len - 1].rstrip() + "…"

    def talisman_effect_group(effect_type: str) -> str:
        token = str(effect_type or "").strip().lower()
        if not token:
            return "Other effects"

        if "restore" in token and "hp" in token:
            return "HP restoration"
        if "restore" in token and "fp" in token:
            return "FP restoration"

        attack_keywords = [
            "attack power",
            "damage",
            "skill",
            "critical",
            "counterattack",
            "jump attack",
            "charge attack",
            "roars",
            "breath",
            "successive attacks",
        ]
        if any(keyword in token for keyword in attack_keywords):
            return "Attack power boosts"

        defense_keywords = [
            "negation",
            "reduces",
            "resistance",
            "defense",
            "damage taken",
            "blocking",
            "poise",
            "immunity",
            "focus",
            "robustness",
            "vitality",
        ]
        if any(keyword in token for keyword in defense_keywords):
            return "Defense / negation"

        utility_keywords = [
            "stealth",
            "conceals",
            "attracts",
            "acquisition",
            "item discovery",
            "memory slots",
            "casting",
            "range",
            "horseback",
            "equip load",
        ]
        if any(keyword in token for keyword in utility_keywords):
            return "Utility / stealth"

        if token.startswith("raises") or "raises " in token:
            return "Attribute / scaling"

        return "Passive effects"

    def format_item_detail_value(column: str, value):
        if value is None:
            return "—"
        try:
            if pd.isna(value):
                return "—"
        except Exception:
            pass

        column_key = str(column or "").strip().lower()
        if dataset == "talismans" and column_key == "dlc":
            return talisman_dlc_label(value)

        if isinstance(value, (int, float)):
            return format_metric_value(value)
        return str(value)

    def format_item_detail_label(column: str) -> str:
        token = str(column or "").strip()
        if not token:
            return "Field"
        return token.replace("_", " ").title()

    def render_item_detail_inspector(source_df: pd.DataFrame, panel_key: str):
        if source_df is None or source_df.empty or "name" not in source_df.columns:
            return

        name_series = source_df["name"].dropna().astype(str).str.strip()
        name_options = [name for name in name_series.tolist() if name]
        if not name_options:
            return
        deduped_names = list(dict.fromkeys(name_options))

        select_key = f"item_detail_name_{panel_key}"
        pending_focus_name = st.session_state.get("item_detail_focus_name")
        expand_key = f"item_detail_expand_{panel_key}"
        expanded = bool(st.session_state.get(expand_key, False))
        if pending_focus_name in deduped_names:
            st.session_state[select_key] = pending_focus_name
            del st.session_state["item_detail_focus_name"]
            expanded = True
            st.session_state[expand_key] = True

        ensure_state_in_options(select_key, deduped_names, deduped_names[0])

        with st.expander("Item details", expanded=expanded):
            selected_name = st.selectbox(
                "Open item:",
                options=deduped_names,
                key=select_key,
            )
            st.caption(f"Focused item: {selected_name}")
            selected_rows = source_df[source_df["name"].astype(str) == str(selected_name)]
            if selected_rows.empty:
                st.info("No details available for this item.")
                return

            selected_row = selected_rows.iloc[0]

            if "image" in source_df.columns and pd.notna(selected_row.get("image")):
                try:
                    st.image(selected_row.get("image"), width=140)
                except Exception:
                    pass

            if dataset == "talismans":
                effect_text = str(selected_row.get("effect", "")).strip()
                if effect_text:
                    st.markdown(f"**Effect:** {effect_text}")

                if "description" in source_df.columns and pd.notna(selected_row.get("description")):
                    st.caption(str(selected_row.get("description", "")))
            else:
                if "description" in source_df.columns and pd.notna(selected_row.get("description")):
                    st.caption(str(selected_row.get("description", "")))

            hidden_columns = {"description", "image", "effect"}
            detail_rows = []
            for column in source_df.columns:
                if column in hidden_columns:
                    continue
                detail_rows.append(
                    {
                        "Field": format_item_detail_label(column),
                        "Value": format_item_detail_value(column, selected_row.get(column)),
                    }
                )

            if detail_rows:
                st.dataframe(pd.DataFrame(detail_rows), use_container_width=True, hide_index=True)

    def qp_get(key: str, default: str = "") -> str:
        try:
            if hasattr(st, "query_params"):
                val = st.query_params.get(key, default)
                if isinstance(val, list):
                    return val[0] if val else default
                return str(val)

            legacy = st.experimental_get_query_params()
            val = legacy.get(key, [default])
            if isinstance(val, list):
                return str(val[0]) if val else default
            return str(val)
        except Exception:
            return default

    def qp_get_bool(key: str, default: bool = False) -> bool:
        return qp_get(key, "true" if default else "false").lower() == "true"

    def qp_get_int(key: str, default: int) -> int:
        try:
            return int(qp_get(key, str(default)))
        except Exception:
            return default

    def qp_update(params: dict):
        try:
            if hasattr(st, "query_params"):
                st.query_params.update(params)
            else:
                st.experimental_set_query_params(**params)
        except Exception:
            pass

    def qp_clear():
        try:
            if hasattr(st, "query_params"):
                st.query_params.clear()
            else:
                st.experimental_set_query_params()
        except Exception:
            pass


    def normalize_armor_mode(value: str) -> str:
        raw = str(value or "").strip().lower()
        legacy_map = {
            "single piece": ARMOR_MODE_SINGLE_PIECE,
            "full list": ARMOR_MODE_FULL_ARMOR_SET,
            "full armor set": ARMOR_MODE_FULL_ARMOR_SET,
            "full almost set": ARMOR_MODE_COMPLETE_ARMOR_SET,
            "full_almost_set": ARMOR_MODE_COMPLETE_ARMOR_SET,
            "complete armor set": ARMOR_MODE_COMPLETE_ARMOR_SET,
            "complete_armor_set": ARMOR_MODE_COMPLETE_ARMOR_SET,
        }
        normalized = legacy_map.get(raw, raw)
        if normalized not in ARMOR_MODE_LABELS:
            return ARMOR_MODE_SINGLE_PIECE
        return normalized

    def normalize_talisman_mode(value: str) -> str:
        raw = str(value or "").strip().lower()
        legacy_map = {
            "single piece": TALISMAN_MODE_SINGLE,
            "single": TALISMAN_MODE_SINGLE,
            "full set": TALISMAN_MODE_FULL_SET,
            "full talisman set": TALISMAN_MODE_FULL_SET,
        }
        normalized = legacy_map.get(raw, raw)
        if normalized not in TALISMAN_MODE_LABELS:
            return TALISMAN_MODE_SINGLE
        return normalized

    def on_hist_view_mode_change():
        st.session_state["hist_view_mode"] = normalize_hist_view_mode(
            st.session_state.get("hist_view_mode_widget", "Interactive (click-to-set)")
        )

    def reset_ui_state():
        current_armor_mode = st.session_state.get("armor_mode")
        current_talisman_mode = st.session_state.get("talisman_mode")
        reset_keys = [
            "selected_dataset_label",
            "armor_piece_type",
            "talisman_mode",
            "highlighted_stats",
            "lock_stat_order",
            "single_highlight_stat",
            "sort_order",
            "rows_to_show",
            "show_raw_dev",
            "optimizer_method",
            "use_max_weight",
            "hist_view_mode",
            "hist_view_mode_widget",
            "max_weight_limit",
            "_qp_hydrated",
            "_optimizer_cache",
            "_opt_weight_stats_signature",
        ]
        for key in reset_keys:
            if key in st.session_state:
                del st.session_state[key]
        dynamic_weight_keys = [
            key for key in list(st.session_state.keys()) if key.startswith("opt_weight_")
        ]
        for key in dynamic_weight_keys:
            del st.session_state[key]
        qp_clear()
        if current_armor_mode:
            st.session_state["armor_mode"] = current_armor_mode
            qp_update({"armor_mode": current_armor_mode})
        if current_talisman_mode:
            st.session_state["talisman_mode"] = current_talisman_mode
            qp_update({"talisman_mode": current_talisman_mode})
        st.session_state["_force_reset_rerun"] = True

    def sync_optimizer_weight_state(stats: list[str]):
        signature = "|".join([str(s) for s in stats])
        if st.session_state.get("_opt_weight_stats_signature") == signature:
            return
        allowed_keys = {f"opt_weight_{safe_stat_key(stat)}" for stat in stats}
        for key in list(st.session_state.keys()):
            if key.startswith("opt_weight_") and key not in allowed_keys:
                del st.session_state[key]
        st.session_state["_opt_weight_stats_signature"] = signature

    if "_qp_hydrated" not in st.session_state:
        st.session_state["selected_dataset_label"] = qp_get("dataset", "")
        st.session_state["armor_mode"] = normalize_armor_mode(
            qp_get("armor_mode", ARMOR_MODE_SINGLE_PIECE)
        )
        st.session_state["talisman_mode"] = normalize_talisman_mode(
            qp_get("talisman_mode", TALISMAN_MODE_SINGLE)
        )
        st.session_state["armor_piece_type"] = qp_get("piece_type", "")
        st.session_state["highlighted_stats"] = [
            s for s in qp_get("stats", "").split("|") if s
        ]
        st.session_state["lock_stat_order"] = qp_get_bool("lock_order", True)
        st.session_state["single_highlight_stat"] = qp_get("single_stat", "")
        st.session_state["sort_order"] = qp_get("sort", "Highest First")
        st.session_state["rows_to_show"] = qp_get_int("rows", 5)
        st.session_state["show_raw_dev"] = False
        st.session_state["optimizer_method"] = qp_get(
            "method", DEFAULT_OPTIMIZATION_METHOD
        )
        st.session_state["optimize_with_weight"] = qp_get_bool("opt_with_weight", False)
        st.session_state["use_max_weight"] = qp_get_bool("use_max_weight", False)
        st.session_state["hist_view_mode"] = normalize_hist_view_mode(
            qp_get("hist_view", "Interactive (click-to-set)")
        )
        st.session_state["hist_view_mode_widget"] = st.session_state["hist_view_mode"]
        try:
            st.session_state["max_weight_limit"] = float(qp_get("max_weight", "0.0"))
        except Exception:
            st.session_state["max_weight_limit"] = 0.0
        st.session_state["_qp_hydrated"] = True

    # Apply deferred updates before widgets are instantiated.
    if st.session_state.get("_force_reset_rerun"):
        del st.session_state["_force_reset_rerun"]
        st.rerun()

    if "_pending_max_weight_limit" in st.session_state:
        try:
            st.session_state["max_weight_limit"] = float(
                st.session_state["_pending_max_weight_limit"]
            )
        except Exception:
            pass
        del st.session_state["_pending_max_weight_limit"]

    def frame_signature(frame: pd.DataFrame, cols: list) -> str:
        target_cols = [c for c in cols if c in frame.columns]
        if not target_cols:
            return f"rows:{len(frame)}"
        hashed = pd.util.hash_pandas_object(
            frame[target_cols].fillna(""), index=False
        ).values
        return hashlib.sha256(hashed.tobytes()).hexdigest()

    def ensure_state_in_options(key: str, options: list, fallback):
        current = st.session_state.get(key, fallback)
        if current not in options:
            st.session_state[key] = fallback

    def ensure_state_multiselect(key: str, options: list, fallback: list):
        current = st.session_state.get(key, fallback)
        if not isinstance(current, list):
            current = []
        filtered = [x for x in current if x in options]
        if not filtered:
            filtered = [x for x in fallback if x in options]
        st.session_state[key] = filtered


    # Ensure manifest exists
    if not manifest_path.exists():
        st.sidebar.info("No checksum manifest found — generating now...")
        generate_manifest()

    # Ensure armor_column_map exists; if missing, inform the user how to generate it
    armor_map_path = ROOT / "armor_column_map.json"
    if not armor_map_path.exists():
        st.sidebar.info(
            "No armor mapping found — run the mapping helper to create `armor_column_map.json` if desired."
        )

    check = verify_manifest()
    integrity_ok = bool(
        check is not None and not check.get("missing") and not check.get("mismatches")
    )
    integrity_btn_col, integrity_status_col = st.sidebar.columns([8, 1])
    with integrity_btn_col:
        integrity_test_clicked = st.button(
            "Test data integrity",
            key="test_data_integrity",
        )
    with integrity_status_col:
        if integrity_ok:
            st.markdown(
                "<div style='display:flex;justify-content:center;align-items:center;height:2.2rem;'>✅</div>",
                unsafe_allow_html=True,
            )

    if check is None:
        st.sidebar.warning(
            "Checksum manifest not loadable or missing. You can regenerate it."
        )
    else:
        if check["missing"] or check["mismatches"]:
            with st.sidebar.expander("Data integrity: Issues detected", expanded=True):
                if check["missing"]:
                    st.write("Missing files:")
                    for mfile in check["missing"]:
                        st.write("- ", mfile)
                if check["mismatches"]:
                    st.write("Mismatched files:")
                    for mm in check["mismatches"]:
                        st.write("- ", mm["path"])
            st.sidebar.error("Data integrity check failed")
            st.sidebar.info("Run secure_data.py to regenerate the manifest if needed.")
        else:
            if integrity_test_clicked:
                st.sidebar.info("Integrity test completed successfully.")

    st.title("🏆 Elden Ring — Ranking & Sorting")
    st.markdown(
        """
        <style>
        [data-testid="stMetricValue"] {
            font-size: 1.05rem !important;
            line-height: 1.1 !important;
            font-variant-numeric: tabular-nums;
        }
        [data-testid="stMetricValue"] > div {
            font-size: 1.05rem !important;
            line-height: 1.1 !important;
            font-variant-numeric: tabular-nums;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    loader = get_loader("v2_profile_loader")
    datasets = loader.get_available_datasets()

    def load_active_dataset_keys() -> list[str]:
        config_path = ROOT / "data" / "active_datasets.json"
        try:
            if config_path.exists():
                with config_path.open("r", encoding="utf-8") as f:
                    payload = json.load(f)
                configured = payload.get("active_datasets", [])
                if isinstance(configured, list):
                    cleaned = [str(item).strip() for item in configured if str(item).strip()]
                    if cleaned:
                        return cleaned
        except Exception:
            pass
        return list(DEFAULT_ACTIVE_DATASET_KEYS)

    active_dataset_keys = load_active_dataset_keys()
    active_dataset_set = set(active_dataset_keys)

    # Sidebar dataset chooser
    st.sidebar.header("Dataset")
    active_ds_keys = [key for key in active_dataset_keys if key in datasets]
    inactive_ds_keys = [key for key in datasets if key not in active_dataset_set]
    ds_keys = [*active_ds_keys, *inactive_ds_keys]
    if not ds_keys:
        ds_keys = datasets

    # Build friendly labels for datasets (e.g., 'items/ammos' -> 'Items / Ammos')
    def pretty_dataset_label(k: str) -> str:
        # replace separators with spaced equivalents and title-case words
        label = k.replace("/", " / ").replace("_", " ")
        return " ".join(part.capitalize() for part in label.split())

    dataset_label_map = {
        (
            pretty_dataset_label(k)
            if k in active_dataset_set
            else f"{pretty_dataset_label(k)} · Not implemented yet"
        ): k
        for k in ds_keys
    }
    ds_labels = list(dataset_label_map.keys())
    if ds_labels:
        ensure_state_in_options("selected_dataset_label", ds_labels, ds_labels[0])
    active_count = len(active_ds_keys)
    if inactive_ds_keys:
        st.markdown(
            f"""
            <style>
            div[role=\"listbox\"] > div:nth-child(n+{active_count + 1}) {{
                color: var(--secondary-text-color) !important;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )
    selected_dataset_label = st.sidebar.selectbox(
        "Choose dataset:", options=ds_labels, key="selected_dataset_label"
    )
    dataset = dataset_label_map.get(selected_dataset_label)

    view_mode_options = [VIEW_MODE_DETAILED, VIEW_MODE_OPTIMIZATION]
    if dataset == "armors":
        ensure_state_in_options("armor_view_mode", view_mode_options, VIEW_MODE_DETAILED)
        st.sidebar.selectbox(
            "Choose view:",
            options=view_mode_options,
            key="armor_view_mode",
        )
    elif dataset == "talismans":
        ensure_state_in_options("talisman_view_mode", view_mode_options, VIEW_MODE_DETAILED)
        st.sidebar.selectbox(
            "Choose view:",
            options=view_mode_options,
            key="talisman_view_mode",
        )
    else:
        ensure_state_in_options("generic_view_mode", view_mode_options, VIEW_MODE_DETAILED)
        st.sidebar.selectbox(
            "Choose view:",
            options=view_mode_options,
            key="generic_view_mode",
        )

    # load selected dataset
    df = None
    if dataset:
        if dataset == "armors":
            if hasattr(loader, "load_dataset_by_profile"):
                df = loader.load_dataset_by_profile(
                    dataset_key=dataset,
                    profile_name="single_piece_visual",
                )
            else:
                filepath = f"data/{dataset}.csv"
                df = DataLoader.load_file(filepath)
            if df is None:
                filepath = f"data/{dataset}.csv"
                df = DataLoader.load_file(filepath)
        else:
            filepath = f"data/{dataset}.csv"
            df = DataLoader.load_file(filepath)

    if df is None:
        st.info("No dataset loaded. Add CSV files to the `data/` folder.")
        return

    # parse armor-like stats when present
    df = parse_armor_stats(df)
    df = apply_post_parse_column_pruning(dataset, df)

    # Load armor column mapping (if present) to avoid ambiguous friendly labels
    armor_map_path = ROOT / "armor_column_map.json"
    armor_col_map = None
    if armor_map_path.exists():
        try:
            with armor_map_path.open("r", encoding="utf-8") as f:
                armor_col_map = json.load(f)
        except Exception:
            armor_col_map = None

    # Additional armor-specific UI: single-piece vs set and piece-type filter
    armor_single_piece = False
    armor_full_set = False
    talisman_single_piece = False
    talisman_full_set = False
    armor_piece_type = None
    armor_placeholder_mode = False
    type_label_map = {}
    armor_piece_labels = []
    detailed_view_active = False
    armor_detail_scope = "Single item"
    talisman_detail_scope = "Single item"
    armor_detail_item_name = None
    talisman_detail_item_name = None
    armor_detail_set_selection = {}
    talisman_detail_set_selection = []
    armor_detailed_scope_mode = DETAILED_SCOPE_CUSTOM
    talisman_detailed_scope_mode = DETAILED_SCOPE_CUSTOM
    custom_stack_view_options = [STACK_VIEW_VERTICAL, STACK_VIEW_HORIZONTAL]

    def resolve_armor_piece_types(arm_df: pd.DataFrame | None):
        raw_to_display = {
            "helm": "Helm",
            "chest armor": "Armor",
            "gauntlets": "Gauntlets",
            "leg armor": "Greaves",
        }
        fallback_map = {v: k for k, v in raw_to_display.items()}
        try:
            if arm_df is not None and "type" in arm_df.columns:
                raw_types = [str(t) for t in arm_df["type"].dropna().unique()]
                if (
                    armor_col_map
                    and "piece_type_map" in armor_col_map
                    and armor_col_map["piece_type_map"]
                ):
                    label_map = {
                        raw_to_display.get(str(k).strip().lower(), v): k
                        for k, v in armor_col_map["piece_type_map"].items()
                    }
                    labels = list(label_map.keys())
                else:
                    label_map = {
                        raw_to_display.get(str(t).strip().lower(), str(t)): t
                        for t in raw_types
                    }
                    labels = list(label_map.keys())
            else:
                label_map = fallback_map
                labels = list(label_map.keys())
        except Exception:
            label_map = fallback_map
            labels = list(label_map.keys())

        ordered = [label for label in ARMOR_PIECE_ORDER if label in labels]
        ordered.extend([label for label in labels if label not in ordered])
        return label_map, ordered

    if dataset == "armors" and str(
        st.session_state.get("armor_view_mode", VIEW_MODE_DETAILED)
    ) == VIEW_MODE_DETAILED:
        detail_scope_options = [
            DETAILED_SCOPE_SINGLE,
            DETAILED_SCOPE_FULL,
            DETAILED_SCOPE_CUSTOM,
        ]
        ensure_state_in_options(
            "armor_detailed_scope_mode",
            detail_scope_options,
            DETAILED_SCOPE_CUSTOM,
        )
        armor_detailed_scope_mode = st.sidebar.selectbox(
            "Choose scope:",
            options=detail_scope_options,
            key="armor_detailed_scope_mode",
        )
        if armor_detailed_scope_mode == DETAILED_SCOPE_CUSTOM:
            ensure_state_in_options(
                "armor_custom_stack_view",
                custom_stack_view_options,
                STACK_VIEW_VERTICAL,
            )
            st.sidebar.selectbox(
                "Choose view:",
                options=custom_stack_view_options,
                key="armor_custom_stack_view",
            )

    if dataset == "talismans" and str(
        st.session_state.get("talisman_view_mode", VIEW_MODE_DETAILED)
    ) == VIEW_MODE_DETAILED:
        detail_scope_options = [
            DETAILED_SCOPE_SINGLE,
            DETAILED_SCOPE_FULL,
            DETAILED_SCOPE_CUSTOM,
        ]
        ensure_state_in_options(
            "talisman_detailed_scope_mode",
            detail_scope_options,
            DETAILED_SCOPE_CUSTOM,
        )
        talisman_detailed_scope_mode = st.sidebar.selectbox(
            "Choose scope:",
            options=detail_scope_options,
            key="talisman_detailed_scope_mode",
        )
        if talisman_detailed_scope_mode == DETAILED_SCOPE_CUSTOM:
            ensure_state_in_options(
                "talisman_custom_stack_view",
                custom_stack_view_options,
                STACK_VIEW_VERTICAL,
            )
            st.sidebar.selectbox(
                "Choose view:",
                options=custom_stack_view_options,
                key="talisman_custom_stack_view",
            )

    if dataset == "armors":
        armor_view_mode = str(
            st.session_state.get("armor_view_mode", VIEW_MODE_DETAILED)
        )

        if armor_view_mode == VIEW_MODE_OPTIMIZATION:
            st.sidebar.subheader("Optimization view")
            mode_options = list(ARMOR_MODE_LABELS.keys())
            ensure_state_in_options("armor_mode", mode_options, ARMOR_MODE_SINGLE_PIECE)
            armor_mode = st.sidebar.radio(
                "Mode:",
                mode_options,
                key="armor_mode",
                format_func=lambda mode_key: ARMOR_MODE_LABELS.get(mode_key, str(mode_key)),
            )
            if armor_mode == ARMOR_MODE_SINGLE_PIECE:
                armor_single_piece = True
                type_label_map, armor_piece_labels = resolve_armor_piece_types(df)

                if armor_piece_labels:
                    default_piece_label = (
                        "Armor" if "Armor" in armor_piece_labels else armor_piece_labels[0]
                    )
                    ensure_state_in_options(
                        "armor_piece_type", armor_piece_labels, default_piece_label
                    )
                selected_label = st.sidebar.selectbox(
                    "Piece type:", options=armor_piece_labels, key="armor_piece_type"
                )
                armor_piece_type = type_label_map.get(selected_label, selected_label)
            elif armor_mode == ARMOR_MODE_FULL_ARMOR_SET:
                armor_full_set = True
                type_label_map, armor_piece_labels = resolve_armor_piece_types(df)
            elif armor_mode == ARMOR_MODE_COMPLETE_ARMOR_SET:
                armor_placeholder_mode = True
                st.sidebar.info(
                    "Complete armor set is planned as a meticulous full-set optimizer. "
                    "It is not implemented yet, so no results are shown in this mode."
                )
        else:
            detailed_view_active = True
            armor_detail_scope = "Complete set"
            type_label_map, armor_piece_labels = resolve_armor_piece_types(df)

            def apply_armor_detail_filter(source_df: pd.DataFrame) -> pd.DataFrame:
                return source_df

            filtered_armor_df = apply_armor_detail_filter(df)

            piece_names_by_label = {}
            for piece_label in ARMOR_PIECE_ORDER:
                raw_type = type_label_map.get(piece_label, piece_label)
                piece_names_by_label[piece_label] = sorted(
                    {
                        str(name).strip()
                        for name in filtered_armor_df.loc[
                            filtered_armor_df["type"].astype(str) == str(raw_type), "name"
                        ].dropna().tolist()
                        if str(name).strip()
                    }
                )

            armor_piece_name_tokens = {
                "helm",
                "hood",
                "hat",
                "mask",
                "crown",
                "headband",
                "armor",
                "mail",
                "robe",
                "garb",
                "gown",
                "coat",
                "vest",
                "chest",
                "cuirass",
                "gauntlets",
                "gloves",
                "manchettes",
                "bracers",
                "greaves",
                "leggings",
                "trousers",
                "boots",
                "shoes",
                "altered",
            }

            def armor_family_key(piece_name: str) -> str:
                base = re.sub(r"\([^)]*\)", "", str(piece_name or "").strip())
                tokens = re.findall(r"[A-Za-z0-9']+", base.lower())
                kept = [tok for tok in tokens if tok and tok not in armor_piece_name_tokens]
                if not kept:
                    kept = tokens
                return " ".join(kept[:3]).strip()

            family_index_by_piece = {}
            for piece_label, names in piece_names_by_label.items():
                fam_index = {}
                for piece_name in names:
                    fam_key = armor_family_key(piece_name)
                    fam_index.setdefault(fam_key, []).append(piece_name)
                family_index_by_piece[piece_label] = fam_index

            def resolve_complement_piece_name(source_name: str, target_label: str) -> str | None:
                target_names = piece_names_by_label.get(target_label, [])
                if not target_names:
                    return None
                fam_key = armor_family_key(source_name)
                fam_matches = family_index_by_piece.get(target_label, {}).get(fam_key, [])
                if fam_matches:
                    return fam_matches[0]
                source_tokens = {
                    token
                    for token in re.findall(r"[A-Za-z0-9']+", str(source_name or "").lower())
                    if token not in armor_piece_name_tokens
                }
                best_name = None
                best_score = -1
                for candidate in target_names:
                    candidate_tokens = {
                        token
                        for token in re.findall(r"[A-Za-z0-9']+", candidate.lower())
                        if token not in armor_piece_name_tokens
                    }
                    score = len(source_tokens.intersection(candidate_tokens))
                    if score > best_score:
                        best_score = score
                        best_name = candidate
                return best_name if best_name else target_names[0]

            if armor_detailed_scope_mode == DETAILED_SCOPE_SINGLE:
                single_armor_names = sorted(
                    {
                        str(name).strip()
                        for name in filtered_armor_df.get("name", pd.Series(dtype=str)).dropna().tolist()
                        if str(name).strip()
                    }
                )
                if single_armor_names:
                    ensure_state_in_options(
                        "armor_detail_single_item",
                        single_armor_names,
                        single_armor_names[0],
                    )
                    armor_detail_item_name = st.sidebar.selectbox(
                        "Choose piece:",
                        options=single_armor_names,
                        key="armor_detail_single_item",
                    )
            elif armor_detailed_scope_mode == DETAILED_SCOPE_FULL:
                st.sidebar.markdown("---")
                st.sidebar.subheader("Armor pieces (full scope)")

                pending_sync = st.session_state.pop("armor_full_scope_sync_pending", None)
                if isinstance(pending_sync, dict):
                    for piece_label, resolved_name in pending_sync.items():
                        target_names = piece_names_by_label.get(piece_label, [])
                        target_key = f"armor_full_set_{safe_stat_key(piece_label)}"
                        if resolved_name in target_names:
                            st.session_state[target_key] = resolved_name

                def on_armor_full_piece_change(changed_piece_label: str):
                    source_key = f"armor_full_set_{safe_stat_key(changed_piece_label)}"
                    source_name = st.session_state.get(source_key)
                    if not source_name:
                        return
                    sync_updates = {}
                    for piece_label in ARMOR_PIECE_ORDER:
                        if piece_label == changed_piece_label:
                            continue
                        resolved_name = resolve_complement_piece_name(source_name, piece_label)
                        if resolved_name:
                            sync_updates[piece_label] = resolved_name
                    st.session_state["armor_full_scope_sync_pending"] = sync_updates

                full_scope_current = {}
                for piece_label in ARMOR_PIECE_ORDER:
                    piece_names = piece_names_by_label.get(piece_label, [])
                    if not piece_names:
                        continue
                    key = f"armor_full_set_{safe_stat_key(piece_label)}"
                    ensure_state_in_options(key, piece_names, piece_names[0])
                    selected_piece_name = st.sidebar.selectbox(
                        f"{piece_label}:",
                        options=piece_names,
                        key=key,
                        on_change=on_armor_full_piece_change,
                        args=(piece_label,),
                    )
                    full_scope_current[piece_label] = selected_piece_name

                if full_scope_current:
                    armor_detail_set_selection = dict(full_scope_current)
            else:
                st.sidebar.markdown("---")
                st.sidebar.subheader("Armor pieces (custom scope)")
                for piece_label in ARMOR_PIECE_ORDER:
                    piece_names = piece_names_by_label.get(piece_label, [])
                    if not piece_names:
                        continue
                    key = f"armor_detail_set_{safe_stat_key(piece_label)}"
                    ensure_state_in_options(key, piece_names, piece_names[0])
                    armor_detail_set_selection[piece_label] = st.sidebar.selectbox(
                        f"{piece_label}:",
                        options=piece_names,
                        key=key,
                    )
    elif dataset == "talismans":
        talisman_view_mode = str(
            st.session_state.get("talisman_view_mode", VIEW_MODE_DETAILED)
        )

        if talisman_view_mode == VIEW_MODE_OPTIMIZATION:
            st.sidebar.subheader("Optimization view")
            talisman_mode_options = list(TALISMAN_MODE_LABELS.keys())
            ensure_state_in_options("talisman_mode", talisman_mode_options, TALISMAN_MODE_SINGLE)
            talisman_mode = st.sidebar.radio(
                "Mode:",
                talisman_mode_options,
                key="talisman_mode",
                format_func=lambda mode_key: TALISMAN_MODE_LABELS.get(mode_key, str(mode_key)),
            )
            if talisman_mode == TALISMAN_MODE_SINGLE:
                talisman_single_piece = True
            elif talisman_mode == TALISMAN_MODE_FULL_SET:
                talisman_full_set = True
        else:
            detailed_view_active = True
            talisman_detail_scope = "Complete set"
            talisman_names = sorted(
                {
                    str(name).strip()
                    for name in df.get("name", pd.Series(dtype=str)).dropna().tolist()
                    if str(name).strip()
                }
            )

            if talisman_detailed_scope_mode == DETAILED_SCOPE_SINGLE:
                if talisman_names:
                    ensure_state_in_options(
                        "talisman_detail_single_item",
                        talisman_names,
                        talisman_names[0],
                    )
                    talisman_detail_item_name = st.sidebar.selectbox(
                        "Choose talisman:",
                        options=talisman_names,
                        key="talisman_detail_single_item",
                    )
            elif talisman_detailed_scope_mode == DETAILED_SCOPE_FULL:
                placeholder_families = ["Not implemented yet"]
                ensure_state_in_options(
                    "talisman_detail_family",
                    placeholder_families,
                    placeholder_families[0],
                )
                st.sidebar.selectbox(
                    "Choose family:",
                    options=placeholder_families,
                    key="talisman_detail_family",
                )
                st.sidebar.info(
                    "Family grouping is not implemented yet. "
                    "This selector will be connected once family definitions are added."
                )
            else:
                st.sidebar.markdown("---")
                st.sidebar.subheader("All pieces (Custom scope)")
                for idx, slot_label in enumerate(TALISMAN_SLOT_LABELS, start=1):
                    if not talisman_names:
                        continue
                    key = f"talisman_detail_slot_{idx}"
                    default_name = talisman_names[min(idx - 1, len(talisman_names) - 1)]
                    ensure_state_in_options(key, talisman_names, default_name)
                    selected_name = st.sidebar.selectbox(
                        f"{slot_label}:",
                        options=talisman_names,
                        key=key,
                    )
                    talisman_detail_set_selection.append((slot_label, selected_name))

    else:
        generic_view_mode = str(
            st.session_state.get("generic_view_mode", VIEW_MODE_DETAILED)
        )
        if generic_view_mode == VIEW_MODE_DETAILED:
            detailed_view_active = True
            st.sidebar.markdown("---")
            st.sidebar.subheader("All pieces (Custom scope)")
            ensure_state_in_options(
                "generic_custom_stack_view",
                custom_stack_view_options,
                STACK_VIEW_VERTICAL,
            )
            st.sidebar.selectbox(
                "Choose view:",
                options=custom_stack_view_options,
                key="generic_custom_stack_view",
            )
            generic_names = sorted(
                {
                    str(name).strip()
                    for name in df.get("name", pd.Series(dtype=str)).dropna().tolist()
                    if str(name).strip()
                }
            )
            for idx in range(1, 5):
                if not generic_names:
                    continue
                key = f"generic_detail_slot_{idx}"
                default_name = generic_names[min(idx - 1, len(generic_names) - 1)]
                ensure_state_in_options(key, generic_names, default_name)
                st.sidebar.selectbox(
                    f"Slot {idx}:",
                    options=generic_names,
                    key=key,
                )

    # determine possible highlight stats
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    # prefer weight/poise and damage/resistance columns
    stat_options = [
        c for c in numeric_cols if c.startswith("Dmg:") or c.startswith("Res:")
    ]
    for s in ["weight", "poise"]:
        if s in numeric_cols and s not in stat_options:
            stat_options.insert(0, s)
    if dataset == "armors":
        stat_options = [s for s in stat_options if str(s).strip().lower() != "weight"]
    elif dataset == "talismans":
        stat_options = [
            s for s in numeric_cols if str(s).strip().lower() not in ["id", "dlc", "weight"]
        ]

    col1, col2 = st.columns([3, 1])
    with col1:
        st.header(f"Dataset: {dataset}")
    with col2:
        st.info(f"Total Rows: {len(df)}")

    if dataset not in ["armors", "talismans"] and not detailed_view_active:
        st.markdown("---")
        st.info(
            "This dataset view is currently a placeholder and is not implemented yet."
        )
        st.caption(
            "A dedicated per-dataset skeleton flow will be added in upcoming iterations."
        )
        qp_update(
            {
                "dataset": selected_dataset_label,
                "stats": "",
                "single_stat": "",
            }
        )
        return

    if dataset == "armors" and armor_placeholder_mode:
        st.markdown("---")
        selected_mode_key = st.session_state.get("armor_mode", ARMOR_MODE_SINGLE_PIECE)
        selected_mode_label = ARMOR_MODE_LABELS.get(selected_mode_key, "Armor mode")
        st.info(
            f"{selected_mode_label} is currently a placeholder mode. "
            "This view is intentionally empty until implementation is added."
        )
        qp_update(
            {
                "dataset": selected_dataset_label,
                "armor_mode": str(selected_mode_key),
                "piece_type": "",
                "stats": "",
                "single_stat": "",
            }
        )
        return

    # Controls (sidebar)
    # Use raw CSV column names for stat options and display labels (no friendly renaming)
    options_labels = list(stat_options)
    highlighted_stats = []
    ranking_stats = []
    primary_highlight = None
    lock_stat_order = True
    optimizer_method = DEFAULT_OPTIMIZATION_METHOD
    optimizer_weights = None
    optimizer_weight_signature = None
    optimize_with_weight = False
    use_max_weight = False
    max_weight_limit = None
    ensure_state_in_options("hist_view_mode", HIST_VIEW_OPTIONS, "Interactive (click-to-set)")
    st.session_state["hist_view_mode"] = normalize_hist_view_mode(
        st.session_state.get("hist_view_mode", "Interactive (click-to-set)")
    )
    if "hist_view_mode_widget" not in st.session_state:
        st.session_state["hist_view_mode_widget"] = st.session_state["hist_view_mode"]
    else:
        st.session_state["hist_view_mode_widget"] = normalize_hist_view_mode(
            st.session_state.get("hist_view_mode_widget", "Interactive (click-to-set)")
        )
    hist_view_mode = str(
        st.session_state.get("hist_view_mode", "Interactive (click-to-set)")
    )

    # In single-piece armor/talisman optimization mode, allow selecting many highlighted stats.
    advanced_mode = (
        (dataset == "armors" and (armor_single_piece or armor_full_set))
        or (dataset == "talismans" and (talisman_single_piece or talisman_full_set))
    )

    sort_options = ["Highest First", "Lowest First"]
    row_options = [5, 10, 25, 50, 100]
    ensure_state_in_options("sort_order", sort_options, "Highest First")
    ensure_state_in_options("rows_to_show", row_options, 5)
    sort_choice = st.session_state.get("sort_order", "Highest First")
    per_page = st.session_state.get("rows_to_show", 5)

    if not detailed_view_active:
        st.sidebar.markdown("---")
        st.sidebar.subheader("Ranking Controls")

        if advanced_mode:
            default_stat = "Dmg: Phy" if "Dmg: Phy" in options_labels else (
                options_labels[0] if options_labels else None
            )
            default_highlights = [default_stat] if default_stat else []
            ensure_state_multiselect("highlighted_stats", options_labels, default_highlights)
            highlighted_stats = st.sidebar.multiselect(
                "Highlighted stats:",
                options=options_labels,
                key="highlighted_stats",
            )

            st.sidebar.button(
                "Reset filters/stats",
                key="reset_filters",
                on_click=reset_ui_state,
                use_container_width=True,
            )

            if "lock_stat_order" not in st.session_state:
                st.session_state["lock_stat_order"] = True

            lock_stat_order = st.sidebar.checkbox(
                "Lock stat order",
                help="When on, keep the selected stat order for tie-break visuals.",
                key="lock_stat_order",
            )
            if not lock_stat_order:
                highlighted_stats = sorted(highlighted_stats)

            if dataset == "armors":
                optimize_with_weight = st.sidebar.checkbox(
                    "Optimize with weight",
                    key="optimize_with_weight",
                    help="When off, weight is excluded from optimizer scoring.",
                )

                if "weight" in numeric_cols:
                    use_max_weight = st.sidebar.checkbox(
                        "Use max weight constraint",
                        key="use_max_weight",
                    )
                    if use_max_weight:
                        st.sidebar.selectbox(
                            "Histogram view:",
                            options=HIST_VIEW_OPTIONS,
                            key="hist_view_mode_widget",
                            on_change=on_hist_view_mode_change,
                        )
                        on_hist_view_mode_change()
                        hist_view_mode = str(st.session_state["hist_view_mode"])
                        max_weight_limit = st.sidebar.number_input(
                            "Max weight:",
                            min_value=0.0,
                            step=0.1,
                            key="max_weight_limit",
                        )
        else:
            if options_labels:
                ensure_state_in_options("single_highlight_stat", options_labels, options_labels[0])
                selected_label = st.sidebar.selectbox(
                    "Highlight stat:", options=options_labels, key="single_highlight_stat"
                )
                highlighted_stats = [selected_label]

        sort_choice = st.sidebar.selectbox(
            "Sort order:", sort_options, key="sort_order"
        )
        per_page = st.sidebar.selectbox("Rows to show:", row_options, key="rows_to_show")

    if highlighted_stats:
        primary_highlight = highlighted_stats[0]
        sync_optimizer_weight_state(highlighted_stats)

    if dataset == "talismans":
        optimize_with_weight = False
        use_max_weight = False
        max_weight_limit = None

    ranking_stats = list(highlighted_stats)
    if optimize_with_weight and "weight" in numeric_cols and "weight" not in ranking_stats:
        ranking_stats = [*ranking_stats, "weight"]

    if advanced_mode and not detailed_view_active:
        method_options = list(OPTIMIZER_METHODS.keys())
        ensure_state_in_options("optimizer_method", method_options, DEFAULT_OPTIMIZATION_METHOD)
        optimizer_method = str(
            st.session_state.get("optimizer_method", DEFAULT_OPTIMIZATION_METHOD)
        )

    # perform sorting and show rows using internal rendering
    # Inline minimal renderer to avoid external dependencies
    display_df = df.copy()

    # If armor single-piece mode is active, filter by piece type
    if dataset == "armors" and armor_single_piece and armor_piece_type:
        if "type" in display_df.columns:
            display_df = display_df[display_df['type'].astype(str) == str(armor_piece_type)]

    pre_weight_df = display_df.copy()
    weight_series_all = None
    min_weight_available = None
    max_weight_available = None
    min_weight_for_three = None
    if "weight" in pre_weight_df.columns:
        weight_series_all = pd.to_numeric(pre_weight_df["weight"], errors="coerce").dropna()
        if not weight_series_all.empty:
            min_weight_available = float(weight_series_all.min())
            max_weight_available = float(weight_series_all.max())
            sorted_weights = sorted(weight_series_all.tolist())
            if len(sorted_weights) >= 3:
                min_weight_for_three = float(sorted_weights[2])

    if use_max_weight and max_weight_limit is not None and "weight" in display_df.columns:
        hist_view_mode = normalize_hist_view_mode(
            str(st.session_state.get("hist_view_mode", hist_view_mode))
        )
        st.session_state["hist_view_mode"] = hist_view_mode
        display_df = display_df[pd.to_numeric(display_df["weight"], errors="coerce") <= float(max_weight_limit)]

        candidate_count = len(display_df)
        if candidate_count == 0:
            if min_weight_available is not None:
                st.warning(
                    f"No candidates at max weight {float(max_weight_limit):.2f}. "
                    f"Lowest available weight in this category is {min_weight_available:.2f}."
                )
                if min_weight_for_three is not None:
                    st.info(
                        f"Increase Max weight to at least {min_weight_for_three:.2f} "
                        f"to get 3+ candidates."
                    )
                else:
                    st.info("Increase Max weight to at least that value to start seeing candidates.")
                if st.button("Set to minimal viable weight", key="set_min_viable_weight"):
                    target_weight = (
                        float(min_weight_for_three)
                        if min_weight_for_three is not None
                        else float(min_weight_available)
                    )
                    st.session_state["_pending_max_weight_limit"] = target_weight
                    st.rerun()
            else:
                st.warning("No candidates match the current max-weight filter.")
        elif candidate_count == 1:
            st.info("1 candidate matches this max-weight filter. Ranking is shown, but comparison is limited.")
        elif candidate_count == 2:
            st.info("2 candidates match this max-weight filter. Ranking works, but trade-off visibility is limited.")

        if weight_series_all is not None and not weight_series_all.empty:
            histogram_config = HISTOGRAM_CONFIG
            histogram_runtime_config = copy.deepcopy(histogram_config)
            histogram_runtime_config["debug"]["show_border"] = False
            classic_width_ratio_effective = 1.0
            classic_height_ratio_effective = 1.0
            interactive_width_ratio_effective = 1.0
            interactive_height_ratio_effective = 1.0
            classic_x_offset_px = 0.0
            classic_y_offset_px = 0.0
            interactive_x_offset_px = 0.0
            interactive_y_offset_px = 0.0

            layout_mode = "single"

            classic_hist_config, _classic_render_layer = resolve_auto_render_layer(
                base_config=histogram_runtime_config,
                view_kind="classic",
                layout_mode=layout_mode,
                width_ratio=classic_width_ratio_effective,
                height_ratio=classic_height_ratio_effective,
                x_offset_px=classic_x_offset_px,
                y_offset_px=classic_y_offset_px,
            )
            interactive_hist_config, interactive_render_layer = resolve_auto_render_layer(
                base_config=histogram_runtime_config,
                view_kind="interactive",
                layout_mode=layout_mode,
                width_ratio=interactive_width_ratio_effective,
                height_ratio=interactive_height_ratio_effective,
                x_offset_px=interactive_x_offset_px,
                y_offset_px=interactive_y_offset_px,
            )

            histogram_spec = build_histogram_spec(weight_series_all, histogram_config)
            if histogram_spec is None:
                st.warning(histogram_config["labels"]["invalid_data"])
            else:
                st.caption(histogram_config["labels"]["caption"])
            try:
                interactive_available = go is not None and plotly_events is not None

                def render_interactive_plot(target_ui, click_key: str):
                    def run_in_target_context(fn):
                        if hasattr(target_ui, "__enter__") and hasattr(target_ui, "__exit__"):
                            with target_ui:
                                return fn()
                        return fn()

                    try:
                        fig, interactive_spec = build_interactive_histogram_figure(
                            weight_series_all,
                            float(max_weight_limit),
                            interactive_hist_config,
                        )
                        if fig is None:
                            target_ui.info(histogram_config["labels"]["unavailable"])
                            return False

                        height_override = int(interactive_render_layer["override_height"])
                        selected_points = []
                        try:
                            selected_points = run_in_target_context(
                                lambda: plotly_events(
                                    fig,
                                    click_event=True,
                                    hover_event=False,
                                    select_event=False,
                                    override_height=height_override,
                                    key=click_key,
                                )
                            )
                        except Exception as interactive_err:
                            retry_points = None
                            if "enter" in str(interactive_err).strip("'\" ").lower():
                                try:
                                    retry_points = run_in_target_context(
                                        lambda: plotly_events(
                                            fig,
                                            click_event=True,
                                            hover_event=True,
                                            select_event=False,
                                            override_height=height_override,
                                            key=f"{click_key}_compat",
                                        )
                                    )
                                except Exception:
                                    retry_points = None

                            if retry_points is None:
                                target_ui.warning(
                                    "Interactive click capture is unavailable in this session; showing non-clickable interactive chart."
                                )
                                target_ui.plotly_chart(
                                    fig,
                                    use_container_width=True,
                                    key=f"{click_key}_fallback",
                                )
                                return False
                            selected_points = retry_points

                        new_weight = get_clicked_weight(
                            selected_points,
                            float(max_weight_limit),
                            spec=interactive_spec,
                        )
                        if new_weight is not None:
                            st.session_state["_pending_max_weight_limit"] = new_weight
                            st.rerun()
                        return True
                    except Exception:
                        target_ui.warning(
                            "Interactive histogram hit an internal error; falling back to classic view for this panel."
                        )
                        render_classic_histogram(
                            target_ui,
                            weight_series_all,
                            float(max_weight_limit),
                            classic_hist_config,
                        )
                        return False

                if hist_view_mode == "Classic":
                    render_classic_histogram(st, weight_series_all, float(max_weight_limit), classic_hist_config)
                elif hist_view_mode == "Interactive (click-to-set)":
                    if interactive_available:
                        interactive_enabled = render_interactive_plot(
                            st,
                            click_key=build_hist_click_key(
                                "single",
                                dataset,
                                armor_piece_type,
                                hist_view_mode,
                                max_weight_limit,
                            ),
                        )
                        if interactive_enabled:
                            st.caption(histogram_config["labels"]["interactive_tip"])
                    else:
                        st.info(histogram_config["labels"]["unavailable"])
                        render_classic_histogram(st, weight_series_all, float(max_weight_limit), classic_hist_config)

                if min_weight_available is not None and max_weight_available is not None:
                    st.caption(
                        f"Available weight range in this category: {min_weight_available:.2f} to {max_weight_available:.2f}."
                    )
            except Exception as err:
                st.error(f"Histogram render error: {err}")
                if min_weight_available is not None:
                    st.caption(
                        f"Lowest available weight in this category is {min_weight_available:.2f}."
                    )

    # Persist current UI state to query params for refresh/share.
    qp_update(
        {
            "dataset": selected_dataset_label,
            "armor_mode": str(st.session_state.get("armor_mode", ARMOR_MODE_SINGLE_PIECE)),
            "talisman_mode": str(st.session_state.get("talisman_mode", TALISMAN_MODE_SINGLE)),
            "piece_type": str(armor_piece_type) if armor_piece_type else "",
            "stats": "|".join(highlighted_stats),
            "lock_order": str(lock_stat_order).lower(),
            "sort": sort_choice,
            "rows": str(per_page),
            "dev": "false",
            "opt_with_weight": str(optimize_with_weight).lower(),
            "single_stat": highlighted_stats[0] if highlighted_stats else "",
            "method": optimizer_method,
            "use_max_weight": str(use_max_weight).lower(),
            "hist_view": hist_view_mode,
            "max_weight": str(max_weight_limit) if max_weight_limit is not None else "",
        }
    )

    def rank_display_df(source_df: pd.DataFrame, piece_key: str | None):
        working_df = source_df.copy()
        sampled_mode = False
        if len(highlighted_stats) >= 6 and len(working_df) > 1200:
            sampled_mode = True
            if "name" in working_df.columns:
                working_df = working_df.sort_values(by="name").head(1200)
            else:
                working_df = working_df.head(1200)
            st.info("Sampled ranking mode active for performance (showing first 1200 candidates).")

        ascending = sort_choice == "Lowest First"
        if dataset in ["armors", "talismans"] and len(ranking_stats) >= 2:
            try:
                local_optimizer_weights = None
                local_weight_signature = None
                if optimizer_method == "weighted_sum_normalized" and ranking_stats:
                    local_optimizer_weights = {}
                    for stat in ranking_stats:
                        weight_key = f"opt_weight_{safe_stat_key(stat)}"
                        local_optimizer_weights[stat] = float(
                            st.session_state.get(weight_key, 1.0)
                        )
                    local_weight_signature = tuple(
                        float(local_optimizer_weights.get(stat, 1.0))
                        for stat in ranking_stats
                    )

                cache_key = (
                    dataset,
                    piece_key,
                    tuple(ranking_stats),
                    optimizer_method,
                    local_weight_signature,
                    ascending,
                    sampled_mode,
                    use_max_weight,
                    float(max_weight_limit) if max_weight_limit is not None else None,
                    frame_signature(working_df, ["name", "type", "weight", *ranking_stats]),
                )
                weight_payload = (
                    local_optimizer_weights
                    if optimizer_method == "weighted_sum_normalized" and local_optimizer_weights
                    else {stat: 1.0 for stat in ranking_stats}
                )
                rank_cache = st.session_state.setdefault("_optimizer_cache", {})
                if cache_key in rank_cache:
                    cached_df = rank_cache[cache_key].copy()
                    if "__opt_score" in cached_df.columns and "__opt_tiebreak" in cached_df.columns:
                        working_df = cached_df
                    else:
                        working_df = optimize_single_piece(
                            working_df,
                            selected_stats=ranking_stats,
                            method=optimizer_method,
                            config={
                                "weights": weight_payload,
                                "minimize_stats": ["weight"] if optimize_with_weight else [],
                                "lock_stat_order": lock_stat_order,
                            },
                        )
                        rank_cache[cache_key] = working_df.copy()
                else:
                    working_df = optimize_single_piece(
                        working_df,
                        selected_stats=ranking_stats,
                        method=optimizer_method,
                        config={
                            "weights": weight_payload,
                            "minimize_stats": ["weight"] if optimize_with_weight else [],
                            "lock_stat_order": lock_stat_order,
                        },
                    )
                    rank_cache[cache_key] = working_df.copy()

                if "__opt_score" in working_df.columns and "__opt_tiebreak" in working_df.columns:
                    working_df = working_df.sort_values(
                        by=["__opt_score", "__opt_tiebreak"],
                        ascending=[ascending, ascending],
                    )
                elif primary_highlight and primary_highlight in working_df.columns:
                    working_df = working_df.sort_values(by=primary_highlight, ascending=ascending)
            except ValueError:
                pass
        elif primary_highlight:
            if primary_highlight in working_df.columns:
                working_df = working_df.sort_values(by=primary_highlight, ascending=ascending)

        if "__opt_score" in working_df.columns:
            opt_series = pd.to_numeric(working_df["__opt_score"], errors="coerce")
            max_opt = opt_series.max()
            min_opt = opt_series.min()
            if pd.notna(max_opt) and pd.notna(min_opt):
                if max_opt > min_opt:
                    working_df["__overall_score_100"] = (
                        (opt_series - min_opt) / (max_opt - min_opt)
                    ) * 100.0
                else:
                    working_df["__overall_score_100"] = 100.0

        return working_df, sampled_mode

    def build_ranking_caption() -> str | None:
        if dataset in ["armors", "talismans"] and len(ranking_stats) >= 2:
            return "Ranking single piece stats"
        if primary_highlight:
            return "Ranking single piece stats"
        return None

    def render_download_button_for_rows(
        display_rows: pd.DataFrame,
        section_label: str,
        key_suffix: str,
    ):
        csv_payload = display_rows.to_csv(index=False)
        safe_label = re.sub(r"[^A-Za-z0-9_\-]+", "_", section_label.strip())
        st.download_button(
            label=f"📥 Export {section_label} rows (CSV)",
            data=csv_payload,
            file_name=f"{dataset}_{safe_label}_ranked_view.csv",
            mime="text/csv",
            key=f"download_{safe_label}_{key_suffix}",
        )

    def render_card_rows(
        display_rows: pd.DataFrame,
        compact_mode: bool = False,
        full_set_mode: bool = False,
        image_mode: str = "auto",
    ):
        if full_set_mode and compact_mode:
            cards_html = []
            for _, row in display_rows.iterrows():
                bar_color = None
                if primary_highlight and primary_highlight in df.columns:
                    col_vals = df[primary_highlight].astype(float)
                    mn, mx = col_vals.min(), col_vals.max()
                    val = float(row.get(primary_highlight, 0))
                    norm = (val - mn) / (mx - mn) if mx > mn else 0
                    if norm > 0.66:
                        bar_color = "#4CAF50"
                    elif norm > 0.33:
                        bar_color = "#FFC107"
                    else:
                        bar_color = "#F44336"

                bar_html = (
                    f"<div class='full-set-bar' style='background:{bar_color};'></div>"
                    if bar_color
                    else ""
                )

                if image_mode == "phantom":
                    image_html = "<div class='full-set-img-phantom'></div>"
                elif "image" in df.columns and pd.notna(row.get("image")):
                    image_url = html.escape(str(row.get("image", "")))
                    image_html = f"<img class='full-set-img' src='{image_url}' alt='' />"
                else:
                    image_html = "<div class='full-set-img-placeholder'>[img]</div>"

                title_text = html.escape(str(row.get("name", "")))
                metrics_html = ""
                for hs in highlighted_stats:
                    if hs in row:
                        display_h = format_metric_value(row.get(hs))
                        metrics_html += (
                            "<div class='full-set-metric'>"
                            "<span class='full-set-metric-label'>"
                            "<span class='full-set-star'>&#9733;</span> "
                            f"{html.escape(str(hs))}</span>"
                            f"<span class='full-set-metric-value'>{html.escape(str(display_h))}</span>"
                            "</div>"
                        )

                cards_html.append(
                    "<div class='full-set-card'>"
                    + bar_html
                    + image_html
                    + f"<div class='full-set-title'>{title_text}</div>"
                    + metrics_html
                    + "</div>"
                )

            st.markdown(
                "<div class='full-set-card-list'>" + "".join(cards_html) + "</div>",
                unsafe_allow_html=True,
            )
            return
        for row_idx, (_, row) in enumerate(display_rows.iterrows()):
            color_style = ""
            bar_color = None
            if primary_highlight and primary_highlight in df.columns:
                col_vals = df[primary_highlight].astype(float)
                mn, mx = col_vals.min(), col_vals.max()
                val = float(row.get(primary_highlight, 0))
                norm = (val - mn) / (mx - mn) if mx > mn else 0
                if norm > 0.66:
                    color_style = "background-color: rgba(76, 175, 80, 0.18);"
                    bar_color = "#4CAF50"
                elif norm > 0.33:
                    color_style = "background-color: rgba(255, 193, 7, 0.18);"
                    bar_color = "#FFC107"
                else:
                    color_style = "background-color: rgba(244, 67, 54, 0.18);"
                    bar_color = "#F44336"

            wrapper_style = f"{color_style} padding:12px; border-radius:8px;"
            if full_set_mode and compact_mode:
                wrapper_style = "padding:12px; border-radius:8px;"
            wrapper_class = "full-set-card" if full_set_mode and compact_mode else ""
            if wrapper_class:
                st.markdown(
                    f"<div class='{wrapper_class}' style='{wrapper_style}'>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div style='{wrapper_style}'>",
                    unsafe_allow_html=True,
                )
            if compact_mode:
                if full_set_mode and bar_color:
                    st.markdown(
                        f"<div class='full-set-bar' style='background:{bar_color};'></div>",
                        unsafe_allow_html=True,
                    )
                if "image" in df.columns and pd.notna(row.get("image")):
                    try:
                        st.image(row["image"], width=140)
                    except Exception:
                        st.write("📦")
                else:
                    st.write("📦")
                if "name" in df.columns:
                    title_class = "full-set-title" if full_set_mode else ""
                    if title_class:
                        safe_name = html.escape(str(row.get("name", "")))
                        st.markdown(
                            f"<div class='{title_class}'><strong>{safe_name}</strong></div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(f"### {row['name']}")
                for hs in highlighted_stats:
                    if hs in row:
                        val_h = row.get(hs)
                        display_h = format_metric_value(val_h)
                        st.metric(f"⭐ {hs}", display_h)
            else:
                c1, c2 = st.columns([1, 3])
                with c1:
                    if "image" in df.columns and pd.notna(row.get("image")):
                        try:
                            st.image(row["image"], width=140)
                        except Exception:
                            st.write("📦")
                    else:
                        st.write("📦")
                    for hs in highlighted_stats:
                        if hs in row:
                            val_h = row.get(hs)
                            display_h = format_metric_value(val_h)
                            st.metric(f"⭐ {hs}", display_h)
                with c2:
                    title_left, title_right = st.columns([4, 1])
                    with title_left:
                        if "name" in df.columns:
                            st.markdown(f"### {row['name']}")
                    with title_right:
                        if "__overall_score_100" in row and pd.notna(row.get("__overall_score_100")):
                            overall_val = float(row.get("__overall_score_100", 0.0))
                            st.metric("Overall", f"{overall_val:.2f}")
                    if dataset == "talismans":
                        if "description" in df.columns and pd.notna(row.get("description")):
                            st.caption(row["description"])
                    else:
                        if "description" in df.columns and pd.notna(row.get("description")):
                            st.caption(row["description"])

                    stats = [c for c in numeric_cols if c not in ["id"]]
                    if dataset == "armors":
                        desired_cols = ["weight", "Dmg: Phy", "bleed", "frost", "Res: Poi."]
                        found_cols = [c for c in desired_cols if c in numeric_cols]
                        for c in numeric_cols:
                            if (
                                c.startswith("Dmg:") or c.startswith("Res:")
                            ) and c not in found_cols:
                                found_cols.append(c)

                        display_stats = [
                            s
                            for s in found_cols
                            if s in stats and s not in highlighted_stats
                        ]
                    elif dataset == "talismans":
                        desired_cols = ["weight"]
                        found_cols = [c for c in desired_cols if c in numeric_cols]
                        display_stats = [
                            s
                            for s in found_cols
                            if s in stats and s not in highlighted_stats and str(s).strip().lower() != "dlc"
                        ]
                    else:
                        display_stats = [s for s in stats if s not in highlighted_stats]

                    if display_stats:
                        cols_per_row = 4
                        for i in range(0, len(display_stats), cols_per_row):
                            parts = st.columns(cols_per_row)
                            for j, p in enumerate(parts):
                                if i + j < len(display_stats):
                                    s = display_stats[i + j]
                                    label = s
                                    val = row.get(s, 0)
                                    num_val = None
                                    try:
                                        num_val = float(val)
                                    except Exception:
                                        num_val = None

                                    if num_val is not None and num_val == 0 and s not in highlighted_stats:
                                        p.write("")
                                    else:
                                        display_val = format_metric_value(val)
                                        p.metric(label, display_val)
            st.markdown("</div>", unsafe_allow_html=True)
            gap_px = FULL_SET_ROW_GAP_PX if full_set_mode and compact_mode else 8
            st.markdown(f"<div style='height:{gap_px}px'></div>", unsafe_allow_html=True)

    def render_ranked_cards(
        source_df: pd.DataFrame,
        section_label: str,
        piece_key: str | None,
        show_weight_note: bool = True,
        compact_mode: bool = False,
        show_controls: bool = True,
        full_set_mode: bool = False,
    ):
        nonlocal optimizer_method, optimizer_weights, optimizer_weight_signature
        if source_df.empty:
            st.info(f"No candidates found for {section_label}.")
            return

        ranked_df, _ = rank_display_df(source_df, piece_key)
        display_rows = ranked_df.head(per_page)

        if show_controls:
            if advanced_mode:
                controls_left, controls_right = st.columns([1, 1], gap="medium")
                with controls_right:
                    method_options = list(OPTIMIZER_METHODS.keys())
                    ensure_state_in_options(
                        "optimizer_method",
                        method_options,
                        DEFAULT_OPTIMIZATION_METHOD,
                    )
                    st.markdown("<div style='height: 0.32rem;'></div>", unsafe_allow_html=True)
                    optimizer_method = st.selectbox(
                        "Optimization method",
                        options=method_options,
                        key="optimizer_method",
                    )

                    optimizer_weights = None
                    optimizer_weight_signature = None
                    if optimizer_method == "weighted_sum_normalized" and ranking_stats:
                        st.markdown("<div style='height: 0.25rem;'></div>", unsafe_allow_html=True)
                        optimizer_weights = {}
                        for stat in ranking_stats:
                            weight_key = f"opt_weight_{safe_stat_key(stat)}"
                            if weight_key not in st.session_state:
                                st.session_state[weight_key] = 1.0
                            optimizer_weights[stat] = st.number_input(
                                f"Weight: {stat}",
                                min_value=0.0,
                                step=0.1,
                                key=weight_key,
                            )
                        optimizer_weight_signature = tuple(
                            float(optimizer_weights.get(stat, 1.0))
                            for stat in ranking_stats
                        )

                with controls_left:
                    if show_weight_note and "weight" in ranking_stats:
                        st.info("Optimization note: `weight` is minimized; all other selected stats are maximized.")

                    caption = build_ranking_caption()
                    if caption:
                        st.markdown(caption)

                    st.markdown("<div style='height: 0.10rem;'></div>", unsafe_allow_html=True)
                    render_download_button_for_rows(display_rows, section_label, "main")
            else:
                if show_weight_note and "weight" in ranking_stats:
                    st.info("Optimization note: `weight` is minimized; all other selected stats are maximized.")
                caption = build_ranking_caption()
                if caption:
                    st.markdown(caption)
                render_download_button_for_rows(display_rows, section_label, "main")

        if show_controls and dataset in ["armors", "talismans"] and len(ranking_stats) >= 2 and len(display_rows) >= 1:
            st.markdown("---")
            with st.expander(f"Why this is #1 — {section_label}", expanded=False):
                top_1 = display_rows.iloc[0]
                st.write(f"Top item: **{top_1.get('name', 'Unknown')}**")
                if len(display_rows) >= 2:
                    top_2 = display_rows.iloc[1]
                    st.write(f"Compared against #2: **{top_2.get('name', 'Unknown')}**")
                    for stat in ranking_stats:
                        if stat in display_rows.columns:
                            v1 = pd.to_numeric(top_1.get(stat), errors="coerce")
                            v2 = pd.to_numeric(top_2.get(stat), errors="coerce")
                            if pd.notna(v1) and pd.notna(v2):
                                delta = v1 - v2
                                if str(stat).strip().lower() == "weight":
                                    delta_text = f"{delta:.2f} (lower is better)"
                                else:
                                    delta_text = f"{delta:.2f} (higher is better)"
                                st.write(f"- {stat}: {v1:.2f} vs {v2:.2f} | Δ {delta_text}")
                if "__opt_score" in display_rows.columns:
                    st.write(f"Score: {float(top_1['__opt_score']):.4f}")
                if "__opt_method" in display_rows.columns:
                    st.write(f"Method: {top_1['__opt_method']}")

        render_card_rows(display_rows, compact_mode=compact_mode, full_set_mode=full_set_mode)

        panel_piece = str(piece_key) if piece_key is not None else "all"
        panel_key = f"{dataset}_{section_label}_{panel_piece}"
        render_item_detail_inspector(display_rows, panel_key=panel_key)

    if detailed_view_active:
        st.markdown("---")
        st.subheader("Detailed view")

        def render_detail_items(items: list[tuple[str, pd.DataFrame]], stack_view: str):
            if not items:
                return
            if stack_view == STACK_VIEW_HORIZONTAL:
                columns = st.columns(len(items))
                for col, (label, rows) in zip(columns, items):
                    with col:
                        st.markdown(f"#### {label}")
                        render_card_rows(rows, compact_mode=False, full_set_mode=False)
            else:
                for label, rows in items:
                    st.markdown(f"#### {label}")
                    render_card_rows(rows, compact_mode=False, full_set_mode=False)

        if dataset == "armors":
            if armor_detailed_scope_mode == DETAILED_SCOPE_SINGLE:
                if armor_detail_item_name:
                    slot_rows = df[df["name"].astype(str) == str(armor_detail_item_name)].head(1)
                    if not slot_rows.empty:
                        st.markdown("#### Armor")
                        render_card_rows(slot_rows, compact_mode=False, full_set_mode=False)
                    else:
                        st.info("No armor item matches the current selection.")
                else:
                    st.info("No armor item available for single item view.")
            elif armor_detailed_scope_mode == DETAILED_SCOPE_FULL:
                custom_items = []
                for piece_label in ARMOR_PIECE_ORDER:
                    selected_name = armor_detail_set_selection.get(piece_label)
                    if not selected_name:
                        continue
                    slot_rows = df[df["name"].astype(str) == str(selected_name)].head(1)
                    if slot_rows.empty:
                        continue
                    custom_items.append((piece_label, slot_rows))
                if custom_items:
                    render_detail_items(
                        custom_items,
                        str(st.session_state.get("armor_custom_stack_view", STACK_VIEW_VERTICAL)),
                    )
                else:
                    st.info("No full armor set selection available.")
            else:
                custom_items = []
                for piece_label in ARMOR_PIECE_ORDER:
                    selected_name = armor_detail_set_selection.get(piece_label)
                    if not selected_name:
                        continue
                    slot_rows = df[df["name"].astype(str) == str(selected_name)].head(1)
                    if slot_rows.empty:
                        continue
                    custom_items.append((piece_label, slot_rows))
                if custom_items:
                    render_detail_items(
                        custom_items,
                        str(st.session_state.get("armor_custom_stack_view", STACK_VIEW_VERTICAL)),
                    )
                else:
                    st.info("No complete armor set selection available.")

        elif dataset == "talismans":
            if talisman_detailed_scope_mode == DETAILED_SCOPE_SINGLE:
                if talisman_detail_item_name:
                    slot_rows = df[df["name"].astype(str) == str(talisman_detail_item_name)].head(1)
                    if not slot_rows.empty:
                        st.markdown("#### Talisman")
                        render_card_rows(slot_rows, compact_mode=False, full_set_mode=False)
                    else:
                        st.info("No talisman matches the current selection.")
                else:
                    st.info("No talisman available for single item view.")
            elif talisman_detailed_scope_mode == DETAILED_SCOPE_FULL:
                st.info(
                    "Full set view by family is not implemented yet. "
                    "Choose Custom view to use current slot controls."
                )
            else:
                custom_items = []
                for slot_label, selected_name in talisman_detail_set_selection:
                    if not selected_name:
                        continue
                    slot_rows = df[df["name"].astype(str) == str(selected_name)].head(1)
                    if slot_rows.empty:
                        continue
                    custom_items.append((slot_label, slot_rows))
                if custom_items:
                    render_detail_items(
                        custom_items,
                        str(st.session_state.get("talisman_custom_stack_view", STACK_VIEW_VERTICAL)),
                    )
                else:
                    st.info("No complete talisman set selection available.")
        else:
            custom_items = []
            for idx in range(1, 5):
                key = f"generic_detail_slot_{idx}"
                selected_name = st.session_state.get(key)
                if not selected_name:
                    continue
                slot_rows = df[df["name"].astype(str) == str(selected_name)].head(1)
                if slot_rows.empty:
                    continue
                custom_items.append((f"Slot {idx}", slot_rows))
            if custom_items:
                render_detail_items(
                    custom_items,
                    str(st.session_state.get("generic_custom_stack_view", STACK_VIEW_VERTICAL)),
                )
            else:
                st.info("No complete set selection available for detailed view.")
        return

    if (dataset == "armors" and armor_full_set) or (dataset == "talismans" and talisman_full_set):
        st.markdown("---")
        st.subheader("Full armor set preview" if dataset == "armors" else "Full talisman set preview")
        st.markdown(
            f"""
            <style>
            .full-set-scope [data-testid="stVerticalBlock"] {{
                gap: 0 !important;
            }}
            .full-set-scope [data-testid="stVerticalBlock"] > div {{
                margin-bottom: 0 !important;
            }}
            .full-set-scope .element-container {{
                margin-bottom: 0 !important;
            }}
            .full-set-scope [data-testid="column"] > div {{
                gap: 0 !important;
            }}
            .full-set-col > div {{
                margin-bottom: 0 !important;
            }}
            .full-set-col .element-container {{
                margin: 0 !important;
                padding: 0 !important;
            }}
            .full-set-col .stMarkdown {{
                margin: 0 !important;
            }}
            .full-set-col .stMarkdown p {{
                margin: 0 !important;
            }}
            .full-set-header {{
                font-size: 1.4rem;
                font-weight: 600;
                margin: 0 0 6px 0;
                text-align: center;
            }}
            .full-set-card-list {{
                display: flex;
                flex-direction: column;
                gap: 0;
            }}
            .full-set-card {{
                min-height: {FULL_SET_CARD_HEIGHT_PX}px;
                height: {FULL_SET_CARD_HEIGHT_PX}px;
                overflow: hidden;
                border-bottom: 0;
                margin: 0 !important;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                gap: 6px;
            }}
            .full-set-card + .full-set-card {{
                margin-top: 0 !important;
            }}
            .full-set-title {{
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
                text-align: center;
                color: rgba(255, 255, 255, 0.95);
                font-size: 0.95rem;
                line-height: 1.15;
                min-height: 2.3em;
            }}
            .full-set-bar {{
                height: 6px;
                border-radius: 6px;
                margin: 0 0 8px 0;
            }}
            .full-set-img {{
                width: {FULL_SET_IMAGE_SIZE_PX}px;
                height: auto;
                display: block;
            }}
            .full-set-img-placeholder {{
                width: {FULL_SET_IMAGE_SIZE_PX}px;
                height: {FULL_SET_IMAGE_SIZE_PX}px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 8px;
                background: rgba(255, 255, 255, 0.06);
                color: rgba(255, 255, 255, 0.7);
                font-size: 0.85rem;
            }}
            .full-set-img-phantom {{
                width: {FULL_SET_IMAGE_SIZE_PX}px;
                height: {FULL_SET_PHANTOM_IMAGE_HEIGHT_PX}px;
                display: block;
                border-radius: 8px;
                background: transparent;
            }}
            .full-set-metric {{
                display: flex;
                justify-content: space-between;
                font-size: 0.85rem;
                margin: 2px 0 0 0;
                width: 100%;
            }}
            .full-set-metric-label {{
                color: rgba(255, 255, 255, 0.75);
            }}
            .full-set-metric-value {{
                color: rgba(255, 255, 255, 0.95);
                font-variant-numeric: tabular-nums;
            }}
            .full-set-star {{
                color: #FFC107;
            }}
            .full-set-legend {{
                display: flex;
                align-items: center;
                gap: 12px;
                margin: 6px 0 12px 0;
                font-size: 0.9rem;
                color: rgba(255, 255, 255, 0.8);
            }}
            .full-set-swatch {{
                width: 16px;
                height: 8px;
                border-radius: 6px;
                display: inline-block;
                margin-right: 6px;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )
        full_set_piece_labels = armor_piece_labels if dataset == "armors" else TALISMAN_SLOT_LABELS

        if dataset == "armors" and not full_set_piece_labels:
            st.info("No armor piece types available for full set preview.")
        else:
            if "weight" in ranking_stats:
                st.info("Optimization note: `weight` is minimized; all other selected stats are maximized.")

            caption = build_ranking_caption()
            if caption:
                st.markdown(caption)

            if primary_highlight:
                st.markdown(
                    """
                    <div class='full-set-legend'>
                        <span><span class='full-set-swatch' style='background:#4CAF50;'></span>Higher</span>
                        <span><span class='full-set-swatch' style='background:#FFC107;'></span>Mid</span>
                        <span><span class='full-set-swatch' style='background:#F44336;'></span>Lower</span>
                        <span>Color bar reflects relative value of the primary highlighted stat.</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            ranked_columns = []
            if dataset == "armors":
                piece_column_count = min(
                    len(full_set_piece_labels),
                    max(1, FULL_SET_PIECE_COLUMN_COUNT),
                )
                for label in full_set_piece_labels[:piece_column_count]:
                    raw_type = type_label_map.get(label, label)
                    piece_df = display_df
                    if "type" in piece_df.columns:
                        piece_df = piece_df[piece_df["type"].astype(str) == str(raw_type)]
                    ranked_df, _ = rank_display_df(piece_df, raw_type)
                    ranked_columns.append((label, raw_type, ranked_df.head(per_page)))
            else:
                base_ranked_df, _ = rank_display_df(display_df, None)
                for slot_idx, label in enumerate(full_set_piece_labels[:FULL_SET_PIECE_COLUMN_COUNT]):
                    slot_df = base_ranked_df.iloc[slot_idx:].reset_index(drop=True)
                    ranked_columns.append((label, label, slot_df.head(per_page)))

            def build_summary_rows(columns, max_rows: int) -> pd.DataFrame:
                summary_rows = []
                for row_index in range(max_rows):
                    summary = {"name": ""}
                    for stat in ranking_stats:
                        total = 0.0
                        has_value = False
                        for _label, _raw_type, col_df in columns:
                            if row_index >= len(col_df):
                                continue
                            val = pd.to_numeric(col_df.iloc[row_index].get(stat), errors="coerce")
                            if pd.notna(val):
                                total += float(val)
                                has_value = True
                        if has_value:
                            summary[stat] = total
                    summary_rows.append(summary)
                return pd.DataFrame(summary_rows)

            summary_rows = build_summary_rows(ranked_columns, per_page)
            ranked_columns.append(("Overall", "overall", summary_rows))

            detail_frames = []
            for _label, _raw_type, slot_rows in ranked_columns:
                if slot_rows is None or slot_rows.empty or "name" not in slot_rows.columns:
                    continue
                cleaned = slot_rows.copy()
                cleaned = cleaned[cleaned["name"].astype(str).str.strip() != ""]
                if not cleaned.empty:
                    detail_frames.append(cleaned)
            if detail_frames:
                full_set_detail_df = pd.concat(detail_frames, ignore_index=True)
                if "name" in full_set_detail_df.columns:
                    full_set_detail_df = full_set_detail_df.drop_duplicates(subset=["name"])
                render_item_detail_inspector(full_set_detail_df, panel_key=f"{dataset}_full_set")

            full_set_layout = []
            for i in range(FULL_SET_COLUMN_COUNT):
                full_set_layout.append(1)
                if i < FULL_SET_COLUMN_COUNT - 1:
                    full_set_layout.append(FULL_SET_COLUMN_GAP_RATIO)

            export_row = st.columns(full_set_layout)
            for idx, (label, _raw_type, display_rows) in enumerate(ranked_columns):
                export_map = FULL_SET_LABELS if dataset == "armors" else TALISMAN_FULL_SET_LABELS
                export_label = export_map.get(label, label)
                with export_row[idx * 2]:
                    render_download_button_for_rows(display_rows, export_label, export_label)

            columns = st.columns(full_set_layout)
            for idx, (label, raw_type, display_rows) in enumerate(ranked_columns):
                header_map = FULL_SET_LABELS if dataset == "armors" else TALISMAN_FULL_SET_LABELS
                header_label = header_map.get(label, label)
                with columns[idx * 2]:
                    st.markdown("<div class='full-set-col'>", unsafe_allow_html=True)
                    st.markdown(
                        f"<div class='full-set-header'>{html.escape(str(header_label))}</div>",
                        unsafe_allow_html=True,
                    )
                    render_card_rows(
                        display_rows,
                        compact_mode=True,
                        full_set_mode=True,
                        image_mode="phantom" if label == "Overall" else "auto",
                    )
                    st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("---")
            render_item_detail_inspector(df, panel_key=f"{dataset}_dataset")
        return

    if dataset == "armors" and armor_single_piece:
        render_ranked_cards(display_df, "Single piece", armor_piece_type)
        st.markdown("---")
        render_item_detail_inspector(df, panel_key=f"{dataset}_dataset")
        return

    if dataset == "talismans" and talisman_single_piece:
        render_ranked_cards(display_df, "Single", None)
        st.markdown("---")
        render_item_detail_inspector(df, panel_key=f"{dataset}_dataset")
        return

    render_ranked_cards(display_df, "Results", None)
    st.markdown("---")
    render_item_detail_inspector(df, panel_key=f"{dataset}_dataset")


if __name__ == "__main__":
    main()
