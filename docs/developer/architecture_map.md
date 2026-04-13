# Architecture Map

Last refreshed: `2026-04-13`

## Entry Surfaces

- `app.py`
  - Streamlit entrypoint and top-level composition layer.
- `tools/runtime_controller.py`
  - Detached runtime lifecycle CLI for start/status/open/stop/restart/recover.

## UI / App State Seams

- `app_support/view_state.py`
  - Typed dataset/view/detail key resolution and side-by-side embed URL helpers.
- `app_support/query_state.py`
  - Query-param access and typed session hydration contract.
- `app_support/dataset_ui.py`
  - Dataset capability registry, scope/view support, and selector behavior.
- `app_support/dataset_presentations.py`
  - Dataset-specific presentation specs, formatting, and detail/card metadata.
- `app_support/optimization_view.py`
  - Typed optimizer control state and preset/profile resolution.

## Data / Optimization

- `data_loader.py`
  - CSV loading, file-signature cache invalidation, and profile-based column loading.
- `optimizer/api.py`
  - Dialect-first optimizer entrypoint.
- `optimizer/catalog.py`
  - Engine/objective/method/scope capability matrix.
- `optimizer/dialect.py`
  - Request loading, normalization, and validation.
- `optimizer/strategies/*`
  - Objective-specific ranking implementations.

## Operational Verification

- `tools/temp_support.py`
  - Shared temp-root and cleanup helpers for tests and verification.
- `tools/workspace_verify.py`
  - Consolidated verification runner.
  - Runs `tests_core` everywhere and `tests_runtime_controller` on Windows.
- `tests/test_ui_smoke.py`
  - Streamlit behavior and preserved-flow smoke coverage.
- `tests/test_runtime_controller.py`
  - Runtime lifecycle regression coverage.

## Current Refactor Boundary

- Preserve UI labels, dataset keys, selector behavior, optimization semantics, deferred-dataset handling, and progression-table behavior.
- Continue extracting state, rendering, and orchestration helpers out of `app.py` without changing public entrypoints.
