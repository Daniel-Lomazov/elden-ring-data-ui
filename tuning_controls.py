import time


def apply_auto_ratio_adjustment(
    st,
    ratio_key: str,
    min_value: float,
    max_value: float,
    base_step: float = 0.000005,
) -> bool:
    direction_key = f"_{ratio_key}_auto_direction"
    speed_key = f"_{ratio_key}_auto_speed"
    started_key = f"_{ratio_key}_auto_started"
    last_tick_key = f"_{ratio_key}_auto_last_tick"

    direction = int(st.session_state.get(direction_key, 0))
    if direction == 0:
        return False
    speed = float(st.session_state.get(speed_key, 1.0))
    if speed <= 0:
        speed = 1.0

    now = time.time()
    started_at = float(st.session_state.get(started_key, now))
    last_tick = float(st.session_state.get(last_tick_key, now))
    dt = max(0.0, min(0.30, now - last_tick))
    elapsed = max(0.0, now - started_at)

    speed_multiplier = min(18.0, 1.0 + (elapsed * 3.0))
    tick_scale = max(1.0, dt * 60.0)

    current = float(st.session_state.get(ratio_key, 1.0))
    updated = current + (direction * base_step * speed * speed_multiplier * tick_scale)
    updated = max(min_value, min(max_value, updated))

    st.session_state[ratio_key] = float(updated)
    st.session_state[last_tick_key] = now

    if abs(updated - current) < 1e-12:
        st.session_state[direction_key] = 0
        return False

    return True


def apply_transport_action(st, ratio_key: str, action: str):
    direction_key = f"_{ratio_key}_auto_direction"
    speed_key = f"_{ratio_key}_auto_speed"
    started_key = f"_{ratio_key}_auto_started"
    last_tick_key = f"_{ratio_key}_auto_last_tick"

    current_direction = int(st.session_state.get(direction_key, 0))
    current_speed = float(st.session_state.get(speed_key, 1.0))
    now = time.time()

    if action == "stop":
        st.session_state[direction_key] = 0
        st.session_state[speed_key] = 1.0
        return

    if action == "play_fwd":
        if current_direction == 1:
            return
        st.session_state[direction_key] = 1
        st.session_state[speed_key] = 1.0
        st.session_state[started_key] = now
        st.session_state[last_tick_key] = now
        return

    if action == "play_bwd":
        if current_direction == -1:
            return
        st.session_state[direction_key] = -1
        st.session_state[speed_key] = 1.0
        st.session_state[started_key] = now
        st.session_state[last_tick_key] = now
        return

    if action == "fast_fwd":
        if current_direction == 1:
            st.session_state[speed_key] = max(1.0, current_speed) * 2.0
            return
        if current_direction == -1:
            st.session_state[direction_key] = 1
            st.session_state[speed_key] = 1.0
        else:
            st.session_state[direction_key] = 1
            st.session_state[speed_key] = 2.0
        st.session_state[started_key] = now
        st.session_state[last_tick_key] = now
        return

    if action == "fast_bwd":
        if current_direction == -1:
            st.session_state[speed_key] = max(1.0, current_speed) * 2.0
            return
        if current_direction == 1:
            st.session_state[direction_key] = -1
            st.session_state[speed_key] = 1.0
        else:
            st.session_state[direction_key] = -1
            st.session_state[speed_key] = 2.0
        st.session_state[started_key] = now
        st.session_state[last_tick_key] = now
        return


def render_dimension_tuning_toggle(
    st,
    ui,
    label: str,
    enable_key: str,
    prev_enable_key: str,
    restore_values: dict,
    help_text: str,
) -> bool:
    enabled = ui.checkbox(label, key=enable_key, help=help_text)
    was_enabled = bool(st.session_state.get(prev_enable_key, False))
    if enabled and not was_enabled:
        for target_key, fallback in restore_values.items():
            st.session_state[target_key] = float(st.session_state.get(fallback, 1.0))
    st.session_state[prev_enable_key] = bool(enabled)
    return enabled


def render_transport_number_input(
    st,
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
    if input_key not in st.session_state:
        st.session_state[input_key] = float(
            st.session_state.get(canonical_key, st.session_state.get(default_key, 1.0))
        )

    bwd_fast_col, bwd_col, stop_col, fwd_col, fwd_fast_col = ui.columns(5)
    if bwd_fast_col.button("◀◀", key=f"{control_id}_auto_bwd_fast"):
        apply_transport_action(st, input_key, "fast_bwd")
    if bwd_col.button("◀", key=f"{control_id}_auto_bwd"):
        apply_transport_action(st, input_key, "play_bwd")
    if fwd_col.button("▶", key=f"{control_id}_auto_fwd"):
        apply_transport_action(st, input_key, "play_fwd")
    if fwd_fast_col.button("▶▶", key=f"{control_id}_auto_fwd_fast"):
        apply_transport_action(st, input_key, "fast_fwd")
    if stop_col.button("■", key=f"{control_id}_auto_stop"):
        apply_transport_action(st, input_key, "stop")

    auto_active = apply_auto_ratio_adjustment(
        st,
        ratio_key=input_key,
        min_value=min_value,
        max_value=max_value,
        base_step=base_step,
    )

    value = ui.number_input(
        label,
        min_value=min_value,
        max_value=max_value,
        step=step,
        format=display_format,
        key=input_key,
        help=help_text,
    )
    st.session_state[canonical_key] = float(value)
    return float(value), bool(auto_active)
