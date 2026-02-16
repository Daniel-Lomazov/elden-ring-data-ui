# Elden Ring Data UI

A Streamlit app for exploring Elden Ring datasets, ranking candidates, and optimizing armor/talisman choices with multi-stat scoring.

## What this project does

- Loads CSV datasets from `data/` (including `data/items/`).
- Provides a UI for sorting/ranking and side-by-side comparison workflows.
- Supports optimization modes for armor and talismans (single and set-based flows).
- Includes script-based startup, verification, and recovery workflows for fast development loops.

## Documentation

- `docs/README.md` — onboarding index for docs and session deep dives.
- `docs/optimizer/README.md` — optimizer documentation hub.
- Latest deep dive: `docs/session/2026-02-15_startup_and_verify_deep_dive.md`.
- Latest commit summary: `docs/session/2026-02-15_commit_summary.md`.

## Repository layout

```text
elden_ring_data_ui/
├── app.py                         # Main Streamlit UI
├── data_loader.py                 # CSV loading, column profiles, cache-backed read helpers
├── optimizer/                     # Optimization package (legacy + dialect API + strategies)
├── histogram_views.py             # Histogram rendering + interaction config
├── histogram_layout.py            # Shared histogram sizing/layout helpers
├── ui_components.py               # Parsing/UI utility helpers
├── scripts/                       # PowerShell automation: setup, verify, run, recover
├── tools/                         # Verification utilities used by scripts
├── data/                          # Datasets and load-profile config
│   ├── active_datasets.json       # Default active datasets in app
│   └── column_loading_instructions.json
└── docs/session/                  # Session notes, deep dives, and audits
```

## Setup

### Option A (recommended): Conda

```powershell
conda env create -f environment.yml
conda activate elden_ring_ui
python -m streamlit run app.py
```

### Option B: venv + pip

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m streamlit run app.py
```

## Fast start commands (Windows PowerShell)

The `scripts/` folder is the best path for repeatable runs.

- Full bootstrap + run app:

  ```powershell
  ./scripts/run-all.ps1 -RunApp
  ```

- Fast relaunch while iterating UI:

  ```powershell
  ./scripts/run-all.ps1 -SkipReset -QuickVerify -RunApp -OpenBrowser
  ```

- Ultra-fast relaunch (skip reset/env/verify):

  ```powershell
  ./scripts/run-all.ps1 -UltraQuick -RunApp
  ```

- Verify only:

  ```powershell
  ./scripts/verify-workspace.ps1
  ```

- Recovery if app is stuck/nonresponsive:

  ```powershell
  ./scripts/recover-app.ps1
  ```

## App usage (current)

### Datasets

- Default active datasets are controlled by `data/active_datasets.json`.
- The current default is:
  - `armors`
  - `talismans`
- Additional datasets can be present in `data/` and `data/items/`; app coverage for non-primary datasets may be partial/placeholder depending on view.

### Ranking and optimization behavior

- Single-stat selection uses direct sort behavior.
- Multi-stat selection (2+ valid stats) uses optimizer ranking.
- Current optimization methods:
  - `maximin_normalized` (default)
  - `weighted_sum_normalized`
- Optimization metadata columns include:
  - `__opt_score`
  - `__opt_tiebreak`
  - `__opt_method`
  - `__opt_rank`

### Objective direction rules

- `weight` is minimized.
- Selected non-weight stats are maximized.
- For normalization-based methods, `weight` is inverted after normalization so higher normalized score is always better.

## Loading and reloading data

### Initial loading

- `DataLoader` reads from `data/` and `data/items/`.
- Column-loading profiles are driven by `data/column_loading_instructions.json`.
- Streamlit caching is used for file reads and loader resources.

### If CSV content changes while the app is running

Use one of these reliable refresh paths:

1. **Restart app process (recommended for certainty):**

   ```powershell
   ./scripts/recover-app.ps1
   ```

2. **Full reset + verify + launch:**

   ```powershell
   ./scripts/run-all.ps1 -RunApp
   ```

3. **Manual restart:** stop Streamlit process, then rerun:

   ```powershell
   python -m streamlit run app.py
   ```

## Debugging and verification

### Quick health checks

- Lightweight import/data sanity:

  ```powershell
  python -m tools.final_check
  ```

- Optimizer sanity checks:

  ```powershell
  python -m tools.optimizer_check
  ```

- Dialect + encounter smoke checks:

  ```powershell
  python -m tools.optimizer_smoke
  ```

- Consolidated verify pipeline:

  ```powershell
  ./scripts/verify-workspace.ps1
  ```

### Typical issues and fixes

- **Issue: `Conda environment 'elden_ring_ui' was not found`**
  - Run `./scripts/ensure-conda-env.ps1`

- **Issue: app port conflict / stale Streamlit process**
  - Run `./scripts/reset-dev-session.ps1`
  - Then relaunch with `./scripts/start-app.ps1`

- **Issue: datasets not loading as expected**
  - Confirm CSV exists in `data/` or `data/items/`
  - Check dataset key/path mapping in `data_loader.py`
  - Run `python -m tools.final_check` for a fast probe

- **Issue: optimization output looks wrong**
  - Verify selected stat names match real columns
  - Ensure at least 2 valid stats for optimization mode
  - Run `python -m tools.optimizer_check`

## Optimization internals (where to edit)

- `optimizer/legacy.py`
  - Method registry and dispatch
  - Objective direction handling (`weight` minimization)
  - Scoring implementations:
    - `_score_maximin_normalized`
    - `_score_weighted_sum_normalized`

- `optimizer/api.py`
  - Dialect-first entrypoint `optimize(df, request)`

- `optimizer/dialect.py`
  - Request loading, validation, canonicalization

- `optimizer/strategies/encounter_survival.py`
  - Encounter-aware survival objective `M` and composite `J`

- `optimizer/strategies/full_set_prune.py`
  - Full-set armor pruning + enumeration

- `app.py`
  - UI controls for optimization method selection
  - Session-level caching for optimizer ranking results
  - View-specific rendering of ranked outputs

## Next optimization refinement track

A focused, incremental path to “refine to perfection”:

1. Add per-method diagnostics in UI (show normalized stat contributions).
2. Add robust tie-break controls (secondary/tertiary sort strategy selection).
3. Add optional hard constraints (for example, strict max weight before scoring).
4. Add Pareto frontier mode for trade-off exploration (non-dominated set view).
5. Validate against curated build scenarios and add repeatable benchmark cases.

## Session and deep-dive docs

See `docs/session/` for historical notes and implementation deep dives. Start with:

- `docs/session/2026-02-14_repo_deep_dive.md`
- `docs/session/2026-02-15_startup_and_verify_deep_dive.md`
- `docs/session/2026-02-15_commit_summary.md`

## Notes

- Validation and data-integrity helpers live in `tools/`.
- `setup.ps1` remains available as a legacy entry point.
