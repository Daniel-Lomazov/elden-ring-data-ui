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

## Phase 1 - Repo Reconfirmation And Decision Inventory

### Confirmed repo map

| File | Purpose | Phase 1 finding |
|------|---------|-----------------|
| `scripts/run_streamlit_local.ps1` | Direct foreground Streamlit fallback | Must remain untouched as the rollback-safe foreground path. |
| `scripts/start-app.ps1` | Detached start, readiness polling, browser open/focus | Current owner of start behavior; target to become a thin wrapper over the controller. |
| `scripts/recover-app.ps1` | Recovery composition | Currently reset + start; target to delegate to controller `recover`. |
| `scripts/reset-dev-session.ps1` | Process cleanup by listener PID and command-line match | Current stop heuristic; controller will preserve it as fallback cleanup logic. |
| `scripts/stop_streamlit_port.ps1` | Explicit port kill helper | Remains useful as a blunt helper, but controller becomes primary lifecycle path. |
| `scripts/run-all.ps1` | High-level dev orchestration | Can continue composing reset/verify/run while delegating launch to controller-backed wrappers. |
| `scripts/verify-workspace.ps1` | PowerShell verification entrypoint | Existing verification surface to preserve and extend with controller tests. |
| `tools/workspace_verify.py` | Consolidated verification runner | Existing Python operational entrypoint pattern; strong fit for a new controller module. |
| `.streamlit/config.toml` | Localhost binding and default port | Confirms current local-only behavior and default port 8501. |
| `.gitignore` | Ignored transient artifacts | Confirms `.cache/` is the right transient home for controller metadata/logs. |
| `tests/test_ui_smoke.py` | Headless Streamlit startup smoke | Existing automated evidence for direct Streamlit launch behavior. |

### Current ownership map

- `start`: `scripts/start-app.ps1`
- `stop`: `scripts/reset-dev-session.ps1` and `scripts/stop_streamlit_port.ps1`
- `status`: implicit only, inferred from readiness probes and manual localhost checks
- `open`: `scripts/start-app.ps1` Edge/default-browser logic
- `recover`: `scripts/recover-app.ps1`
- Direct foreground fallback: `scripts/run_streamlit_local.ps1` and `python -m streamlit run app.py`

### Customer decision log

| Decision area | Answer | Acceptance criteria for implementation |
|---------------|--------|----------------------------------------|
| `start` default behavior | Start and auto-open/focus the UI | `controller start` keeps the convenience-first behavior and can bring the UI to the front once ready. |
| `start` when already running | Focus/refresh the existing session | Repeated `start` is idempotent for process ownership and acts as a bring-to-front action instead of creating duplicate sessions. |
| Default port policy | Default to `8501` and auto-recover stale same-app state | The controller prefers `8501`, can detect stale controller-managed state, and should self-heal stale same-app ownership without silently taking over unrelated processes. |
| Logging visibility | Console plus a repo-local `.cache` log file | Background lifecycle commands emit concise console status and persist a controller log under `.cache/` for troubleshooting. |

### Finalized scope for controller milestone

- Add a Python runtime controller under the operational Python surface rather than inside `app.py`.
- Keep Streamlit as the UI and keep direct `streamlit run app.py` plus `scripts/run_streamlit_local.ps1` as the rollback-safe fallback path.
- Rewire detached lifecycle wrappers to the controller while preserving current localhost defaults and browser-first ergonomics.
- Use `.cache/` for controller metadata and log artifacts because it is already the repo's ignored transient area.
- Defer any tray-shell work until the explicit post-controller checkpoint in Phase 7.

PHASE BENCHMARK
- Phase: 1 - Repo reconfirmation and decision inventory
- Planned outcome: Confirm the assessment against repo reality and resolve the minimum customer-facing defaults needed for the controller contract.
- Actual outcome: Reconfirmed the lifecycle ownership map from repo evidence, identified `.cache/` as the transient home for controller state, and captured customer-approved defaults for start/open behavior, stale-state handling, and log visibility.
- Evidence: README review, lifecycle script review, `.streamlit/config.toml`, `.gitignore`, verification tooling review, and interactive BA/CS decision answers recorded in this file.
- Tests/checks run: Read-only repo inspection, subagent reviews, targeted config/persistence searches, and BA/CS question flow.
- Pass/fail summary: PASS
- Self-score on correctness (0-5): 5
- Self-score on stability (0-5): 5
- Self-score on minimalism/scope control (0-5): 5
- Self-score on rollback safety (0-5): 5
- Gaps or regressions: No runtime execution yet; controller contract still needs to formalize exact CLI, metadata schema, and stale-state semantics.
- Decision: proceed
- Plan adjustment for next phase: Define the controller as a Python operational module with stable commands, repo-local transient metadata/logging, and wrapper-compatible output markers before any implementation begins.

