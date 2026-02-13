# Sanity Checks and Alignment Debug Posture — 2026-02-13

This file summarizes the current sanity-check coverage and the debug/alignment posture for histogram work.

## Existing Sanity Checks

- `final_check.py`
  - Import integrity and dataset access validation.
- `optimizer_check.py`
  - Optimizer behavior smoke checks.
- Script-level readiness checks in `start-app.ps1`
  - TCP listener detection
  - HTTP readiness probe
  - machine-readable startup flags (`READY`, `LISTENER_PID`).
- Manual UI check: verify weighted-sum weights change ranking order when adjusted.

## Operational Commands (Canonical)

- Full verify + run (recommended):
  - `./scripts/run-all.ps1 -RunApp -OpenBrowser -WaitForReadySeconds 60`
- Fast recovery:
  - `./scripts/recover-app.ps1 -OpenBrowser`
- Verify only:
  - `./scripts/verify-workspace.ps1`

## Histogram Alignment Debug Posture

Current mechanism:
- Temporary debug border toggle in app state and histogram config path.

Recommended usage pattern:
1. Enable debug border while tuning width/height/offset values.
2. Validate in all three modes:
   - Classic
   - Interactive
   - Side-by-side
3. Validate again after mode changes and reruns.
4. Disable border for normal operation.

## What is intentionally not added (minimal-change policy)

- No new heavy test framework.
- No persistent debug UI panels.
- No global refactor unrelated to histogram/render or startup reliability.

## Known Stable Baseline

At this point, stable baseline means:
- startup scripts produce `READY=True`,
- app reachable on `http://localhost:8501`,
- histogram view state synchronized,
- interactive renderer protected against `enter` crash path.
