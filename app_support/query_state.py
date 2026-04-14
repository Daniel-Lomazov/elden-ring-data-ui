"""Query-param and session hydration helpers for the Streamlit entrypoint."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, MutableMapping


DEFAULT_HIST_VIEW_MODE = "Interactive (click-to-set)"


@dataclass(frozen=True)
class QueryParamHydrationState:
    selected_dataset_label: str
    armor_mode: str
    talisman_mode: str
    armor_piece_type: str
    highlighted_stats: tuple[str, ...]
    lock_stat_order: bool
    single_highlight_stat: str
    sort_order: str
    rows_to_show: int
    optimizer_method: str
    optimizer_engine: str
    optimizer_objective_type: str
    optimizer_encounter_profile: str
    optimizer_lambda_status: float
    optimize_with_weight: bool
    use_max_weight: bool
    hist_view_mode: str
    max_weight_limit: float


class QueryParamAccessor:
    def __init__(self, streamlit_module) -> None:
        self._st = streamlit_module

    def get(self, key: str, default: str = "") -> str:
        try:
            if hasattr(self._st, "query_params"):
                value = self._st.query_params.get(key, default)
                if isinstance(value, list):
                    return str(value[0]) if value else default
                return str(value)
            legacy = self._st.experimental_get_query_params()
            value = legacy.get(key, [default])
            if isinstance(value, list):
                return str(value[0]) if value else default
            return str(value)
        except Exception:
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        return self.get(key, "true" if default else "false").lower() == "true"

    def get_int(self, key: str, default: int) -> int:
        try:
            return int(self.get(key, str(default)))
        except Exception:
            return default

    def update(self, params: Mapping[str, Any]) -> None:
        try:
            if hasattr(self._st, "query_params"):
                self._st.query_params.update(dict(params))
            else:
                self._st.experimental_set_query_params(**dict(params))
        except Exception:
            pass

    def clear(self) -> None:
        try:
            if hasattr(self._st, "query_params"):
                self._st.query_params.clear()
            else:
                self._st.experimental_set_query_params()
        except Exception:
            pass

    def hydrate_session_state(
        self,
        session_state: MutableMapping[str, Any],
        *,
        armor_mode_default: str,
        talisman_mode_default: str,
        optimization_method_default: str,
        optimizer_engine_default: str,
        optimizer_objective_default: str,
        normalize_armor_mode: Callable[[str], str],
        normalize_talisman_mode: Callable[[str], str],
        normalize_method_id: Callable[[str | None], str],
        normalize_engine_id: Callable[[str | None], str],
        normalize_objective_id: Callable[[str | None], str],
        normalize_hist_view_mode: Callable[[str], str],
    ) -> QueryParamHydrationState:
        highlighted_stats = tuple(stat for stat in self.get("stats", "").split("|") if stat)
        try:
            optimizer_lambda_status = float(self.get("lambda_status", "1.0"))
        except Exception:
            optimizer_lambda_status = 1.0
        try:
            max_weight_limit = float(self.get("max_weight", "0.0"))
        except Exception:
            max_weight_limit = 0.0

        hydrated = QueryParamHydrationState(
            selected_dataset_label=self.get("dataset", ""),
            armor_mode=normalize_armor_mode(self.get("armor_mode", armor_mode_default)),
            talisman_mode=normalize_talisman_mode(self.get("talisman_mode", talisman_mode_default)),
            armor_piece_type=self.get("piece_type", ""),
            highlighted_stats=highlighted_stats,
            lock_stat_order=self.get_bool("lock_order", True),
            single_highlight_stat=self.get("single_stat", ""),
            sort_order=self.get("sort", "Highest First"),
            rows_to_show=self.get_int("rows", 5),
            optimizer_method=normalize_method_id(
                self.get("method", optimization_method_default)
            ),
            optimizer_engine=normalize_engine_id(
                self.get("opt_engine", optimizer_engine_default)
            ),
            optimizer_objective_type=normalize_objective_id(
                self.get("objective", optimizer_objective_default)
            ),
            optimizer_encounter_profile=self.get("profile", ""),
            optimizer_lambda_status=optimizer_lambda_status,
            optimize_with_weight=self.get_bool("opt_with_weight", False),
            use_max_weight=self.get_bool("use_max_weight", False),
            hist_view_mode=normalize_hist_view_mode(
                self.get("hist_view", DEFAULT_HIST_VIEW_MODE)
            ),
            max_weight_limit=max_weight_limit,
        )

        session_state["selected_dataset_label"] = hydrated.selected_dataset_label
        session_state["armor_mode"] = hydrated.armor_mode
        session_state["talisman_mode"] = hydrated.talisman_mode
        session_state["armor_piece_type"] = hydrated.armor_piece_type
        session_state["highlighted_stats"] = list(hydrated.highlighted_stats)
        session_state["lock_stat_order"] = hydrated.lock_stat_order
        session_state["single_highlight_stat"] = hydrated.single_highlight_stat
        session_state["sort_order"] = hydrated.sort_order
        session_state["rows_to_show"] = hydrated.rows_to_show
        session_state["show_raw_dev"] = False
        session_state["optimizer_method"] = hydrated.optimizer_method
        session_state["optimizer_engine"] = hydrated.optimizer_engine
        session_state["optimizer_objective_type"] = hydrated.optimizer_objective_type
        session_state["optimizer_encounter_profile"] = hydrated.optimizer_encounter_profile
        session_state["optimizer_lambda_status"] = hydrated.optimizer_lambda_status
        session_state["optimize_with_weight"] = hydrated.optimize_with_weight
        session_state["use_max_weight"] = hydrated.use_max_weight
        session_state["hist_view_mode"] = hydrated.hist_view_mode
        session_state["hist_view_mode_widget"] = hydrated.hist_view_mode
        session_state["max_weight_limit"] = hydrated.max_weight_limit
        session_state["_qp_hydrated"] = True
        return hydrated