## Phase 2 - Controller Architecture Contract

- Contract file: `docs/specs/runtime_controller.md`
- Chosen implementation location: `tools/runtime_controller.py`
- Chosen CLI surface: `python -m tools.runtime_controller start|stop|status|open|restart|recover`
- Chosen transient artifacts:
  - `.cache/runtime-controller.json`
  - `.cache/runtime-controller.log`
- Chosen ownership rule: detached/background lifecycle is controller-owned; direct foreground Streamlit runs stay outside controller ownership.
- Chosen recovery rule: stale same-app state may be reconciled or cleaned up automatically; unrelated port owners must never be terminated by the controller.
- Chosen browser rule: `start` implies `open`, and already-running sessions are brought to the front instead of duplicated.

PHASE BENCHMARK
- Phase: 2 - Controller architecture contract
- Planned outcome: Freeze the controller interface, state layout, readiness contract, and wrapper integration points before implementation.
- Actual outcome: Added a concrete controller spec with command semantics, state schema, `.cache` artifact locations, same-app recovery rules, logging rules, and wrapper responsibilities.
- Evidence: `docs/specs/runtime_controller.md`
- Tests/checks run: Repo pattern review against existing `tools.*` module entrypoints and script integration points.
- Pass/fail summary: PASS
- Self-score on correctness (0-5): 5
- Self-score on stability (0-5): 5
- Self-score on minimalism/scope control (0-5): 5
- Self-score on rollback safety (0-5): 5
- Gaps or regressions: Browser focus implementation details still need code-level validation on Windows.
- Decision: proceed
- Plan adjustment for next phase: Implement the controller in one additive Python module first, then only extract tiny helpers if that becomes necessary for testability or clarity.

## Phase 3 - Controller Core Implementation

- Added controller module: `tools/runtime_controller.py`
- Implemented commands:
  - `start`
  - `stop`
  - `status`
  - `open`
  - `restart`
  - `recover`
- Implemented controller-owned artifacts:
  - `.cache/runtime-controller.json`
  - `.cache/runtime-controller.log`
- Implemented same-app safeguards:
  - controller-owned state is validated against live process identity when possible
  - same-app `streamlit run app.py` processes can be reconciled when metadata is stale or absent
  - unrelated port owners report conflict instead of being terminated
- Implemented browser behavior:
  - Windows path prefers existing Edge window focus/refresh when possible
  - fallback path opens the default browser if Edge-specific automation is unavailable

### Live command evidence

- `python -m tools.runtime_controller status --port 8501` reported `STATUS=stopped` before launch.
- `python -m tools.runtime_controller start --port 8501 --wait-seconds 45 --no-open-browser` launched a detached Streamlit session and wrote runtime state/log artifacts.
- `python -m tools.runtime_controller status --port 8501` reported a live session with matching `APP_PID` and `LISTENER_PID`.
- `python -m tools.runtime_controller open --port 8501` returned `BROWSER_ACTION=opened`.
- Repeating `start` reused the live session rather than spawning a duplicate process.
- `python -m tools.runtime_controller restart --port 8501 --wait-seconds 45 --no-open-browser` stopped PID `34728` and relaunched PID `31560`.
- `python -m tools.runtime_controller recover --port 8501 --wait-seconds 45 --no-open-browser` relaunched a fresh session and preserved controller ownership.
- `python -m tools.runtime_controller stop --port 8501` stopped the managed process, and a final `status` returned `STATUS=stopped`.

PHASE BENCHMARK
- Phase: 3 - Implement the controller core
- Planned outcome: Create an additive Python runtime controller that owns detached Streamlit lifecycle, state, readiness, open, and recovery behavior.
- Actual outcome: Added `tools/runtime_controller.py`, persisted runtime metadata/logging in `.cache`, and verified live lifecycle commands against the app on port `8501`.
- Evidence: `tools/runtime_controller.py`, `.cache/runtime-controller.json`, `.cache/runtime-controller.log`, and live command runs recorded above.
- Tests/checks run: module error check, direct `status`, direct `start`, direct `open`, repeated `start`, `restart`, `recover`, `stop`, and final `status`.
- Pass/fail summary: PASS
- Self-score on correctness (0-5): 5
- Self-score on stability (0-5): 4
- Self-score on minimalism/scope control (0-5): 5
- Self-score on rollback safety (0-5): 5
- Gaps or regressions: Browser actions were verified through command success and log/state updates, but wrapper-level launch behavior is still untested because scripts have not been rewired yet.
- Decision: proceed
- Plan adjustment for next phase: Rewire existing lifecycle scripts into thin controller wrappers while preserving `scripts/run_streamlit_local.ps1` as the direct foreground fallback.