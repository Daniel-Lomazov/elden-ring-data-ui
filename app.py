"""Minimal app for ranking/sorting armors and similar datasets."""

import streamlit as st
import pandas as pd
import re
import json
import hashlib
import subprocess
import html
import copy
import time
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
from histogram_layout import (
    UNIFORM_HISTOGRAM_PARAMS,
    place_one_by_two_grid,
    place_graphical_object_in_grid_cell,
    resolve_auto_render_layer,
)
from tuning_controls import (
    render_dimension_tuning_toggle as tc_render_dimension_tuning_toggle,
    render_transport_number_input as tc_render_transport_number_input,
)

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
}

HIST_VIEW_OPTIONS = [
    "Classic",
    "Interactive (click-to-set)",
    "Side-by-side",
]


def normalize_hist_view_mode(value: str) -> str:
    normalized = str(value or "").strip()
    if normalized in HIST_VIEW_OPTIONS:
        return normalized
    return "Side-by-side"


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


@st.cache_resource
def get_loader():
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
            subprocess.run(["python", str(ROOT / "secure_data.py")], check=True)
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

    def render_dev_table(table_df: pd.DataFrame, max_rows_sample: int = 100):
        if table_df is None or table_df.empty:
            st.info("No rows to display in dev view.")
            return

        sample_df = table_df.head(max_rows_sample)
        column_widths = {}
        for col in table_df.columns:
            header_len = len(str(col))
            max_cell_len = header_len
            if col in sample_df.columns:
                try:
                    max_cell_len = max(
                        header_len,
                        sample_df[col].astype(str).map(len).max(),
                    )
                except Exception:
                    max_cell_len = header_len

            min_px = 90
            max_px = 320
            if str(col).lower() in ["name", "type"]:
                max_px = 240
            width_px = int(max(min_px, min(max_px, max_cell_len * 8 + 24)))
            column_widths[col] = width_px

        header_html = "".join(
            f"<th style='min-width:{column_widths[c]}px;width:{column_widths[c]}px;'>"
            f"{html.escape(str(c))}</th>"
            for c in table_df.columns
        )

        body_rows = []
        for _, row in table_df.iterrows():
            cells = "".join(
                f"<td style='min-width:{column_widths[c]}px;width:{column_widths[c]}px;'>"
                f"{html.escape(str(row.get(c, '')))}</td>"
                for c in table_df.columns
            )
            body_rows.append(f"<tr>{cells}</tr>")

        table_html = f"""
        <div style='overflow-x:auto; overflow-y:auto; max-height:480px; border:1px solid rgba(128,128,128,0.25); border-radius:8px;'>
          <table style='border-collapse:collapse; table-layout:fixed; width:max-content; min-width:100%;'>
            <thead style='position:sticky; top:0; background:rgba(20,20,20,0.95); z-index:1;'>
              <tr>{header_html}</tr>
            </thead>
            <tbody>
              {''.join(body_rows)}
            </tbody>
          </table>
        </div>
        <style>
          th, td {{ padding: 6px 10px; border-bottom: 1px solid rgba(128,128,128,0.2); text-align:left; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
        </style>
        """
        st.markdown(table_html, unsafe_allow_html=True)

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

    def render_dimension_tuning_toggle(
        ui,
        label: str,
        enable_key: str,
        prev_enable_key: str,
        restore_values: dict,
        help_text: str,
    ) -> bool:
        return tc_render_dimension_tuning_toggle(
            st,
            ui,
            label=label,
            enable_key=enable_key,
            prev_enable_key=prev_enable_key,
            restore_values=restore_values,
            help_text=help_text,
        )

    def render_transport_number_input(
        ui,
        control_id: str,
        label: str,
        input_key: str,
        canonical_key: str,
        default_key: str,
        min_value: float,
        max_value: float,
        help_text: str,
        step: float = 0.000001,
        display_format: str = "%.10f",
        base_step: float = 0.000005,
    ):
        return tc_render_transport_number_input(
            st,
            ui,
            control_id=control_id,
            label=label,
            input_key=input_key,
            canonical_key=canonical_key,
            default_key=default_key,
            min_value=min_value,
            max_value=max_value,
            help_text=help_text,
            step=step,
            display_format=display_format,
            base_step=base_step,
        )

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

    def on_hist_view_mode_change():
        st.session_state["hist_view_mode"] = normalize_hist_view_mode(
            st.session_state.get("hist_view_mode_widget", "Side-by-side")
        )

    def reset_ui_state():
        reset_keys = [
            "show_all_datasets",
            "selected_dataset_label",
            "armor_mode",
            "armor_piece_type",
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
            "enable_hist_tuning_classic",
            "enable_hist_tuning_interactive",
            "classic_width_ratio",
            "classic_width_ratio_input",
            "hist_default_classic_width_ratio",
            "interactive_width_ratio",
            "interactive_width_ratio_input",
            "hist_default_width_ratio",
            "hist_default_interactive_width_ratio",
            "classic_x_offset_px",
            "classic_x_offset_px_input",
            "hist_default_classic_x_offset_px",
            "classic_y_offset_px",
            "classic_y_offset_px_input",
            "hist_default_classic_y_offset_px",
            "interactive_x_offset_px",
            "interactive_x_offset_px_input",
            "hist_default_interactive_x_offset_px",
            "interactive_y_offset_px",
            "interactive_y_offset_px_input",
            "hist_default_interactive_y_offset_px",
            "interactive_height_ratio",
            "interactive_height_ratio_input",
            "hist_default_height_ratio",
            "hist_default_interactive_height_ratio",
            "classic_height_ratio",
            "classic_height_ratio_input",
            "hist_default_classic_height_ratio",
            "show_plot_debug_border",
            "_prev_enable_hist_tuning_classic",
            "_prev_enable_hist_tuning_interactive",
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
        st.session_state["show_all_datasets"] = qp_get_bool("show_all", False)
        st.session_state["selected_dataset_label"] = qp_get("dataset", "")
        st.session_state["armor_mode"] = normalize_armor_mode(
            qp_get("armor_mode", ARMOR_MODE_SINGLE_PIECE)
        )
        st.session_state["armor_piece_type"] = qp_get("piece_type", "")
        st.session_state["highlighted_stats"] = [
            s for s in qp_get("stats", "").split("|") if s
        ]
        st.session_state["lock_stat_order"] = qp_get_bool("lock_order", True)
        st.session_state["single_highlight_stat"] = qp_get("single_stat", "")
        st.session_state["sort_order"] = qp_get("sort", "Highest First")
        st.session_state["rows_to_show"] = qp_get_int("rows", 5)
        st.session_state["show_raw_dev"] = qp_get_bool("dev", False)
        st.session_state["optimizer_method"] = qp_get(
            "method", DEFAULT_OPTIMIZATION_METHOD
        )
        st.session_state["use_max_weight"] = qp_get_bool("use_max_weight", False)
        st.session_state["hist_view_mode"] = normalize_hist_view_mode(
            qp_get("hist_view", "Side-by-side")
        )
        st.session_state["hist_view_mode_widget"] = st.session_state["hist_view_mode"]
        st.session_state["enable_hist_tuning_interactive"] = qp_get_bool(
            "hist_tune_interactive", qp_get_bool("hist_width_tune", False)
        )
        st.session_state["enable_hist_tuning_classic"] = qp_get_bool(
            "hist_tune_classic", False
        )
        try:
            ratio = float(qp_get("hist_width_ratio", "1.0"))
        except Exception:
            ratio = 1.0
        st.session_state["interactive_width_ratio"] = min(4.0, max(0.3, ratio))
        try:
            classic_width_ratio = float(qp_get("hist_classic_width_ratio", "1.0"))
        except Exception:
            classic_width_ratio = 1.0
        st.session_state["classic_width_ratio"] = min(4.0, max(0.3, classic_width_ratio))
        try:
            default_ratio = float(qp_get("hist_width_default_ratio", "1.0"))
        except Exception:
            default_ratio = 1.0
        st.session_state["hist_default_width_ratio"] = min(4.0, max(0.3, default_ratio))
        st.session_state["hist_default_interactive_width_ratio"] = float(
            st.session_state["hist_default_width_ratio"]
        )
        try:
            default_classic_width_ratio = float(
                qp_get("hist_classic_width_default_ratio", "1.0")
            )
        except Exception:
            default_classic_width_ratio = 1.0
        st.session_state["hist_default_classic_width_ratio"] = min(
            4.0, max(0.3, default_classic_width_ratio)
        )
        try:
            height_ratio = float(qp_get("hist_height_ratio", "1.0"))
        except Exception:
            height_ratio = 1.0
        st.session_state["interactive_height_ratio"] = min(3.0, max(0.4, height_ratio))
        try:
            default_height_ratio = float(qp_get("hist_height_default_ratio", "1.0"))
        except Exception:
            default_height_ratio = 1.0
        st.session_state["hist_default_height_ratio"] = min(3.0, max(0.4, default_height_ratio))
        st.session_state["hist_default_interactive_height_ratio"] = float(
            st.session_state["hist_default_height_ratio"]
        )
        try:
            classic_height_ratio = float(qp_get("hist_classic_height_ratio", "1.0"))
        except Exception:
            classic_height_ratio = 1.0
        st.session_state["classic_height_ratio"] = min(3.0, max(0.4, classic_height_ratio))
        try:
            default_classic_height_ratio = float(
                qp_get("hist_classic_height_default_ratio", "1.0")
            )
        except Exception:
            default_classic_height_ratio = 1.0
        st.session_state["hist_default_classic_height_ratio"] = min(
            3.0, max(0.4, default_classic_height_ratio)
        )
        try:
            classic_x_offset = float(qp_get("hist_classic_x_offset", "0"))
        except Exception:
            classic_x_offset = 0.0
        st.session_state["classic_x_offset_px"] = min(160.0, max(-160.0, classic_x_offset))
        try:
            classic_y_offset = float(qp_get("hist_classic_y_offset", "0"))
        except Exception:
            classic_y_offset = 0.0
        st.session_state["classic_y_offset_px"] = min(120.0, max(-120.0, classic_y_offset))
        try:
            interactive_x_offset = float(qp_get("hist_interactive_x_offset", "0"))
        except Exception:
            interactive_x_offset = 0.0
        st.session_state["interactive_x_offset_px"] = min(160.0, max(-160.0, interactive_x_offset))
        try:
            interactive_y_offset = float(qp_get("hist_interactive_y_offset", "0"))
        except Exception:
            interactive_y_offset = 0.0
        st.session_state["interactive_y_offset_px"] = min(120.0, max(-120.0, interactive_y_offset))
        st.session_state["hist_default_classic_x_offset_px"] = float(
            st.session_state.get("classic_x_offset_px", 0.0)
        )
        st.session_state["hist_default_classic_y_offset_px"] = float(
            st.session_state.get("classic_y_offset_px", 0.0)
        )
        st.session_state["hist_default_interactive_x_offset_px"] = float(
            st.session_state.get("interactive_x_offset_px", 0.0)
        )
        st.session_state["hist_default_interactive_y_offset_px"] = float(
            st.session_state.get("interactive_y_offset_px", 0.0)
        )
        st.session_state["show_plot_debug_border"] = qp_get_bool("hist_debug_border", False)
        st.session_state["_prev_enable_hist_tuning_classic"] = False
        st.session_state["_prev_enable_hist_tuning_interactive"] = False
        try:
            st.session_state["max_weight_limit"] = float(qp_get("max_weight", "0.0"))
        except Exception:
            st.session_state["max_weight_limit"] = 0.0
        st.session_state["_qp_hydrated"] = True

    # Apply deferred updates before widgets are instantiated.
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
            st.sidebar.success("Data integrity OK")

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

    loader = get_loader()
    datasets = loader.get_available_datasets()

    # Sidebar dataset chooser
    st.sidebar.header("Dataset")
    show_all = st.sidebar.checkbox(
        "Show all datasets", key="show_all_datasets"
    )

    # Default behavior: show only 'armors' (if available). Enable checkbox to reveal all datasets.
    if show_all:
        ds_keys = datasets
    else:
        if "armors" in datasets:
            ds_keys = ["armors"]
        else:
            # fallback to compact list if armors not present
            ds_keys = datasets[:9] if len(datasets) > 9 else datasets

    # Build friendly labels for datasets (e.g., 'items/ammos' -> 'Items / Ammos')
    def pretty_dataset_label(k: str) -> str:
        # replace separators with spaced equivalents and title-case words
        label = k.replace("/", " / ").replace("_", " ")
        return " ".join(part.capitalize() for part in label.split())

    dataset_label_map = {pretty_dataset_label(k): k for k in ds_keys}
    ds_labels = list(dataset_label_map.keys())
    if ds_labels:
        ensure_state_in_options("selected_dataset_label", ds_labels, ds_labels[0])
    selected_dataset_label = st.sidebar.selectbox(
        "Choose dataset:", options=ds_labels, key="selected_dataset_label"
    )
    dataset = dataset_label_map.get(selected_dataset_label)

    # load selected dataset
    df = None
    if dataset:
        filepath = f"data/{dataset}.csv"
        df = DataLoader.load_file(filepath)

    if df is None:
        st.info("No dataset loaded. Add CSV files to the `data/` folder.")
        return

    # parse armor-like stats when present
    df = parse_armor_stats(df)

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
    armor_piece_type = None
    armor_placeholder_mode = False
    type_label_map = {}
    armor_piece_labels = []

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
    if dataset == "armors":
        st.sidebar.markdown("---")
        st.sidebar.subheader("Armor View")
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
                ensure_state_in_options(
                    "armor_piece_type", armor_piece_labels, armor_piece_labels[0]
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

    # determine possible highlight stats
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    # prefer weight/poise and damage/resistance columns
    stat_options = [
        c for c in numeric_cols if c.startswith("Dmg:") or c.startswith("Res:")
    ]
    for s in ["weight", "poise"]:
        if s in numeric_cols and s not in stat_options:
            stat_options.insert(0, s)

    col1, col2 = st.columns([3, 1])
    with col1:
        st.header(f"Dataset: {dataset}")
    with col2:
        st.info(f"Total Rows: {len(df)}")

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
                "show_all": str(show_all).lower(),
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
    primary_highlight = None
    lock_stat_order = True
    optimizer_method = DEFAULT_OPTIMIZATION_METHOD
    optimizer_weights = None
    optimizer_weight_signature = None
    use_max_weight = False
    max_weight_limit = None
    ensure_state_in_options("hist_view_mode", HIST_VIEW_OPTIONS, "Side-by-side")
    st.session_state["hist_view_mode"] = normalize_hist_view_mode(
        st.session_state.get("hist_view_mode", "Side-by-side")
    )
    if "hist_view_mode_widget" not in st.session_state:
        st.session_state["hist_view_mode_widget"] = st.session_state["hist_view_mode"]
    else:
        st.session_state["hist_view_mode_widget"] = normalize_hist_view_mode(
            st.session_state.get("hist_view_mode_widget", "Side-by-side")
        )
    hist_view_mode = str(st.session_state.get("hist_view_mode", "Side-by-side"))

    st.sidebar.markdown("---")
    st.sidebar.subheader("Ranking Controls")
    # In single-piece armor mode, allow selecting many highlighted stats.
    if dataset == "armors" and (armor_single_piece or armor_full_set):
        default_highlights = (
            options_labels[:2] if len(options_labels) >= 2 else options_labels[:1]
        )
        ensure_state_multiselect("highlighted_stats", options_labels, default_highlights)
        highlighted_stats = st.sidebar.multiselect(
            "Highlighted stats:",
            options=options_labels,
            key="highlighted_stats",
        )
        lock_stat_order = st.sidebar.checkbox(
            "Lock stat order",
            help="When on, keep the selected stat order for tie-break visuals.",
            key="lock_stat_order",
        )
        if not lock_stat_order:
            highlighted_stats = sorted(highlighted_stats)
    else:
        # Existing single-highlight behavior for non single-piece views.
        if options_labels:
            ensure_state_in_options("single_highlight_stat", options_labels, options_labels[0])
            selected_label = st.sidebar.selectbox(
                "Highlight stat:", options=options_labels, key="single_highlight_stat"
            )
            highlighted_stats = [selected_label]

    if highlighted_stats:
        primary_highlight = highlighted_stats[0]
        sync_optimizer_weight_state(highlighted_stats)

    # default sort: Highest First (no None option)
    sort_options = ["Highest First", "Lowest First"]
    ensure_state_in_options("sort_order", sort_options, "Highest First")
    sort_choice = st.sidebar.selectbox(
        "Sort order:", sort_options, key="sort_order"
    )
    # default rows: 5
    row_options = [5, 10, 25, 50, 100]
    ensure_state_in_options("rows_to_show", row_options, 5)
    per_page = st.sidebar.selectbox("Rows to show:", row_options, key="rows_to_show")

    show_raw_dev = st.sidebar.checkbox(
        "Show raw data table (dev view)",
        key="show_raw_dev",
    )

    enable_hist_tuning_classic = False
    enable_hist_tuning_interactive = False
    interactive_width_ratio = 1.0
    classic_width_ratio = 1.0
    default_hist_width_ratio = float(st.session_state.get("hist_default_width_ratio", 1.0))
    default_classic_width_ratio = float(
        st.session_state.get("hist_default_classic_width_ratio", 1.0)
    )
    interactive_height_ratio = 1.0
    default_hist_height_ratio = float(st.session_state.get("hist_default_height_ratio", 1.0))
    classic_height_ratio = 1.0
    default_classic_height_ratio = float(
        st.session_state.get("hist_default_classic_height_ratio", 1.0)
    )
    classic_x_offset_px = 0.0
    classic_y_offset_px = 0.0
    interactive_x_offset_px = 0.0
    interactive_y_offset_px = 0.0
    show_plot_debug_border = bool(st.session_state.get("show_plot_debug_border", False))

    st.session_state.setdefault("classic_width_ratio", 1.0)
    st.session_state.setdefault("hist_default_classic_width_ratio", 1.0)
    st.session_state.setdefault("hist_default_interactive_width_ratio", float(st.session_state.get("hist_default_width_ratio", 1.0)))
    st.session_state.setdefault("hist_default_interactive_height_ratio", float(st.session_state.get("hist_default_height_ratio", 1.0)))
    st.session_state.setdefault("classic_x_offset_px", 0.0)
    st.session_state.setdefault("classic_y_offset_px", 0.0)
    st.session_state.setdefault("interactive_x_offset_px", 0.0)
    st.session_state.setdefault("interactive_y_offset_px", 0.0)
    st.session_state.setdefault("hist_default_classic_x_offset_px", 0.0)
    st.session_state.setdefault("hist_default_classic_y_offset_px", 0.0)
    st.session_state.setdefault("hist_default_interactive_x_offset_px", 0.0)
    st.session_state.setdefault("hist_default_interactive_y_offset_px", 0.0)

    def render_histogram_tuning_controls(ui, view_kind: str):
        is_classic = view_kind == "classic"
        prefix = "classic" if is_classic else "interactive"
        ratio_limits = UNIFORM_HISTOGRAM_PARAMS.get("ratio_limits", {})
        offset_limits = UNIFORM_HISTOGRAM_PARAMS.get("offset_limits", {})
        enable_key = f"enable_hist_tuning_{prefix}"
        prev_enable_key = f"_prev_enable_hist_tuning_{prefix}"
        defaults_map = {
            f"{prefix}_width_ratio": f"hist_default_{prefix}_width_ratio",
            f"{prefix}_height_ratio": f"hist_default_{prefix}_height_ratio",
            f"{prefix}_x_offset_px": f"hist_default_{prefix}_x_offset_px",
            f"{prefix}_y_offset_px": f"hist_default_{prefix}_y_offset_px",
        }

        enabled_local = render_dimension_tuning_toggle(
            ui,
            "Enable manual dimensions tuning",
            enable_key=enable_key,
            prev_enable_key=prev_enable_key,
            restore_values=defaults_map,
            help_text="Tune width, height, and offsets for this histogram panel.",
        )

        auto_flags = []
        if enabled_local:
            ui.caption("Size")
            width_value, width_auto = render_transport_number_input(
                ui,
                control_id=f"{prefix}_width",
                label="Width ratio",
                input_key=f"{prefix}_width_ratio_input",
                canonical_key=f"{prefix}_width_ratio",
                default_key=f"hist_default_{prefix}_width_ratio",
                min_value=float(ratio_limits.get("width_min", 0.05)),
                max_value=float(ratio_limits.get("width_max", 12.0)),
                help_text="Width multiplier relative to the generated base width.",
            )
            height_value, height_auto = render_transport_number_input(
                ui,
                control_id=f"{prefix}_height",
                label="Height ratio",
                input_key=f"{prefix}_height_ratio_input",
                canonical_key=f"{prefix}_height_ratio",
                default_key=f"hist_default_{prefix}_height_ratio",
                min_value=float(ratio_limits.get("height_min", 0.1)),
                max_value=float(ratio_limits.get("height_max", 12.0)),
                help_text="Height multiplier relative to the generated base height.",
            )
            ui.caption("Offset")
            x_value, x_auto = render_transport_number_input(
                ui,
                control_id=f"{prefix}_xoffset",
                label="X offset (px)",
                input_key=f"{prefix}_x_offset_px_input",
                canonical_key=f"{prefix}_x_offset_px",
                default_key=f"hist_default_{prefix}_x_offset_px",
                min_value=float(offset_limits.get("x_min", -600)),
                max_value=float(offset_limits.get("x_max", 600)),
                help_text="Horizontal offset in pixels.",
                step=1.0,
                display_format="%.0f",
                base_step=0.5,
            )
            y_value, y_auto = render_transport_number_input(
                ui,
                control_id=f"{prefix}_yoffset",
                label="Y offset (px)",
                input_key=f"{prefix}_y_offset_px_input",
                canonical_key=f"{prefix}_y_offset_px",
                default_key=f"hist_default_{prefix}_y_offset_px",
                min_value=float(offset_limits.get("y_min", -400)),
                max_value=float(offset_limits.get("y_max", 400)),
                help_text="Vertical offset in pixels.",
                step=1.0,
                display_format="%.0f",
                base_step=0.5,
            )
            auto_flags.extend([width_auto, height_auto, x_auto, y_auto])

            if ui.button(
                "Lock current values as defaults",
                key=f"lock_hist_{prefix}_defaults",
            ):
                st.session_state[f"hist_default_{prefix}_width_ratio"] = float(width_value)
                st.session_state[f"hist_default_{prefix}_height_ratio"] = float(height_value)
                st.session_state[f"hist_default_{prefix}_x_offset_px"] = float(x_value)
                st.session_state[f"hist_default_{prefix}_y_offset_px"] = float(y_value)
                if prefix == "interactive":
                    st.session_state["hist_default_width_ratio"] = float(width_value)
                    st.session_state["hist_default_height_ratio"] = float(height_value)

        if any(auto_flags):
            time.sleep(0.05)
            st.rerun()

        ui.caption(
            f"Defaults — W: {float(st.session_state.get(f'hist_default_{prefix}_width_ratio', 1.0)):.2f}, "
            f"H: {float(st.session_state.get(f'hist_default_{prefix}_height_ratio', 1.0)):.2f}, "
            f"X: {float(st.session_state.get(f'hist_default_{prefix}_x_offset_px', 0.0)):.0f}px, "
            f"Y: {float(st.session_state.get(f'hist_default_{prefix}_y_offset_px', 0.0)):.0f}px"
        )

    if dataset == "armors" and (armor_single_piece or armor_full_set):
        st.sidebar.markdown("---")
        st.sidebar.subheader("Optimization")
        method_options = list(OPTIMIZER_METHODS.keys())
        ensure_state_in_options("optimizer_method", method_options, DEFAULT_OPTIMIZATION_METHOD)
        optimizer_method = st.sidebar.selectbox(
            "Method:", options=method_options, key="optimizer_method"
        )

        if optimizer_method == "weighted_sum_normalized" and highlighted_stats:
            st.sidebar.caption(
                "Set weights for each selected stat (higher weight = stronger preference)."
            )
            optimizer_weights = {}
            for stat in highlighted_stats:
                weight_key = f"opt_weight_{safe_stat_key(stat)}"
                if weight_key not in st.session_state:
                    st.session_state[weight_key] = 1.0
                optimizer_weights[stat] = st.sidebar.number_input(
                    f"Weight: {stat}",
                    min_value=0.0,
                    step=0.1,
                    key=weight_key,
                )
            optimizer_weight_signature = tuple(
                float(optimizer_weights.get(stat, 1.0)) for stat in highlighted_stats
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
                st.sidebar.markdown("---")
                st.sidebar.subheader("Histogram tuning (temporary): dimensions")
                st.sidebar.caption(
                    "Manual tuning controls are attached directly below each histogram panel."
                )
                show_plot_debug_border = st.sidebar.checkbox(
                    "Show plot debug border (temporary)",
                    key="show_plot_debug_border",
                    help="Draws a thin white rectangle around each rendered histogram block for visual size matching.",
                )

    st.sidebar.button(
        "Reset filters/stats",
        key="reset_filters",
        on_click=reset_ui_state,
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
            histogram_runtime_config["debug"]["show_border"] = bool(show_plot_debug_border)
            enable_hist_tuning_classic = bool(st.session_state.get("enable_hist_tuning_classic", False))
            enable_hist_tuning_interactive = bool(
                st.session_state.get("enable_hist_tuning_interactive", False)
            )
            interactive_width_ratio = float(
                st.session_state.get("interactive_width_ratio", default_hist_width_ratio)
            )
            interactive_height_ratio = float(
                st.session_state.get("interactive_height_ratio", default_hist_height_ratio)
            )
            classic_width_ratio = float(
                st.session_state.get("classic_width_ratio", default_classic_width_ratio)
            )
            classic_height_ratio = float(
                st.session_state.get("classic_height_ratio", default_classic_height_ratio)
            )
            interactive_x_offset_px = float(st.session_state.get("interactive_x_offset_px", 0.0))
            interactive_y_offset_px = float(st.session_state.get("interactive_y_offset_px", 0.0))
            classic_x_offset_px = float(st.session_state.get("classic_x_offset_px", 0.0))
            classic_y_offset_px = float(st.session_state.get("classic_y_offset_px", 0.0))
            classic_width_ratio_effective = (
                float(classic_width_ratio)
                if enable_hist_tuning_classic
                else float(st.session_state.get("hist_default_classic_width_ratio", 1.0))
            )
            classic_height_ratio_effective = (
                float(classic_height_ratio)
                if enable_hist_tuning_classic
                else float(default_classic_height_ratio)
            )
            interactive_width_ratio_effective = (
                float(interactive_width_ratio)
                if enable_hist_tuning_interactive
                else float(
                    st.session_state.get(
                        "hist_default_interactive_width_ratio", default_hist_width_ratio
                    )
                )
            )
            interactive_height_ratio_effective = (
                float(interactive_height_ratio)
                if enable_hist_tuning_interactive
                else float(
                    st.session_state.get(
                        "hist_default_interactive_height_ratio", default_hist_height_ratio
                    )
                )
            )

            layout_mode = "grid" if hist_view_mode == "Side-by-side" else "single"

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
                    render_histogram_tuning_controls(st, "classic")
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
                        render_histogram_tuning_controls(st, "interactive")
                    else:
                        st.info(histogram_config["labels"]["unavailable"])
                        render_classic_histogram(st, weight_series_all, float(max_weight_limit), classic_hist_config)
                else:
                    left_col, right_col = place_one_by_two_grid(st)

                    place_graphical_object_in_grid_cell(
                        left_col,
                        label=histogram_config["labels"]["classic_label"],
                        render_fn=lambda target_ui: render_classic_histogram(
                            target_ui,
                            weight_series_all,
                            float(max_weight_limit),
                            classic_hist_config,
                        ),
                        controls_fn=lambda target_ui: render_histogram_tuning_controls(
                            target_ui,
                            "classic",
                        ),
                    )

                    if interactive_available:
                        interactive_side_enabled = {"value": True}

                        def _render_side_interactive(target_ui):
                            interactive_side_enabled["value"] = render_interactive_plot(
                                target_ui,
                                click_key=build_hist_click_key(
                                    "side",
                                    dataset,
                                    armor_piece_type,
                                    hist_view_mode,
                                    max_weight_limit,
                                ),
                            )

                        place_graphical_object_in_grid_cell(
                            right_col,
                            label=histogram_config["labels"]["interactive_label"],
                            render_fn=_render_side_interactive,
                            controls_fn=lambda target_ui: render_histogram_tuning_controls(
                                target_ui,
                                "interactive",
                            ),
                        )
                    else:
                        place_graphical_object_in_grid_cell(
                            right_col,
                            label=histogram_config["labels"]["interactive_label"],
                            render_fn=lambda target_ui: (
                                target_ui.info(histogram_config["labels"]["unavailable"]),
                                render_classic_histogram(
                                    target_ui,
                                    weight_series_all,
                                    float(max_weight_limit),
                                    classic_hist_config,
                                ),
                            )[-1],
                        )
                    if interactive_available:
                        if interactive_side_enabled["value"]:
                            st.caption(histogram_config["labels"]["interactive_side_tip"])

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
            "show_all": str(show_all).lower(),
            "dataset": selected_dataset_label,
            "armor_mode": str(st.session_state.get("armor_mode", ARMOR_MODE_SINGLE_PIECE)),
            "piece_type": str(armor_piece_type) if armor_piece_type else "",
            "stats": "|".join(highlighted_stats),
            "lock_order": str(lock_stat_order).lower(),
            "sort": sort_choice,
            "rows": str(per_page),
            "dev": str(show_raw_dev).lower(),
            "single_stat": highlighted_stats[0] if highlighted_stats else "",
            "method": optimizer_method,
            "use_max_weight": str(use_max_weight).lower(),
            "hist_view": hist_view_mode,
            "max_weight": str(max_weight_limit) if max_weight_limit is not None else "",
            "hist_tune_interactive": str(bool(st.session_state.get("enable_hist_tuning_interactive", False))).lower(),
            "hist_tune_classic": str(bool(st.session_state.get("enable_hist_tuning_classic", False))).lower(),
            "hist_width_ratio": str(float(st.session_state.get("interactive_width_ratio", interactive_width_ratio))),
            "hist_width_default_ratio": str(float(st.session_state.get("hist_default_interactive_width_ratio", default_hist_width_ratio))),
            "hist_height_ratio": str(float(st.session_state.get("interactive_height_ratio", interactive_height_ratio))),
            "hist_height_default_ratio": str(float(st.session_state.get("hist_default_interactive_height_ratio", default_hist_height_ratio))),
            "hist_interactive_x_offset": str(float(st.session_state.get("interactive_x_offset_px", 0.0))),
            "hist_interactive_y_offset": str(float(st.session_state.get("interactive_y_offset_px", 0.0))),
            "hist_classic_width_ratio": str(float(st.session_state.get("classic_width_ratio", classic_width_ratio))),
            "hist_classic_width_default_ratio": str(float(st.session_state.get("hist_default_classic_width_ratio", 1.0))),
            "hist_classic_height_ratio": str(float(st.session_state.get("classic_height_ratio", classic_height_ratio))),
            "hist_classic_height_default_ratio": str(default_classic_height_ratio),
            "hist_classic_x_offset": str(float(st.session_state.get("classic_x_offset_px", 0.0))),
            "hist_classic_y_offset": str(float(st.session_state.get("classic_y_offset_px", 0.0))),
            "hist_debug_border": str(show_plot_debug_border).lower(),
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
        if dataset == "armors" and len(highlighted_stats) >= 2:
            try:
                cache_key = (
                    dataset,
                    piece_key,
                    tuple(highlighted_stats),
                    optimizer_method,
                    optimizer_weight_signature,
                    ascending,
                    sampled_mode,
                    use_max_weight,
                    float(max_weight_limit) if max_weight_limit is not None else None,
                    frame_signature(working_df, ["name", "type", "weight", *highlighted_stats]),
                )
                weight_payload = (
                    optimizer_weights
                    if optimizer_method == "weighted_sum_normalized" and optimizer_weights
                    else {stat: 1.0 for stat in highlighted_stats}
                )
                rank_cache = st.session_state.setdefault("_optimizer_cache", {})
                if cache_key in rank_cache:
                    cached_df = rank_cache[cache_key].copy()
                    if "__opt_score" in cached_df.columns and "__opt_tiebreak" in cached_df.columns:
                        working_df = cached_df
                    else:
                        working_df = optimize_single_piece(
                            working_df,
                            selected_stats=highlighted_stats,
                            method=optimizer_method,
                            config={
                                "weights": weight_payload,
                                "lock_stat_order": lock_stat_order,
                            },
                        )
                        rank_cache[cache_key] = working_df.copy()
                else:
                    working_df = optimize_single_piece(
                        working_df,
                        selected_stats=highlighted_stats,
                        method=optimizer_method,
                        config={
                            "weights": weight_payload,
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
        if dataset == "armors" and len(highlighted_stats) >= 2:
            caption_line = (
                f"Ranking single pieces by highlighted stats: {', '.join(highlighted_stats)} "
                f"(method: {optimizer_method})"
            )
            if optimizer_method == "weighted_sum_normalized" and optimizer_weights:
                weight_tokens = [
                    f"{stat}={float(optimizer_weights.get(stat, 1.0)):.2f}"
                    for stat in highlighted_stats
                ]
                caption_line += f" | weights: {', '.join(weight_tokens)}"
            return caption_line
        if primary_highlight:
            return f"Highlight stat: {primary_highlight}"
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

    def render_card_rows(display_rows: pd.DataFrame, compact_mode: bool = False):
        for _, row in display_rows.iterrows():
            color_style = ""
            if primary_highlight and primary_highlight in df.columns:
                col_vals = df[primary_highlight].astype(float)
                mn, mx = col_vals.min(), col_vals.max()
                val = float(row.get(primary_highlight, 0))
                norm = (val - mn) / (mx - mn) if mx > mn else 0
                if norm > 0.66:
                    color_style = "background-color: rgba(76, 175, 80, 0.18);"
                elif norm > 0.33:
                    color_style = "background-color: rgba(255, 193, 7, 0.18);"
                else:
                    color_style = "background-color: rgba(244, 67, 54, 0.18);"

            st.markdown(
                f"<div style='{color_style} padding:12px; border-radius:8px;'>",
                unsafe_allow_html=True,
            )
            if compact_mode:
                if "image" in df.columns and pd.notna(row.get("image")):
                    try:
                        st.image(row["image"], width=140)
                    except Exception:
                        st.write("📦")
                else:
                    st.write("📦")
                if "name" in df.columns:
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
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    def render_ranked_cards(
        source_df: pd.DataFrame,
        section_label: str,
        piece_key: str | None,
        show_weight_note: bool = True,
        compact_mode: bool = False,
        show_controls: bool = True,
    ):
        if source_df.empty:
            st.info(f"No candidates found for {section_label}.")
            return

        ranked_df, _ = rank_display_df(source_df, piece_key)
        display_rows = ranked_df.head(per_page)

        if show_controls:
            if show_weight_note and "weight" in highlighted_stats:
                st.info("Optimization note: `weight` is minimized; all other selected stats are maximized.")

            caption = build_ranking_caption()
            if caption:
                st.caption(caption)

            render_download_button_for_rows(display_rows, section_label, "main")

        if show_raw_dev:
            st.markdown("---")
            st.subheader(f"🧪 Raw data (dev view) — {section_label}")

            dev_view_df = display_rows.copy()
            if "__opt_score" not in dev_view_df.columns:
                dev_view_df["__opt_score"] = None
            if "__opt_tiebreak" not in dev_view_df.columns:
                dev_view_df["__opt_tiebreak"] = None
            if "__opt_method" not in dev_view_df.columns:
                dev_view_df["__opt_method"] = None
            if "__opt_length" not in dev_view_df.columns:
                dev_view_df["__opt_length"] = len(highlighted_stats)

            dev_columns = list(dev_view_df.columns)
            contribution_columns = [
                f"Norm: {s}"
                for s in highlighted_stats
                if f"Norm: {s}" in dev_columns
            ]
            fixed_dev_columns = [
                c
                for c in [
                    "name",
                    "type",
                    "__opt_score",
                    "__opt_method",
                    *highlighted_stats,
                    *contribution_columns,
                ]
                if c in dev_columns
            ]

            if fixed_dev_columns:
                render_dev_table(dev_view_df[fixed_dev_columns])
            else:
                st.info("No dev-view columns available for current data.")

        if show_controls and dataset == "armors" and len(highlighted_stats) >= 2 and len(display_rows) >= 1:
            st.markdown("---")
            with st.expander(f"Why this is #1 — {section_label}", expanded=False):
                top_1 = display_rows.iloc[0]
                st.write(f"Top item: **{top_1.get('name', 'Unknown')}**")
                if len(display_rows) >= 2:
                    top_2 = display_rows.iloc[1]
                    st.write(f"Compared against #2: **{top_2.get('name', 'Unknown')}**")
                    for stat in highlighted_stats:
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

        render_card_rows(display_rows, compact_mode=compact_mode)

    if dataset == "armors" and armor_full_set:
        st.markdown("---")
        st.subheader("Full armor set preview")
        if not armor_piece_labels:
            st.info("No armor piece types available for full set preview.")
        else:
            if "weight" in highlighted_stats:
                st.info("Optimization note: `weight` is minimized; all other selected stats are maximized.")

            caption = build_ranking_caption()
            if caption:
                st.caption(caption)

            ranked_columns = []
            for label in armor_piece_labels[:4]:
                raw_type = type_label_map.get(label, label)
                piece_df = display_df
                if "type" in piece_df.columns:
                    piece_df = piece_df[piece_df["type"].astype(str) == str(raw_type)]
                ranked_df, _ = rank_display_df(piece_df, raw_type)
                ranked_columns.append((label, raw_type, ranked_df.head(per_page)))

            export_row = st.columns(4)
            for idx, (label, _raw_type, display_rows) in enumerate(ranked_columns):
                export_label = FULL_SET_LABELS.get(label, label)
                with export_row[idx % 4]:
                    render_download_button_for_rows(display_rows, export_label, export_label)

            columns = st.columns(4)
            for idx, (label, raw_type, display_rows) in enumerate(ranked_columns):
                header_label = FULL_SET_LABELS.get(label, label)
                with columns[idx % 4]:
                    st.subheader(header_label)
                    render_card_rows(display_rows, compact_mode=True)
        return

    if dataset == "armors" and armor_single_piece:
        render_ranked_cards(display_df, "Single piece", armor_piece_type)
        return

    render_ranked_cards(display_df, "Results", None)


if __name__ == "__main__":
    main()
