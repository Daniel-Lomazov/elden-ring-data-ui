import copy
from typing import Any, Callable, Dict, Tuple


UNIFORM_HISTOGRAM_PARAMS: Dict[str, Any] = {
    "grid": {
        "column_weights": [1, 1],
        "gap": "medium",
    },
    "dimensions": {
        "base_embed_width": 760,
        "height_key": "height",
        "embed_height_key": "embed_height",
    },
    "offset_limits": {
        "x_min": -600,
        "x_max": 600,
        "y_min": -400,
        "y_max": 400,
    },
    "ratio_limits": {
        "width_min": 0.05,
        "width_max": 12.0,
        "height_min": 0.1,
        "height_max": 12.0,
    },
}


VIEW_SPECIFIC_HISTOGRAM_PARAMS: Dict[str, Dict[str, Any]] = {
    "classic": {
        "width_mode": "pixel",
        "embed_height_trim": 0,
    },
    "interactive": {
        "width_mode": "container",
        "container_width_value": "100%",
        "embed_height_trim": 12,
    },
}


def place_one_by_two_grid(ui, column_weights=None, gap=None) -> Tuple[Any, Any]:
    grid_cfg = UNIFORM_HISTOGRAM_PARAMS["grid"]
    weights = column_weights or grid_cfg["column_weights"]
    cell_gap = gap or grid_cfg["gap"]
    return ui.columns(weights, gap=cell_gap)


def place_n_by_m_grid(
    ui,
    rows: int,
    cols: int,
    column_weights=None,
    gap=None,
):
    if rows <= 0 or cols <= 0:
        raise ValueError("rows and cols must be positive")

    weights = column_weights or [1] * cols
    cell_gap = gap or UNIFORM_HISTOGRAM_PARAMS["grid"]["gap"]
    grid_rows = []
    for _ in range(rows):
        grid_rows.append(ui.columns(weights, gap=cell_gap))
    return grid_rows


def place_graphical_object_in_grid_cell(
    cell,
    label: str,
    render_fn: Callable[[Any], Any],
    controls_fn: Callable[[Any], None] | None = None,
):
    panel = cell.container()
    panel.caption(label)
    chart_slot = panel.container()
    controls_slot = panel.container()
    result = render_fn(chart_slot)
    if controls_fn is not None:
        controls_fn(controls_slot)
    return result


def resolve_auto_render_layer(
    base_config: Dict[str, Any],
    view_kind: str,
    layout_mode: str,
    width_ratio: float,
    height_ratio: float,
    x_offset_px: float,
    y_offset_px: float,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if view_kind not in VIEW_SPECIFIC_HISTOGRAM_PARAMS:
        raise ValueError(f"Unknown histogram view kind: {view_kind}")

    uniform = UNIFORM_HISTOGRAM_PARAMS
    custom = VIEW_SPECIFIC_HISTOGRAM_PARAMS[view_kind]
    config = copy.deepcopy(base_config)

    dims_cfg = uniform["dimensions"]
    layout_cfg = config["layout"]
    base_height = int(base_config["layout"][dims_cfg["height_key"]])
    base_embed_height = int(
        base_config["layout"].get(dims_cfg["embed_height_key"], base_height)
    )

    x_min = float(uniform["offset_limits"]["x_min"])
    x_max = float(uniform["offset_limits"]["x_max"])
    y_min = float(uniform["offset_limits"]["y_min"])
    y_max = float(uniform["offset_limits"]["y_max"])

    x_offset = int(round(max(x_min, min(x_max, float(x_offset_px)))))
    y_offset = int(round(max(y_min, min(y_max, float(y_offset_px)))))

    layout_cfg[dims_cfg["height_key"]] = int(round(base_height * float(height_ratio)))
    layout_cfg[dims_cfg["embed_height_key"]] = int(
        round(base_embed_height * float(height_ratio))
    )
    layout_cfg["x_offset_px"] = x_offset
    layout_cfg["y_offset_px"] = y_offset

    if layout_mode == "grid":
        layout_cfg.pop("width", None)
        layout_cfg["embed_width"] = custom.get("container_width_value", "100%")
    elif custom["width_mode"] == "container":
        layout_cfg.pop("width", None)
        layout_cfg["embed_width"] = custom.get("container_width_value", "100%")
    else:
        base_embed_width = int(uniform["dimensions"]["base_embed_width"])
        width_px = int(round(base_embed_width * float(width_ratio)))
        layout_cfg["width"] = width_px
        layout_cfg["embed_width"] = width_px

    render_height = int(
        layout_cfg.get(dims_cfg["embed_height_key"], layout_cfg[dims_cfg["height_key"]])
    )
    trim = int(custom.get("embed_height_trim", 0) or 0)
    render_layer = {
        "override_height": max(120, render_height - trim),
    }
    return config, render_layer
