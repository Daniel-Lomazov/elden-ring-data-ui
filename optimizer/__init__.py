"""Optimizer package.

Backward-compatible exports are preserved from legacy optimizer module,
while new dialect-first API is exposed via `optimize`.
"""

from .api import optimize
from .dialect import canonicalize_request, load_request
from .legacy import (
    DEFAULT_OPTIMIZATION_METHOD,
    DEFAULT_OPTIMIZATION_SCOPE,
    OPTIMIZER_METHODS,
    OPTIMIZER_METHODS_BY_SCOPE,
    OPT_SCOPE_COMPLETE_SET,
    OPT_SCOPE_FULL_SET,
    OPT_SCOPE_SINGLE_PIECE,
    get_optimizer_methods,
    optimize_candidates,
    optimize_complete_set,
    optimize_full_set,
    optimize_single_piece,
    register_optimizer_method,
)

__all__ = [
    "DEFAULT_OPTIMIZATION_METHOD",
    "DEFAULT_OPTIMIZATION_SCOPE",
    "OPTIMIZER_METHODS",
    "OPTIMIZER_METHODS_BY_SCOPE",
    "OPT_SCOPE_SINGLE_PIECE",
    "OPT_SCOPE_FULL_SET",
    "OPT_SCOPE_COMPLETE_SET",
    "get_optimizer_methods",
    "register_optimizer_method",
    "optimize_candidates",
    "optimize_single_piece",
    "optimize_full_set",
    "optimize_complete_set",
    "canonicalize_request",
    "load_request",
    "optimize",
]
