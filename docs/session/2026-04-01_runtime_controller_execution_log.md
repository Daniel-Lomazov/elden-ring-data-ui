# Runtime Controller Execution Log

## Phase 0 - Branch Creation And Baseline

- Branch name: `feat/runtime-controller-hybrid-shell`
- Starting commit: `198257724b26f5036ebb2c6916cef51087524ea8`
- Baseline run method:
  - Direct foreground fallback: `python -m streamlit run app.py` from the project environment.
  - Script fallback: `./scripts/run_streamlit_local.ps1` launches `python -m streamlit run app.py --server.port 8501` in the foreground and is stopped with `Ctrl+C`.
  - Detached convenience run: `./scripts/start-app.ps1` launches Streamlit in the background, waits for readiness, and opens or refreshes an Edge window for `http://localhost:8501` by default.
  - Recovery path: `./scripts/recover-app.ps1` resets the local session, then calls `./scripts/start-app.ps1`.
- Baseline verification commands:
  - `./scripts/verify-workspace.ps1`
  - `python -m tools.workspace_verify`
  - `./scripts/run-all.ps1 -RunApp`
  - `./scripts/run-all.ps1 -SkipReset -QuickVerify -RunApp -OpenBrowser`
- Baseline automated test inventory:
  - `tests/test_data_loader_cache.py`
  - `tests/test_dataset_ui_registry.py`
  - `tests/test_dialect.py`
  - `tests/test_full_set_encounter_constraints.py`
  - `tests/test_full_set_stat_rank.py`
  - `tests/test_monotonicity.py`
  - `tests/test_optimization_view_resolver.py`
  - `tests/test_optimization_view_support.py`
  - `tests/test_optimizer_matrix.py`
  - `tests/test_optimizer_presets.py`
  - `tests/test_ui_smoke.py`
  - `tests/test_weighted_sum_behavior.py`
- Baseline known risks:
  - Lifecycle ownership is spread across multiple PowerShell scripts instead of a single runtime authority.
  - Browser-open and browser-focus behavior is embedded inside `scripts/start-app.ps1`.
  - Stop and recover behavior uses port scans and command-line matching without persistent runtime metadata.
  - Detached startup can leave stale state ambiguous because there is no controller-owned runtime record.
- Rollback paths:
  - Git rollback anchor: `git checkout main` at `198257724b26f5036ebb2c6916cef51087524ea8`.
  - Runtime fallback: `./scripts/run_streamlit_local.ps1` and direct `python -m streamlit run app.py` remain the non-controller execution path.
  - Existing script wrappers remain the comparison baseline until Phase 4 rewiring.

PHASE BENCHMARK
- Phase: 0 - Branch creation and clean starting point
- Planned outcome: Isolate work on a new branch and document the current launch, verification, and rollback baseline.
- Actual outcome: Created `feat/runtime-controller-hybrid-shell`, recorded the starting commit, and documented current script-driven lifecycle behavior plus rollback paths.
- Evidence: `git checkout -b feat/runtime-controller-hybrid-shell`; baseline captured in this file.
- Tests/checks run: `git status` via source control inspection, branch check, commit hash capture, script and README review.
- Pass/fail summary: PASS
- Self-score on correctness (0-5): 5
- Self-score on stability (0-5): 5
- Self-score on minimalism/scope control (0-5): 5
- Self-score on rollback safety (0-5): 5
- Gaps or regressions: No runtime execution performed yet; baseline is documentation-backed and source-backed only.
- Decision: proceed
- Plan adjustment for next phase: Reconfirm repo entrypoints and product-facing behavior, then ask only the customer decisions that materially affect controller defaults.