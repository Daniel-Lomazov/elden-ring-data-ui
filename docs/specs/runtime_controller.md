# Runtime Controller Spec (v1)

## Goal

Introduce a Python runtime controller as the single source of truth for detached Streamlit lifecycle behavior while keeping direct foreground `streamlit run app.py` execution unchanged.

## Non-goals

- No native desktop rewrite.
- No embedded webview.
- No tray implementation in this milestone.
- No refactor of `app.py` UI logic unless controller work proves a tiny extraction is necessary.

## Code location

- Primary module: `tools/runtime_controller.py`
- CLI entrypoint: `python -m tools.runtime_controller <command>`
- PowerShell wrappers continue to resolve the correct Python executable and then invoke the controller module.
- The controller itself launches Streamlit with `sys.executable` so the detached app uses the same Python runtime that invoked the controller.

## Transient runtime artifacts

- Runtime state file: `.cache/runtime-controller.json`
- Runtime log file: `.cache/runtime-controller.log`
- Both artifacts are repo-local and ignored by git.
- The legacy `.streamlit_browser_pid` side file stops being authoritative once wrappers delegate to the controller.

## Controller ownership model

- The controller owns detached/background lifecycle only.
- Direct foreground runs from `python -m streamlit run app.py` or `scripts/run_streamlit_local.ps1` remain outside controller ownership by design.
- The controller is allowed to detect a same-app unmanaged process for reconciliation or cleanup.
- The controller must not terminate unrelated processes that happen to occupy the target port.

## Runtime state schema

```json
{
  "version": 1,
  "workspace_root": "C:/repo",
  "entrypoint": "app.py",
  "python_exe": "C:/Python/python.exe",
  "command": ["python", "-m", "streamlit", "run", "app.py", "--server.port", "8501", "--server.headless", "true"],
  "url": "http://localhost:8501",
  "port": 8501,
  "app_pid": 1234,
  "app_started_at": "2026-04-01T15:04:05Z",
  "app_created_at": 1743520000.12,
  "listener_pid": 1234,
  "listener_observed_at": "2026-04-01T15:04:12Z",
  "ready": true,
  "ready_at": "2026-04-01T15:04:12Z",
  "browser_pid": 4321,
  "browser_last_action": "refreshed",
  "last_status": "running",
  "last_error": null,
  "log_path": ".cache/runtime-controller.log"
}
```

### Required fields

- Identity: `version`, `workspace_root`, `entrypoint`, `python_exe`, `command`, `url`, `port`
- Process ownership: `app_pid`, `app_created_at`, `listener_pid`
- Lifecycle: `app_started_at`, `ready`, `ready_at`, `last_status`, `last_error`
- Browser state: `browser_pid`, `browser_last_action`
- Diagnostics: `log_path`

## Live status states

- `stopped`: no controller-owned app is running and no same-app listener is active.
- `starting`: process launched but readiness not yet confirmed.
- `running`: listener exists and HTTP readiness succeeded.
- `stale`: state file points to a dead or mismatched process.
- `unmanaged_same_app`: a matching workspace `streamlit run app.py` process exists without valid controller state.
- `port_conflict`: target port is owned by an unrelated process.
- `failed`: launch or readiness failed and the controller recorded an error.

## Same-app detection rules

A process is considered the same app only when all of the following are true:

- The command line contains `streamlit run app.py`.
- The working tree path or command line matches this repository root.
- The process listener is bound to the requested port.

If those checks fail, the controller must treat the listener as unrelated.

## Readiness contract

- Start Streamlit with:

```text
python -m streamlit run app.py --server.port <port> --server.headless true
```

- Use repository root as the working directory.
- Wait for both:
  - a listener on the requested port
  - a successful HTTP probe to `http://localhost:<port>/`
- Default wait budget: `45` seconds.
- HTTP readiness succeeds on response codes `200-499`, matching the current PowerShell behavior.

## Command contract

### `start`

Behavior:

