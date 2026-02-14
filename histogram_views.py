import pandas as pd
import numpy as np

try:
    import plotly.graph_objects as go
except Exception:
    go = None


HISTOGRAM_CONFIG = {
    "labels": {
        "x": "Weight",
        "y": "Pieces",
        "legend": "Region",
        "count_tooltip": "Count",
        "caption": "Weight distribution for current category (before max-weight cutoff):",
        "interactive_tip": "Tip: click a bar to set Max weight to that value.",
        "interactive_side_tip": "Tip: click a bar in the interactive panel to set Max weight.",
        "classic_label": "Classic",
        "interactive_label": "Interactive (click-to-set)",
        "unavailable": "Interactive histogram unavailable; showing classic view.",
        "invalid_data": "Unable to render histogram for current weight data.",
    },
    "regions": {
        "within": "Within max weight",
        "above": "Above max weight",
    },
    "colors": {
        "within": "#4CAF50",
        "above": "#9E9E9E",
        "cutoff": "#FF9800",
        "grid": "rgba(128,128,128,0.25)",
        "foreground": "#FFFFFF",
    },
    "fonts": {
        "regular": "Arial, sans-serif",
        "axis_label_size": 10,
        "axis_title_size": 11,
    },
    "compute": {
        "bin_count": 20,
        "min_y_upper": 10,
    },
    "layout": {
        "height": 236,
        "embed_height": 236,
        "margin": {"l": 0, "r": 0, "t": 8, "b": 56},
        "bargap": 0.22,
        "background": "rgba(0,0,0,0)",
    },
    "x_axis": {
        "tick0": 0,
        "dtick": 2,
        "tickangle": 0,
        "tickwidth": 1.5,
        "title_standoff": 14,
    },
    "y_axis": {
        "tickwidth": 1.5,
        "title_standoff": 12,
    },
    "cutoff": {
        "line_width": 2,
        "line_dash": "dash",
        "stroke_dash": [6, 3],
    },
    "debug": {
        "show_border": False,
        "border_color": "#FFFFFF",
        "border_width": 1,
    },
}


def build_histogram_spec(weight_series: pd.Series, config: dict = HISTOGRAM_CONFIG):
    numeric_weights = pd.to_numeric(weight_series, errors="coerce").dropna()
    if numeric_weights.empty:
        return None

    weight_min = float(numeric_weights.min())
    weight_max = float(numeric_weights.max())
    if weight_max <= weight_min:
        weight_max = weight_min + 1e-6

    bin_count = int(config["compute"]["bin_count"])
    bin_size = (weight_max - weight_min) / bin_count

    all_counts, _ = np.histogram(
        numeric_weights,
        bins=bin_count,
        range=(weight_min, weight_max),
    )
    max_bin_count = int(all_counts.max()) if all_counts.size else 0
    y_tick_step = 10 if max_bin_count >= 50 else (5 if max_bin_count >= 25 else 2)
    y_axis_upper = max(
        int(config["compute"]["min_y_upper"]),
        int(np.ceil(max_bin_count / y_tick_step) * y_tick_step) if max_bin_count > 0 else int(config["compute"]["min_y_upper"]),
    )
    x_axis_min = 0.0
    x_axis_max = max(2.0, float(np.ceil(weight_max / 2.0) * 2.0))
    x_ticks = [float(v) for v in np.arange(x_axis_min, x_axis_max + 0.1, 2.0)]

    return {
        "weights": numeric_weights,
        "weight_min": weight_min,
        "weight_max": weight_max,
        "x_axis_min": x_axis_min,
        "x_axis_max": x_axis_max,
        "x_ticks": x_ticks,
        "bin_count": bin_count,
        "bin_size": bin_size,
        "y_axis_upper": y_axis_upper,
        "y_tick_step": y_tick_step,
    }


