"""Minimal app for ranking/sorting armors and similar datasets."""

import streamlit as st
import pandas as pd
import re
import json
import hashlib
import subprocess
from pathlib import Path
from data_loader import DataLoader
from ui_components import parse_armor_stats

st.set_page_config(page_title="Elden Ring - Ranking UI", page_icon="🏆", layout="wide")


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

    loader = get_loader()
    datasets = loader.get_available_datasets()

    # Sidebar dataset chooser
    st.sidebar.header("Dataset")
    show_all = st.sidebar.checkbox("Show all datasets", value=False)

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
    selected_dataset_label = st.sidebar.selectbox(
        "Choose dataset:", options=ds_labels, index=0
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
    armor_piece_type = None
    if dataset == "armors":
        st.sidebar.markdown("---")
        st.sidebar.subheader("Armor View")
        # default to Single piece mode
        armor_mode = st.sidebar.radio("Mode:", ["Full list", "Single piece"], index=1)
        if armor_mode == "Single piece":
            armor_single_piece = True
            # try to get piece types from the armors dataframe
            try:
                arm_df = df
                if "type" in arm_df.columns:
                    raw_types = [str(t) for t in arm_df["type"].dropna().unique()]
                    # prefer piece-type mapping from armor_column_map.json if available
                    if (
                        armor_col_map
                        and "piece_type_map" in armor_col_map
                        and armor_col_map["piece_type_map"]
                    ):
                        # armor_col_map['piece_type_map'] is raw -> display
                        pt_map = armor_col_map["piece_type_map"]
                        # build display -> raw mapping for selectbox
                        type_label_map = {v: k for k, v in pt_map.items()}
                        types = sorted(type_label_map.keys())
                    else:
                        # create spaced Title Case display labels but keep mapping to original values
                        def to_camel(s: str) -> str:
                            parts = re.split(r"[^0-9a-zA-Z]+", s.strip())
                            # join with spaces for better readability (e.g., 'Chest Armor')
                            return " ".join(p.capitalize() for p in parts if p)

                        type_label_map = {to_camel(t): t for t in raw_types}
                        types = sorted(type_label_map.keys())
                else:
                    type_label_map = {
                        "Head": "Head",
                        "Chest": "Chest",
                        "Arms": "Arms",
                        "Legs": "Legs",
                    }
                    types = ["Head", "Chest", "Arms", "Legs"]
            except Exception:
                type_label_map = {
                    "Head": "Head",
                    "Chest": "Chest",
                    "Arms": "Arms",
                    "Legs": "Legs",
                }
                types = ["Head", "Chest", "Arms", "Legs"]

            # show CamelCase labels in the selectbox and map back to original values
            selected_label = st.sidebar.selectbox("Piece type:", options=types, index=0)
            armor_piece_type = type_label_map.get(selected_label, selected_label)

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

    # Controls
    control_cols = st.columns([2, 1, 1])
    # Use raw CSV column names for stat options and display labels (no friendly renaming)
    options_labels = list(stat_options)

    with control_cols[0]:
        # default highlight: first relevant stat (if any) — present friendly labels
        if options_labels:
            selected_label = st.selectbox(
                "Highlight stat:", options=options_labels, index=0
            )
            # selected_label is the raw column name
            highlight = selected_label
        else:
            highlight = None
    with control_cols[1]:
        # default sort: Highest First (no None option)
        sort_choice = st.selectbox(
            "Sort order:", ["Highest First", "Lowest First"], index=0
        )
    with control_cols[2]:
        # default rows: 5
        per_page = st.selectbox("Rows to show:", [5, 10, 25, 50, 100], index=0)

    # Control: when checked, show only zero-value stats; when unchecked, hide zero-value stats
    show_only_zero = st.checkbox("Show only zero-value stats", value=False)

    # perform sorting and show rows using internal rendering
    # Inline minimal renderer to avoid external dependencies
    display_df = df.copy()

    # If armor single-piece mode is active, filter by piece type
    if dataset == "armors" and armor_single_piece and armor_piece_type:
        if "type" in display_df.columns:
            display_df = display_df[display_df['type'].astype(str) == str(armor_piece_type)]

    # If 'Show only zero-value stats' is checked and a highlight stat is selected,
    # filter rows to only those where the highlighted stat equals zero.
    if highlight and show_only_zero:
        try:
            display_df = display_df[display_df[highlight].astype(float) == 0]
        except Exception:
            display_df = display_df[display_df[highlight] == 0]
    # (removed: optional filter to only rows where highlighted stat > 0)

    # Apply sorting (Highest/Lowest). Default is Highest First.
    if highlight:
        ascending = sort_choice == "Lowest First"
        if highlight in display_df.columns:
            display_df = display_df.sort_values(by=highlight, ascending=ascending)

    display_df = display_df.head(per_page)

    # Render rows: image, name, description, highlighted stat, stats
    for _, row in display_df.iterrows():
        # compute color
        color_style = ""
        if highlight and highlight in df.columns:
            # compute normalized using whole dataset for consistent coloring
            col_vals = df[highlight].astype(float)
            mn, mx = col_vals.min(), col_vals.max()
            val = float(row.get(highlight, 0))
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
        c1, c2 = st.columns([1, 3])
        with c1:
            if "image" in df.columns and pd.notna(row.get("image")):
                try:
                    st.image(row["image"], width=140)
                except Exception:
                    st.write("📦")
            else:
                st.write("📦")
            if highlight and highlight in row:
                # display the exact CSV column name and use the exact data value from the row
                val_h = row.get(highlight)
                try:
                    display_h = f"{float(val_h):.2f}"
                except Exception:
                    display_h = str(val_h)
                st.metric(f"⭐ {highlight}", display_h)
        with c2:
            if "name" in df.columns:
                st.markdown(f"### {row['name']}")
            if "description" in df.columns and pd.notna(row.get("description")):
                st.caption(row["description"])

            stats = [c for c in numeric_cols if c not in ["id"]]
            # For armors, restrict and order visible stats to an explicit list of CSV column names
            if dataset == "armors":
                # Use only exact CSV column names here (no friendly renaming or fuzzy matching)
                desired_cols = ["weight", "Dmg: Phy", "bleed", "frost", "Res: Poi."]
                # Include desired columns only if they exist exactly in the dataframe
                found_cols = [c for c in desired_cols if c in numeric_cols]

                # fallback: include any remaining Dmg:/Res: columns not already included
                for c in numeric_cols:
                    if (
                        c.startswith("Dmg:") or c.startswith("Res:")
                    ) and c not in found_cols:
                        found_cols.append(c)

                display_stats = [
                    s
                    for s in found_cols
                    if s in stats and not (highlight and s == highlight)
                ]
            else:
                display_stats = [s for s in stats if not (highlight and s == highlight)]

            if display_stats:
                cols_per_row = 4
                for i in range(0, len(display_stats), cols_per_row):
                    parts = st.columns(cols_per_row)
                    for j, p in enumerate(parts):
                        if i + j < len(display_stats):
                            s = display_stats[i + j]
                            # Display exact CSV column name as label
                            label = s
                            val = row.get(s, 0)
                            # determine numeric value (if possible)
                            num_val = None
                            try:
                                num_val = float(val)
                            except Exception:
                                num_val = None

                            # Default behavior: hide zero-value stats (unless it's the highlighted stat)
                            if num_val is not None and num_val == 0 and s != highlight:
                                p.write('')
                            else:
                                display_val = f"{num_val:.2f}" if num_val is not None else val
                                p.metric(label, display_val)
            # Debug expanders removed for clean UI
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
