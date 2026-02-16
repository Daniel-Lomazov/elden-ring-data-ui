"""Strategy registry for Optimizer Dialect API."""

from __future__ import annotations

from typing import Callable, Dict

import pandas as pd

StrategyFn = Callable[[pd.DataFrame, dict], pd.DataFrame]

_REGISTRY: Dict[str, StrategyFn] = {}


def register_strategy(name: str, strategy: StrategyFn) -> None:
    key = str(name or "").strip().lower()
    if not key:
        raise ValueError("strategy name cannot be empty")
    _REGISTRY[key] = strategy


def get_strategy(name: str) -> StrategyFn | None:
    return _REGISTRY.get(str(name or "").strip().lower())


def list_strategies() -> list[str]:
    return sorted(_REGISTRY.keys())