def render_classic_histogram(target, weight_series: pd.Series, max_weight_limit: float, config: dict = HISTOGRAM_CONFIG):
    import altair as alt

    spec = build_histogram_spec(weight_series, config)
    if spec is None:
        return False

    hist_df = pd.DataFrame({"weight": spec["weights"]})
    hist_df["region"] = hist_df["weight"].apply(
        lambda w: config["regions"]["within"] if w <= float(max_weight_limit) else config["regions"]["above"]
    )

    x_offset_px = int(config.get("layout", {}).get("x_offset_px", 0) or 0)
    y_offset_px = int(config.get("layout", {}).get("y_offset_px", 0) or 0)
    chart_width = config.get("layout", {}).get("width")

    chart_height = config["layout"].get("embed_height", config["layout"]["height"])
    chart_props = {
        "height": chart_height,
    }
    if chart_width is not None:
        chart_props["width"] = int(chart_width)

    chart = (
        alt.Chart(hist_df)
        .mark_bar()
        .encode(
            x=alt.X(
                "weight:Q",
                bin=alt.Bin(
                    step=spec["bin_size"],
                    extent=[spec["weight_min"], spec["weight_max"]],
                ),
                scale=alt.Scale(domain=[spec["x_axis_min"], spec["x_axis_max"]]),
                axis=alt.Axis(values=spec["x_ticks"]),
                title=config["labels"]["x"],
            ),
            y=alt.Y("count():Q", title=config["labels"]["y"]),
            color=alt.Color(
                "region:N",
                scale=alt.Scale(
                    domain=[
                        config["regions"]["within"],
                        config["regions"]["above"],
                    ],
                    range=[
                        config["colors"]["within"],
                        config["colors"]["above"],
                    ],
                ),
                legend=alt.Legend(title=config["labels"]["legend"]),
            ),
            tooltip=[
                "region:N",
                alt.Tooltip("count():Q", title=config["labels"]["count_tooltip"]),
            ],
        )
        .properties(**chart_props)
    )

    cutoff_rule = alt.Chart(
        pd.DataFrame({"cutoff": [float(max_weight_limit)]})
    ).mark_rule(
        color=config["colors"]["cutoff"],
        strokeDash=config["cutoff"]["stroke_dash"],
    ).encode(x="cutoff:Q")

    classic_chart = (chart + cutoff_rule).configure_axis(
        labelFont=config["fonts"]["regular"],
        titleFont=config["fonts"]["regular"],
        labelFontSize=config["fonts"]["axis_label_size"],
        titleFontSize=config["fonts"]["axis_title_size"],
        tickWidth=config["x_axis"]["tickwidth"],
    ).configure_legend(
        labelFont=config["fonts"]["regular"],
        titleFont=config["fonts"]["regular"],
        labelFontSize=config["fonts"]["axis_label_size"],
        titleFontSize=config["fonts"]["axis_title_size"],
    )
    if config.get("debug", {}).get("show_border", False):
        classic_chart = classic_chart.configure_view(
            stroke=config["debug"].get("border_color", "#FFFFFF"),
            strokeWidth=config["debug"].get("border_width", 1),
        )

    if x_offset_px or y_offset_px:
        classic_chart = classic_chart.properties(
            title={
                "text": "",
                "anchor": "start",
                "dx": x_offset_px,
                "dy": y_offset_px,
            }
        )

    target.altair_chart(classic_chart, use_container_width=(chart_width is None))
    return True


