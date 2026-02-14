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
- Manual UI check: verify default histogram view is Interactive and axis labels are fully visible.
- Manual UI check: verify full armor set preview shows five columns with aligned rows.

## Operational Commands (Canonical)

- Full verify + run (recommended):
  - `./scripts/run-all.ps1 -RunApp -OpenBrowser -WaitForReadySeconds 60`
- Fast recovery:
  - `./scripts/recover-app.ps1 -OpenBrowser`
- Verify only:
  - `./scripts/verify-workspace.ps1`

## Histogram Alignment Debug Posture

Current mechanism:
- Manual tuning controls are removed; histogram sizing is fixed in code.
- Interactive render height includes extra padding and larger bottom margin to avoid clipped axes.

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
