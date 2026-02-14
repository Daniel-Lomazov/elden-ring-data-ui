# Repo Deep Dive — 2026-02-14

This document captures a full repository deep dive: what happened historically, what is true now, and what is planned next.

## Scope of Audit

- Recursively reviewed repository structure.
- Read documentation, Python modules, and PowerShell scripts.
- Inspected dataset files in read-only mode (headers + row counts, no data mutation).
- Applied only behavior-safe structural cleanup.

## What Happened (Historical)

Based on session docs and current code, the project has gone through:

1. Histogram reliability and UX hardening
   - Removed side-by-side mode, defaulted to interactive histogram.
   - Added robust fallbacks for interactive click capture failures.
   - Eliminated `enter` crash path by avoiding unconditional context-manager usage.
2. State-management improvements
   - Query-param hydration/persistence.
   - Reset path preserving armor mode.
   - Optimizer weight-state synchronization on highlighted-stat changes.
3. Full armor set UX expansion
   - Added deterministic five-column full-set preview with Overall summary.
4. Operational hardening
   - Added script suite for reset/setup/verify/start/recover/run-all.

## What Is Happening Now (Current State)

### Runtime and environment

- Primary environment: Conda `elden_ring_ui`.
- Run lifecycle is script-driven via `scripts/run-all.ps1`, `scripts/start-app.ps1`, and `scripts/recover-app.ps1`.

### Data integrity and safety posture

- App verifies checksum manifest against `data_checksums.json` at runtime.
- `secure_data.py` is available to regenerate manifest and backup archive.
- Data files were audited read-only in this deep dive.

### Structure tightening completed in this pass

- Introduced `tools/` package for operational Python utilities.
- Moved implementation logic for:
  - `final_check`
  - `optimizer_check`
  - `secure_data`
  into `tools/`.
- Kept original root entrypoints as compatibility wrappers, so existing commands and scripts remain valid.
- Hardened app subprocess behavior to use `sys.executable` for helper invocation in the active runtime.

## Documentation Quality Assessment

### Strong

- `README.md` includes quick start, script automation, and histogram/optimizer behavior notes.
- `docs/session/*` provides traceability of requests, timeline, and nuanced decisions.
- `ui_smoke_checklist.md` gives practical manual verification points.

### Tightened

- Added this deep-dive status document for consolidated “past/present/future” visibility.
- Updated README structure to reflect `tools/` organization and wrapper entrypoints.

## Data Snapshot (Read-Only)

- Datasets are organized under `data/` plus `data/items/`.
- Notable large files: `weapons_upgrades.csv`, `shields_upgrades.csv`.
- Headers and row counts were checked recursively with no data modifications.

## Planned Next Steps

1. Add light automated check orchestration (single command summary report) without introducing heavy test framework.
2. Add minimal architecture map doc for module responsibilities and call graph.
3. Consider optional split of large `app.py` into logically isolated modules only when paired with snapshot-style UI regression checks.
4. Add CI sanity job (imports + optimizer check + script lint) to guard against regressions.

## Non-Goals in This Pass

- No visual changes to UI layout, colors, spacing, or scaling.
- No behavior changes to ranking logic or histogram semantics.
- No data mutations.