def build_interactive_histogram_figure(
    weight_series: pd.Series,
    max_weight_limit: float,
    config: dict = HISTOGRAM_CONFIG,
):
    if go is None:
        return None, None

    spec = build_histogram_spec(weight_series, config)
    if spec is None:
        return None, None

    within = spec["weights"][spec["weights"] <= float(max_weight_limit)]
    above = spec["weights"][spec["weights"] > float(max_weight_limit)]

    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=within,
            name=config["regions"]["within"],
            marker_color=config["colors"]["within"],
            nbinsx=spec["bin_count"],
            xbins=dict(
                start=spec["weight_min"],
                end=spec["weight_max"],
                size=spec["bin_size"],
            ),
            opacity=0.95,
        )
    )
    fig.add_trace(
        go.Histogram(
            x=above,
            name=config["regions"]["above"],
            marker_color=config["colors"]["above"],
            nbinsx=spec["bin_count"],
            xbins=dict(
                start=spec["weight_min"],
                end=spec["weight_max"],
                size=spec["bin_size"],
            ),
            opacity=0.95,
        )
    )
    x_offset_px = int(config.get("layout", {}).get("x_offset_px", 0) or 0)
    y_offset_px = int(config.get("layout", {}).get("y_offset_px", 0) or 0)
    x_offset_px = max(-24, min(24, x_offset_px))
    y_offset_px = max(-24, min(24, y_offset_px))
    base_margin = config["layout"]["margin"]
    adjusted_margin = {
        "l": int(max(56, base_margin.get("l", 0) + max(0, x_offset_px))),
        "r": int(max(20, base_margin.get("r", 0) + max(0, -x_offset_px))),
        "t": int(max(14, base_margin.get("t", 0) + max(0, y_offset_px))),
        "b": int(max(72, base_margin.get("b", 0) + max(0, -y_offset_px))),
    }

    layout_kwargs = {
        "barmode": "stack",
        "height": config["layout"].get("embed_height", config["layout"]["height"]),
        "autosize": config["layout"].get("autosize", True),
        "margin": adjusted_margin,
        "xaxis_title": config["labels"]["x"],
        "yaxis_title": config["labels"]["y"],
        "legend_title": config["labels"]["legend"],
        "bargap": config["layout"]["bargap"],
        "plot_bgcolor": config["layout"]["background"],
        "paper_bgcolor": config["layout"]["background"],
        "font": dict(
            color=config["colors"]["foreground"],
            family=config["fonts"]["regular"],
            size=config["fonts"]["axis_label_size"],
        ),
    }
    if config["layout"].get("width") is not None:
        layout_kwargs["width"] = int(config["layout"]["width"])

    fig.update_layout(
        **layout_kwargs,
    )
    x_axis_kwargs = {
        "showgrid": False,
        "zeroline": False,
        "ticks": "outside",
        "tickwidth": config["x_axis"]["tickwidth"],
        "tickangle": config["x_axis"]["tickangle"],
        "range": [spec["x_axis_min"], spec["x_axis_max"]],
        "autorange": False,
        "tickfont": dict(
            color=config["colors"]["foreground"],
            family=config["fonts"]["regular"],
            size=config["fonts"]["axis_label_size"],
        ),
        "title_font": dict(
            color=config["colors"]["foreground"],
            family=config["fonts"]["regular"],
            size=config["fonts"]["axis_title_size"],
        ),
        "title_standoff": config["x_axis"]["title_standoff"],
        "automargin": True,
    }
    if config["x_axis"].get("tick0") is not None:
        x_axis_kwargs["tick0"] = config["x_axis"]["tick0"]
    if config["x_axis"].get("dtick") is not None:
        x_axis_kwargs["dtick"] = config["x_axis"]["dtick"]
    fig.update_xaxes(**x_axis_kwargs)
    fig.update_yaxes(
        showgrid=True,
        gridcolor=config["colors"]["grid"],
        zeroline=False,
        ticks="outside",
        tickwidth=config["y_axis"]["tickwidth"],
        range=[0, spec["y_axis_upper"]],
        dtick=spec["y_tick_step"],
        autorange=False,
        tickfont=dict(
            color=config["colors"]["foreground"],
            family=config["fonts"]["regular"],
            size=config["fonts"]["axis_label_size"],
        ),
        title_font=dict(
            color=config["colors"]["foreground"],
            family=config["fonts"]["regular"],
            size=config["fonts"]["axis_title_size"],
        ),
        title_standoff=config["y_axis"]["title_standoff"],
        automargin=True,
    )
    fig.add_vline(
        x=float(max_weight_limit),
        line_width=config["cutoff"]["line_width"],
        line_dash=config["cutoff"]["line_dash"],
        line_color=config["colors"]["cutoff"],
    )
    if config.get("debug", {}).get("show_border", False):
        fig.add_shape(
            type="rect",
            xref="paper",
            yref="paper",
            x0=0,
            y0=0,
            x1=1,
            y1=1,
            line=dict(
                color=config["debug"].get("border_color", "#FFFFFF"),
                width=config["debug"].get("border_width", 1),
            ),
            fillcolor="rgba(0,0,0,0)",
            layer="above",
        )

    return fig, spec


def get_clicked_weight(
    selected_points,
    current_limit: float,
    tolerance: float = 1e-9,
    spec: dict | None = None,
):
    if not selected_points:
        return None
    point = selected_points[0] if isinstance(selected_points, list) else {}

    clicked_x = point.get("x")
    new_weight = None

    if clicked_x is not None:
        try:
            new_weight = float(clicked_x)
        except Exception:
            try:
                text_value = str(clicked_x)
                token = ""
                for ch in text_value:
                    if ch.isdigit() or ch in ".-":
                        token += ch
                    elif token:
                        break
                if token:
                    new_weight = float(token)
            except Exception:
                new_weight = None

    if new_weight is None and spec is not None:
        point_index = point.get("pointNumber")
        if point_index is None:
            point_index = point.get("pointIndex")
        if point_index is None:
            point_numbers = point.get("pointNumbers")
            if isinstance(point_numbers, list) and point_numbers:
                point_index = point_numbers[0]
        if point_index is None:
            point_indices = point.get("pointIndices")
            if isinstance(point_indices, list) and point_indices:
                point_index = point_indices[0]
        if point_index is not None:
            try:
                index_int = int(point_index)
                bin_size = float(spec.get("bin_size", 0.0))
                weight_min = float(spec.get("weight_min", 0.0))
                if bin_size > 0:
                    new_weight = weight_min + ((index_int + 1) * bin_size)
            except Exception:
                new_weight = None

    if new_weight is None:
        return None

    if abs(new_weight - float(current_limit)) <= tolerance:
        return None
    return new_weight
