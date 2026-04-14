# Development Guide

This document describes the architecture, module responsibilities, test entry points,
and CI expectations for `elden-ring-data-ui`. Start here after reading
[`../README.md`](../README.md) and [`../CONTRIBUTING.md`](../CONTRIBUTING.md).

---

## Architecture overview

```
elden_ring_data_ui/
├── app.py                  # Main Streamlit UI entry point
├── app_support/            # UI state, query, and view helpers
├── optimizer/              # Optimizer package (dialect API, strategies, constraints)
├── data_loader.py          # CSV loading and cache-backed read helpers
├── histogram_views.py      # Histogram rendering and interaction config
├── histogram_layout.py     # Histogram sizing and layout helpers
├── ui_components.py        # Parsing and UI utility helpers
├── tuning_controls.py      # Optimizer tuning control helpers
├── tools/                  # Verification orchestrator and smoke tools
├── tests/                  # Unit and integration test suite
├── scripts/                # PowerShell automation: setup, run, recover, verify
└── data/                   # Datasets, load-profile config, and icon registry
```

---

## Module roles

### `app.py`

The Streamlit application entry point. Contains `main()`, which orchestrates:
- Dataset loading and cache management (`@st.cache_resource`, `@lru_cache`)
- Session state initialization and query parameter hydration via `app_support`
- Optimizer preset handling and weight-session mutation
- Dataset-specific view dispatch (browse, ranked, optimization, side-by-side)

`app.py` is intentionally the integration surface. Extract helpers to `app_support/`
when logic becomes reusable or independently testable.

### `app_support/`

Focused helpers for specific UI subsystems:

| Module | Role |
|--------|------|
| `dataset_ui.py` | Dataset rendering, view dispatch, and sidebar controls |
| `dataset_presentations.py` | Card/table presentation logic for each dataset type |
| `detail_scope.py` | Detailed-item scope and focus helpers |
| `optimization_view.py` | Optimization result view and resolver support |

### `optimizer/`

The optimizer package exposes a structured API:

| Module | Role |
|--------|------|
| `api.py` | Public entry point; `optimize()` and `optimize_from_dialect()` |
| `dialect.py` | Typed request/response contract (`OptimizeRequest`, `OptimizeResponse`) |
| `catalog.py` | Dataset catalog and stat-key registry |
| `constraints.py` | Constraint builders for stat floors/ceilings and set requirements |
| `strategies/` | Solver strategy implementations |
| `features/` | Feature extraction and scoring helpers |
| `schema.py` | Shared types and enums |
| `presets.py` | Preset definitions for the optimizer UI |
| `registry.py` | Strategy and preset registration |
| `legacy.py` | Compatibility shims for older call sites |

See [`specs/optimizer_dialect.md`](specs/optimizer_dialect.md) for the full
request/response contract.

### `data_loader.py`

All CSV loading goes through `data_loader.py`. It provides:
- Cache-backed dataset reads using `@st.cache_resource`
- Column profile application from `data/column_loading_instructions.json`
- Checksum validation against `data_checksums.json`

Do not load CSV files directly in other modules.

### `tools/`

| Module | Role |
|--------|------|
| `workspace_verify.py` | Central verification orchestrator; used by CI and scripts |
| `final_check.py` | Fast import/data probe (always runs first) |
| `optimizer_check.py` | Deterministic optimizer sanity checks |
| `optimizer_smoke.py` | Broader optimizer smoke coverage and rank validation |
| `runtime_controller.py` | Managed app lifecycle controller |
| `secure_data.py` | Data integrity helpers |

---

## Test entry points

All tests live in `tests/`. The supported way to run them:

```powershell
# Full suite via orchestrator (recommended)
.\.venv\Scripts\python.exe -m tools.workspace_verify

# Quick lint + smoke only (~10s)
.\.venv\Scripts\python.exe -m tools.workspace_verify --quick

# Targeted subsets
.\.venv\Scripts\python.exe -m unittest tests.test_ui_smoke -q
.\.venv\Scripts\python.exe -m unittest tests.test_runtime_controller -q
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

### Key test files

| Test file | What it covers |
|-----------|---------------|
| `test_ui_smoke.py` | Streamlit AppTest smoke tests; primary safety net for `app.py` changes |
| `test_optimization_view_support.py` | Optimization result view resolver behavior |
| `test_optimizer_matrix.py` | Optimizer multi-stat scoring matrix |
| `test_optimizer_presets.py` | Preset definitions and application |
| `test_dialect.py` | Dialect request/response contract validation |
| `test_runtime_controller.py` | Runtime controller lifecycle and Windows-path behavior |
| `test_dataset_ui_registry.py` | Dataset UI dispatch and view registry |
| `test_data_loader_cache.py` | CSV loading and cache correctness |
| `test_dataset_presentation.py` | Card and table presentation output |
| `test_dataset_value_standardization.py` | Column normalization and standardization |
| `test_monotonicity.py` | Optimizer monotonicity invariants |
| `test_weighted_sum_behavior.py` | Weighted scoring correctness |
| `test_full_set_encounter_constraints.py` | Full-set encounter constraint logic |
| `test_full_set_stat_rank.py` | Full-set stat ranking correctness |

### UI smoke tests (`test_ui_smoke.py`)

These use `streamlit.testing.v1` (marked experimental by Streamlit). The tests
create isolated `AppTest` instances with temporary directories managed by
`tools/temp_support.py`. If the Streamlit testing API changes, these tests are
the first to break.

---

## CI expectations

GitHub Actions runs `.github/workflows/ci.yml` on:
- Every push to `main` and `dev/lomazov`
- Every pull request targeting `main`
- Manual dispatch (`workflow_dispatch`)
- Scheduled (nightly) deep run

### CI jobs

| Job | OS | Python | What runs |
|-----|----|--------|-----------|
| `lint-and-verify` | ubuntu-latest | 3.11 | `ruff check .` → `python -m tools.workspace_verify` |
| `verify-windows` | windows-latest | 3.11 | `python -m tools.workspace_verify` (full suite) |

The `lint-and-verify` job is **required** for merging into `main` (branch
protection). `verify-windows` runs for parity but is not a blocking gate.

### Branch protection on `main`

- Required status check: `lint-and-verify` (strict — must pass on latest commit)
- 1 approving PR review required
- Stale reviews dismissed on new push
- All conversations must be resolved
- Force push and branch deletion disabled

---

## Adding a new dataset

1. Add the CSV file to `data/`.
2. Register it in `data/active_datasets.json`.
3. Add column profile entries to `data/column_loading_instructions.json` if needed.
4. Update `data_loader.py` to handle any new loading patterns.
5. Add dataset presentation logic in `app_support/dataset_presentations.py`.
6. Run `python -m tools.workspace_verify` to confirm no regressions.

---

## Extending the optimizer

1. Add new strategies under `optimizer/strategies/`.
2. Register them in `optimizer/registry.py`.
3. Update the dialect contract in `optimizer/dialect.py` and document in
   [`specs/optimizer_dialect.md`](specs/optimizer_dialect.md).
4. Add tests in `tests/test_optimizer_matrix.py` or a new targeted file.
5. Run `python -m tools.workspace_verify` (includes optimizer smoke).

---

## Runtime verification workflow

```
ruff check .                           # lint
python -m tools.workspace_verify       # full local verification
python -m unittest discover -s tests   # bare test runner (no orchestrator)
```

The orchestrator (`workspace_verify`) runs steps in order:
`final_check` → `optimizer_check` → `optimizer_smoke` → `tests_core` → `tests_runtime_controller`

Each step exits non-zero on failure and blocks subsequent steps.