- If controller-owned state is live, do not leave the old process running alongside a second managed process.
- If controller-owned or same-app state is live on the requested port, stop that same-app session and relaunch it as a fresh managed session.
- If same-app state exists but metadata is stale or missing, reconcile it before restart logic instead of treating it as foreign.
- If target port is occupied by an unrelated process, return `port_conflict` and exit nonzero.
- If no valid same-app session exists, spawn a detached Streamlit process, write state, wait for readiness, and only open the UI when browser opening is explicitly enabled.
- External browser opening is opt-in. By default, `start` leaves the app running headless and available on localhost.
- When `start` had to replace an existing same-app session and browser opening is enabled, browser open behavior should use a fresh window instead of only focusing the previous one.

Default options:

- `--port 8501`
- `--wait-seconds 45`
- `--open-browser false`

Output markers:

- `STATUS=<state>`
- `APP_URL=http://localhost:<port>`
- `START_PID=<pid>`
- `LISTENER_PID=<pid|unknown>`
- `READY=<true|false>`
- `STARTUP_SECONDS=<seconds>`
- `BROWSER_ACTION=<opened|refreshed|failed|skipped>`

### `status`

Behavior:

- Read state file if present.
- Re-probe listener and HTTP readiness.
- Detect stale metadata and unmanaged same-app processes.
- Emit a concise machine-readable summary and exit `0` for `running` or `stopped`, nonzero for `failed` or `port_conflict`.

Output markers:

- `STATUS=<state>`
- `APP_URL=http://localhost:<port>`
- `APP_PID=<pid|none>`
- `LISTENER_PID=<pid|none>`
- `READY=<true|false>`
- `DETAIL=<message>`

### `open`

Behavior:

- If a controller-owned or reconciled same-app session is running, open or focus that UI.
- If the session is not running, exit nonzero with a clear message instead of spawning a process.
- On Windows, prefer current app-window behavior: focus and refresh an existing same-port Edge window when possible; otherwise open a new window and fall back to the default browser if Edge integration is unavailable.
- `open` itself remains non-destructive; the forced close-and-reopen behavior is reserved for restart-style flows such as rerunning `start`, `restart`, and `recover` against the same app.

Output markers:

- `STATUS=<state>`
- `APP_URL=http://localhost:<port>`
- `BROWSER_ACTION=<opened|refreshed|failed>`

### `stop`

Behavior:

- Stop the controller-owned process if it is still alive.
- If metadata is stale but a same-app workspace process is detected, stop that same-app process.
- If no controller-owned or same-app process is found, return success as a no-op.
- Never stop an unrelated process solely because it is bound to the target port.
- Clear or rewrite runtime state after stop completes.

Output markers:

- `STATUS=<stopped|running|port_conflict>`
- `STOPPED_PIDS=<comma-separated or empty>`
- `DETAIL=<message>`

### `restart`

Behavior:

- Equivalent to `stop` followed by `start` using the same port and wait/open defaults.
- If `stop` reports a foreign port conflict, exit nonzero without killing the foreign process.
- If browser opening is enabled, reopen the UI in a fresh window after the restart.

### `recover`

Behavior:

- Repair stale controller state.
- Stop same-app workspace processes that are orphaned or unhealthy.
- Preserve the customer-approved default port policy: auto-recover stale same-app state on `8501`, but never seize the port from unrelated processes.
- Finish with a normal `start` flow, including a fresh browser window on success when browser opening is enabled.

## Logging approach

- Every controller command appends timestamped events to `.cache/runtime-controller.log`.
- Detached Streamlit stdout and stderr are redirected into the same log file.
- Console output stays concise and machine-readable so PowerShell wrappers remain simple.

## Wrapper integration contract

- `scripts/start-app.ps1` becomes a thin wrapper for `python -m tools.runtime_controller start`.
- `scripts/recover-app.ps1` becomes a thin wrapper for `python -m tools.runtime_controller recover`.
- `scripts/reset-dev-session.ps1` delegates runtime stop to `python -m tools.runtime_controller stop` and retains only optional cache cleanup behavior.
- `scripts/stop_streamlit_port.ps1` delegates to controller stop logic by default and may retain an explicit emergency-only hard kill mode if needed for rollback safety.
- `scripts/run-all.ps1` remains an orchestrator and delegates app launch to the updated wrappers.
- `scripts/run_streamlit_local.ps1` remains the direct foreground fallback and does not delegate to the controller.

## Rollback contract

- Reverting the controller and wrappers must restore the previous detached PowerShell-owned behavior.
- Direct foreground launch remains available throughout the migration.
- No controller-specific metadata is required for direct `streamlit run` to function.