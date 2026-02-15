# Startup + Verify Deep Dive (2026-02-15)

## Goal
Make the repeated dev loop faster and clearer:
- setup environment,
- verify workspace,
- relaunch app.

## What was optimized

### 1) Consolidated verification runner
- Added `tools/workspace_verify.py`.
- `scripts/verify-workspace.ps1` now runs one consolidated Python entrypoint instead of separate shell-level check invocations.
- Supports:
  - full mode (default): final + optimizer checks,
  - quick mode (`-Quick`): skips optimizer and app import check.

### 2) Faster verify execution path
- `verify-workspace.ps1` now resolves the environment Python executable and runs it directly.
- Removed repeated `conda run` overhead for verification.
- Script now prints explicit timings:
  - verification runtime,
  - total script runtime.

### 3) Cached dependency sync for setup
- `scripts/ensure-conda-env.ps1` now stores a SHA-256 hash of `requirements.txt` in `.cache/requirements.sha256`.
- If unchanged, pip install is skipped automatically.
- Force refresh is still available via `-AlwaysSyncPip`.

### 4) Better orchestration observability
- `scripts/run-all.ps1` now prints phase timings:
  - reset,
  - environment,
  - verification,
  - app launch,
  - total.
- Fixed browser behavior passthrough: app browser opens only when `-OpenBrowser` is explicitly provided.

### 5) Startup timing visibility
- `scripts/start-app.ps1` now prints:
  - process spawn timing,
  - startup total seconds (`STARTUP_SECONDS`).

## Measured timings (current machine)

### Baseline (before this optimization batch)
- `verify-workspace.ps1`: ~8.60s
- `run-all.ps1 -SkipReset -SkipVerify`: ~9.70s (pip always synced)

### After optimization
- `verify-workspace.ps1`: ~3.35s
- `verify-workspace.ps1 -Quick`: ~3.49s
- `run-all.ps1 -SkipReset -SkipVerify`: ~1.45s (requirements unchanged)
- `run-all.ps1 -SkipReset -QuickVerify -RunApp`: ~6.82s

## Recommended command profiles

### Fast edit/relaunch loop
```powershell
./scripts/run-all.ps1 -SkipReset -QuickVerify -RunApp
```

### Full confidence check
```powershell
./scripts/verify-workspace.ps1
```

### Full dependency refresh (when requirements changed)
```powershell
./scripts/run-all.ps1 -AlwaysSyncPip -RunApp
```

## Notes
- Quick verify prioritizes relaunch speed and skips heavier checks.
- Full verify remains available for pre-commit confidence.
- `.cache/` is intentionally ignored in git.
