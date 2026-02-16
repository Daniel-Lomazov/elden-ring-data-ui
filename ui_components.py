"""Minimal UI helpers for sorting/ranking app.

This file is aggressively trimmed to only the parsing and rendering
helpers required by the simplified ranking/sorting UI.
"""

import ast
import re
from typing import Dict

import pandas as pd
import streamlit as st

# Optional plotting backends - import lazily but keep safe at import-time
try:
    import plotly.express as px
    import plotly.graph_objects as go
except Exception:
    px = None
    go = None


def parse_armor_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Parse 'damage negation' and 'resistance' literal strings into numeric columns.

    Uses ast.literal_eval for robustness against the varied formatting found
    in the dataset.
    """
    df = df.copy()

    if "damage negation" in df.columns:

        def extract_damage(v):
            try:
                if isinstance(v, str):
                    data = ast.literal_eval(v)
                    if isinstance(data, list) and data:
                        data = data[0]
                    if isinstance(data, dict):
                        return data
                return {}
            except Exception:
                return {}

        dmg = df["damage negation"].apply(extract_damage)

        # Normalize keys for robust lookup (handles variants like 'VS Str' vs 'VS Str.')
        def normalize_key(s: str) -> str:
            if not isinstance(s, str):
                return str(s)
            # replace non-alphanumeric with single space, lowercase, strip
            return re.sub(r"[^0-9a-zA-Z]+", " ", s).strip().lower()

        def alias_keys(*aliases: str) -> list[str]:
            return [normalize_key(alias) for alias in aliases if str(alias).strip()]

        def first_value_for_aliases(normalized_dict: dict, aliases: list[str]) -> float:
            if not isinstance(normalized_dict, dict):
                return 0.0
            for alias in aliases:
                if alias in normalized_dict:
                    return normalized_dict.get(alias, 0.0)
            return 0.0

        def dict_to_normalized(d: dict) -> dict:
            out = {}
            if not isinstance(d, dict):
                return out
            for k, v in d.items():
                nk = normalize_key(k)
                try:
                    out[nk] = float(v)
                except Exception:
                    try:
                        out[nk] = float(str(v).replace(",", "."))
                    except Exception:
                        out[nk] = 0.0
            return out

        dmg_norm = dmg.apply(
            lambda x: dict_to_normalized(x) if isinstance(x, dict) else {}
        )

        damage_key_aliases = {
            "Phy": alias_keys("Phy", "Physical", "Standard"),
            "VS Str.": alias_keys("VS Str.", "VS Str", "VS Strike", "Strike"),
            "VS Sla.": alias_keys("VS Sla.", "VS Sla", "VS Slash", "Slash"),
            "VS Pie.": alias_keys("VS Pie.", "VS Pie", "VS Pierce", "Pierce"),
            "Mag": alias_keys("Mag", "Magic"),
            "Fir": alias_keys("Fir", "Fire"),
            "Lit": alias_keys("Lit", "Lightning"),
            "Hol": alias_keys("Hol", "Holy"),
        }
        for key, aliases in damage_key_aliases.items():
            df[f"Dmg: {key}"] = dmg_norm.apply(
                lambda nd, alias_list=aliases: first_value_for_aliases(nd, alias_list)
            )

    if "resistance" in df.columns:

        def extract_res(v):
            try:
                if isinstance(v, str):
                    data = ast.literal_eval(v)
                    if isinstance(data, list) and data:
                        data = data[0]
                    if isinstance(data, dict):
                        return data
                return {}
            except Exception:
                return {}

        res = df["resistance"].apply(extract_res)

        # normalize resistance keys as well
        res_norm = res.apply(
            lambda x: dict_to_normalized(x) if isinstance(x, dict) else {}
        )
        resistance_key_aliases = {
            "Imm.": alias_keys("Imm.", "Imm", "Immu.", "Immu", "Immunity"),
            "Rob.": alias_keys("Rob.", "Rob", "Robu.", "Robu", "Robust", "Robustness"),
            "Foc.": alias_keys("Foc.", "Foc", "Focus"),
            "Vit.": alias_keys("Vit.", "Vit", "Vita.", "Vita", "Vitality"),
            "Poi.": alias_keys("Poi.", "Poi", "Poise"),
        }
        for key, aliases in resistance_key_aliases.items():
            df[f"Res: {key}"] = res_norm.apply(
                lambda nd, alias_list=aliases: first_value_for_aliases(nd, alias_list)
            )

        status_parent_map = {
            "status.poison": "Res: Imm.",
            "status.rot": "Res: Imm.",
            "status.bleed": "Res: Rob.",
            "status.frost": "Res: Rob.",
            "status.sleep": "Res: Foc.",
            "status.madness": "Res: Foc.",
            "status.death": "Res: Vit.",
        }
        for status_key, parent_col in status_parent_map.items():
            if parent_col in df.columns:
                df[status_key] = pd.to_numeric(df[parent_col], errors="coerce").fillna(0.0)
            else:
                df[status_key] = 0.0

    return df


def render_comparison_view(datasets: Dict[str, pd.DataFrame]):
    """Render side-by-side comparison of multiple datasets."""
    st.subheader("📊 Dataset Comparison")

    selected_datasets = st.multiselect(
        "Select datasets to compare:",
        options=list(datasets.keys()),
        default=(
            list(datasets.keys())[:2] if len(datasets) >= 2 else list(datasets.keys())
        ),
        key="comparison_datasets",
    )

    if selected_datasets:
        comparison_data = []

        for ds_name in selected_datasets:
            df = datasets[ds_name]
            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

            comparison_data.append(
                {
                    "Dataset": ds_name,
                    "Rows": len(df),
                    "Columns": len(df.columns),
                    "Numeric": len(numeric_cols),
                    "Memory (KB)": df.memory_usage(deep=True).sum() / 1024,
                }
            )

        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, use_container_width=True)

        # Memory usage chart (plot only if plotly is available)
        if px is not None:
            fig = px.bar(
                comparison_df,
                x="Dataset",
                y="Memory (KB)",
                title="Dataset Memory Usage",
                color="Rows",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Plotly not installed; skipping memory usage chart")


def render_correlation_heatmap(df: pd.DataFrame, title: str = "Correlation Matrix"):
    """Render correlation heatmap for numeric columns."""
    numeric_df = df.select_dtypes(include=["number"])

    if numeric_df.shape[1] > 1:
        corr_matrix = numeric_df.corr()

        if go is not None:
            fig = go.Figure(
                data=go.Heatmap(
                    z=corr_matrix.values,
                    x=corr_matrix.columns,
                    y=corr_matrix.columns,
                    colorscale="RdBu",
                    zmid=0,
                    zmin=-1,
                    zmax=1,
                )
            )
            fig.update_layout(title=title, height=600)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Plotly not installed; skipping correlation heatmap")
    else:
        st.info("Not enough numeric columns for correlation matrix")


def render_statistics_table(df: pd.DataFrame):
    """Render descriptive statistics table."""
    st.subheader("📈 Descriptive Statistics")

    numeric_df = df.select_dtypes(include=["number"])

    if len(numeric_df.columns) > 0:
        stats_df = numeric_df.describe().T
        stats_df = stats_df.round(4)
        st.dataframe(stats_df, use_container_width=True)
    else:
        st.info("No numeric columns available")


def render_missing_data(df: pd.DataFrame):
    """Render missing data visualization."""
    st.subheader("⚠️ Missing Data")

    missing = df.isnull().sum()
    missing_pct = (missing / len(df)) * 100

    missing_df = pd.DataFrame(
        {
            "Column": missing.index,
            "Missing Count": missing.values,
            "Missing %": missing_pct.values,
        }
    ).sort_values("Missing %", ascending=False)

    # Filter to columns with missing data
    missing_df = missing_df[missing_df["Missing Count"] > 0]

    if len(missing_df) > 0:
        col1, col2 = st.columns(2)

        with col1:
            st.dataframe(missing_df, use_container_width=True)

        with col2:
            if len(missing_df) <= 20:
                fig = px.bar(
                    missing_df,
                    x="Column",
                    y="Missing %",
                    title="Percentage of Missing Data",
                    color="Missing %",
                )
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("No missing data detected!")


def render_data_table(
    df: pd.DataFrame,
    title: str = "Data Preview",
    max_rows: int = 100,
    highlight_col: str = None,
    sort_order: str = "none",
):
    """Render data rows with images, full description, and highlighted stat sorting."""
    st.subheader(title)

    # Create unique keys based on title to avoid widget collisions across tabs
    table_key = title.lower().replace(" ", "_").replace("&", "and")

    # Display options
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        search_term = st.text_input("Search in table:", key=f"table_search_{table_key}")

    with col2:
        show_rows = st.selectbox(
            "Rows to show:", [10, 25, 50, 100, 500], key=f"table_rows_{table_key}"
        )

    with col3:
        sort_opt = st.selectbox(
            "Sort by highlighted stat:",
            ["None", "Highest First", "Lowest First"],
            key=f"sort_order_{table_key}",
        )

    # Filter first
    if search_term:
        mask = (
            df.astype(str)
            .apply(lambda x: x.str.contains(search_term, case=False))
            .any(axis=1)
        )
        display_df = df[mask].copy()
    else:
        display_df = df.copy()

    # Sort BEFORE limiting rows
    if highlight_col and highlight_col in display_df.columns and sort_opt != "None":
        ascending = sort_opt == "Lowest First"
        display_df = display_df.sort_values(by=highlight_col, ascending=ascending)

    # Apply row limit after sorting
    display_df = display_df.head(show_rows)

    # Detect columns
    has_images = "image" in display_df.columns
    has_name = "name" in display_df.columns
    has_description = "description" in display_df.columns
    has_special = "special effect" in display_df.columns

    if has_images or has_name:
        st.markdown("---")

        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        stat_cols = [
            col
            for col in numeric_cols
            if col.startswith("Dmg:") or col.startswith("Res:")
        ]
        other_cols = [
            col for col in numeric_cols if col not in stat_cols and col not in ["id"]
        ]

        # Color ramp for highlight stat
        highlight_values = None
        min_val = max_val = None
        if highlight_col and highlight_col in display_df.columns:
            highlight_values = display_df[highlight_col].astype(float)
            min_val = highlight_values.min()
            max_val = highlight_values.max()

        # One item per row to show full info
        for _, row in display_df.iterrows():
            container_color = ""
            if highlight_col and highlight_col in row and highlight_values is not None:
                value = float(row[highlight_col])
                normalized = (
                    (value - min_val) / (max_val - min_val) if max_val > min_val else 0
                )
                if normalized > 0.66:
                    container_color = (
                        "background-color: rgba(76, 175, 80, 0.18);"  # Green
                    )
                elif normalized > 0.33:
                    container_color = (
                        "background-color: rgba(255, 193, 7, 0.18);"  # Yellow
                    )
                else:
                    container_color = (
                        "background-color: rgba(244, 67, 54, 0.18);"  # Red
                    )

            st.markdown(
                f"<div style='{container_color} padding: 12px; border-radius: 10px;'>",
                unsafe_allow_html=True,
            )

            c_img, c_body = st.columns([1, 3])

            with c_img:
                if has_images and pd.notna(row.get("image")):
                    try:
                        st.image(row["image"], width=140, use_column_width=True)
                    except Exception:
                        st.write("📦")
                else:
                    st.write("📦")

                # Highlight stat badge
                if highlight_col and highlight_col in row:
                    val = row[highlight_col]
                    st.metric(
                        f"⭐ {highlight_col}",
                        f"{val:.2f}" if isinstance(val, float) else val,
                    )

            with c_body:
                if has_name:
                    st.markdown(f"### {row['name']}")

                if has_description and pd.notna(row.get("description")):
                    st.caption(row["description"])

                # Show all stats in rows of 4
                all_stat_cols = stat_cols + other_cols
                if all_stat_cols:
                    cols_per_row = 4
                    for j in range(0, len(all_stat_cols), cols_per_row):
                        stat_row = st.columns(cols_per_row)
                        for k, stat_col in enumerate(stat_row):
                            if j + k < len(all_stat_cols):
                                col_name = all_stat_cols[j + k]
                                value = row[col_name]
                                label = (
                                    f"⭐ {col_name}"
                                    if col_name == highlight_col
                                    else col_name
                                )
                                stat_col.metric(
                                    label,
                                    (
                                        f"{value:.2f}"
                                        if isinstance(value, float)
                                        else value
                                    ),
                                )

                if has_special and pd.notna(row.get("special effect")):
                    st.caption(f"✨ {row['special effect']}")

            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    else:
        # Fallback to regular table display
        st.dataframe(display_df, use_container_width=True)

    st.caption(f"Showing {len(display_df)} of {len(df)} rows")


def render_export_options(df: pd.DataFrame, dataset_name: str):
    """Render export options for dataframe."""
    st.subheader("💾 Export")

    col1, col2, col3 = st.columns(3)

    with col1:
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"{dataset_name}.csv",
            mime="text/csv",
        )

    with col2:
        json = df.to_json(orient="records", indent=2)
        st.download_button(
            label="📥 Download JSON",
            data=json,
            file_name=f"{dataset_name}.json",
            mime="application/json",
        )

    with col3:
        excel = df.to_excel(index=False) if "openpyxl" in dir() else None
        if excel:
            st.download_button(
                label="📥 Download Excel",
                data=excel,
                file_name=f"{dataset_name}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


def render_ranking_view(df: pd.DataFrame, dataset_name: str):
    """Render ranking/sorting view with top 5 highlighted and rest scrollable."""
    st.subheader("🏆 Ranking & Sorting")

    # Parse armor stats if applicable
    df_processed = parse_armor_stats(df)

    # Get numeric columns and text columns (potential ailments/effects)
    numeric_cols = df_processed.select_dtypes(include=["number"]).columns.tolist()
    text_cols = df_processed.select_dtypes(include=["object"]).columns.tolist()

    # Remove unwanted text columns
    text_cols = [col for col in text_cols if col not in ["image", "id"]]

    if not numeric_cols and not text_cols:
        st.warning("No columns available for ranking")
        return

    # Sort options
    col1, col2 = st.columns(2)

    with col1:
        sort_by_type = st.radio(
            "Sort by:",
            (
                ["📊 Stat (Numeric)", "⚠️ Afflicted Ailment (Text)"]
                if text_cols
                else ["📊 Stat (Numeric)"]
            ),
            key=f"ranking_type_{dataset_name}",
        )

    with col2:
        if sort_by_type == "📊 Stat (Numeric)":
            if numeric_cols:
                sort_column = st.selectbox(
                    "Select stat to rank by:",
                    options=numeric_cols,
                    key=f"ranking_stat_{dataset_name}",
                )
                sort_ascending = st.checkbox(
                    "Sort ascending (lowest first)", key=f"ranking_asc_{dataset_name}"
                )
            else:
                st.warning("No numeric columns available")
                return
        else:
            if text_cols:
                sort_column = st.selectbox(
                    "Select ailment/effect column:",
                    options=text_cols,
                    key=f"ranking_ailment_{dataset_name}",
                )
                sort_ascending = False
            else:
                st.warning("No text columns available")
                return

    # Sort the dataframe
    sorted_df = df_processed.sort_values(
        by=sort_column, ascending=sort_ascending, na_position="last"
    )

    # Display top 5
    st.markdown("### 🥇 Top 5")
    top_5 = sorted_df.head(5)

    # Create beautiful display for top 5
    for rank, (idx, row) in enumerate(top_5.iterrows(), 1):
        medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][rank - 1]

        with st.container():
            col_badge, col_content = st.columns([1, 10])

            with col_badge:
                st.markdown(f"<h2>{medal}</h2>", unsafe_allow_html=True)

            with col_content:
                # Get the first reasonable column to identify the item
                id_col = None
                for col in ["name", "Name", "id", "ID", "title", "Title"]:
                    if col in df.columns:
                        id_col = col
                        break

                if id_col:
                    item_name = row[id_col]
                else:
                    item_name = row.iloc[0] if len(row) > 0 else "Item"

                # Show rank value
                if sort_by_type == "📊 Stat (Numeric)":
                    value = row[sort_column]
                    st.markdown(f"**{item_name}** • {sort_column}: `{value}`")
                else:
                    value = row[sort_column]
                    st.markdown(f"**{item_name}** • {sort_column}: `{value}`")

        st.caption("---")

    # Rest (scrollable)
    st.markdown("### 📋 Rest (Scrollable)")
    rest_df = sorted_df.iloc[5:].reset_index(drop=True)

    if len(rest_df) > 0:
        # Show count
        st.info(f"Showing {len(rest_df)} more items")

        # Display with pagination controls
        rows_per_page = st.selectbox(
            "Items per page:",
            [10, 25, 50, 100, 500],
            index=1,
            key=f"ranking_pagination_{dataset_name}",
        )

        # Calculate pages
        num_pages = (len(rest_df) + rows_per_page - 1) // rows_per_page
        page = (
            st.selectbox(
                "Page:", range(1, num_pages + 1), key=f"ranking_page_{dataset_name}"
            )
            - 1
        )

        # Get data for current page
        start_idx = page * rows_per_page
        end_idx = start_idx + rows_per_page
        page_df = rest_df.iloc[start_idx:end_idx]

        # Display table
        st.dataframe(
            page_df, use_container_width=True, key=f"ranking_table_{dataset_name}"
        )

        st.caption(f"Page {page + 1} of {num_pages}")
    else:
        st.info("Only 5 or fewer items in this dataset")
