# Flaw Register

> **Internal release analysis** — This register tracks known flaws identified during
> release preparation. It is an internal development artifact, not a public bug list.
> For reporting issues to the project, open a GitHub issue.

Last refreshed: `2026-04-13`

| ID | Flaw | Impact | Owner | Status | Evidence / Fix |
| --- | --- | --- | --- | --- | --- |
| F-001 | `tests/test_ui_smoke.py` mutated `TMP`, `TEMP`, and `tempfile.tempdir` at import time | Suite-order coupling and false negatives in combined verification | Verification | Fixed | Centralized temp handling in `tools/temp_support.py`; moved smoke-suite temp setup out of import-time globals |
| F-002 | Runtime-controller tests depended on temp directories that were not stable under the sandboxed Windows environment | `tests.test_runtime_controller` and `tools.workspace_verify` failed even when controller logic was correct | Runtime / Verification | Fixed | Runtime-controller tests now use explicit repo-local workspaces and direct state/log paths |
| F-003 | `tools.workspace_verify` reported unit tests as one opaque step | Hard to distinguish general regressions from Windows runtime-controller failures | Verification | Fixed | Verification now reports `tests_core` and `tests_runtime_controller` as separate steps |
| F-004 | Maintainer docs described a healthier verification story than the current tree | Release/onboarding trust gap | Docs / Release | Fixed | README, docs index, release docs, and CI metadata refreshed to match the current gate layout |
| F-005 | `app.py` still owns a large amount of orchestration and rendering logic | High-cost change surface and elevated regression risk | UI Architecture | Open | Refactor started with typed view/query-state seams in `app_support/view_state.py` and `app_support/query_state.py` |
