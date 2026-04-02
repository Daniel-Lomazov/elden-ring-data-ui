# Elden Ring Data UI

A Streamlit app for exploring Elden Ring datasets, ranking candidates, and optimizing armor/talisman choices with multi-stat scoring.

## What this project does

- Loads CSV datasets from `data/` (including `data/items/`).
- Provides a UI for sorting/ranking and side-by-side comparison workflows.
- Supports optimization modes for armor and talismans (single and set-based flows).
- Includes script-based startup, verification, and recovery workflows for fast development loops.
- Depends on `plotly` for chart and interaction paths used by the UI.

## Documentation

- `docs/README.md` — onboarding index for docs and session deep dives.
- `docs/optimizer/README.md` — optimizer documentation hub.
- `docs/developer/icon_and_stat_layout_customization.md` — current UI layout/icon/detailed-scope customization points.
- Latest deep dive: `docs/session/2026-02-16_optimizer_v2_iteration_summary.md`.
- Latest commit summary: `docs/session/2026-02-15_commit_summary.md`.

## Repository layout

```text
elden_ring_data_ui/
├── app.py                         # Main Streamlit UI
├── app_support/                   # Detailed-scope text/focus/placeholders helpers
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

### Runtime command matrix

| Command | Use it when | Lifecycle owner | Browser behavior | Logical restart path |
|---------|-------------|-----------------|------------------|----------------------|
| `./scripts/run_streamlit_local.ps1` | You want a direct foreground Streamlit session while developing | Current terminal only | Streamlit prints the URL; browser opening is manual | `Ctrl+C`, then rerun `./scripts/run_streamlit_local.ps1` |
| `./scripts/start-app.ps1` | You want the managed detached app flow | `tools.runtime_controller` | Does not open an external browser by default; pass `-OpenBrowser` to opt in to a fresh window after start/restart | `./scripts/recover-app.ps1` |
| `./scripts/recover-app.ps1` | The managed app needs a clean controller-backed restart | `tools.runtime_controller` | Does not open an external browser by default; pass `-OpenBrowser` to opt in to a fresh window after recovery | This is the preferred managed restart command |
| `./scripts/stop_streamlit_port.ps1 -Port 8501` | You want to stop the current local app session | `tools.runtime_controller` by default; emergency hard kill only with `-ForceAnyListener` | None | Follow with `start-app.ps1` or `run_streamlit_local.ps1` |
| `./scripts/run-all.ps1 -RunApp` | You want reset + environment + verification + managed start in one command | `run-all.ps1` orchestrates, controller owns the final app lifecycle | No external browser by default; pass `-OpenBrowser` to opt in | Rerun `run-all.ps1 -RunApp` or use `recover-app.ps1` after the initial bootstrap |

### Practical restart rules

- If you started the app with `run_streamlit_local.ps1`, restart it by stopping that terminal with `Ctrl+C` and running `run_streamlit_local.ps1` again.
- If you rerun `start-app.ps1` while the same app still owns port `8501`, the controller now closes that current session and starts a fresh one instead of reusing the old window.
- If you started the app with `start-app.ps1` or `run-all.ps1 -RunApp`, restart it with `recover-app.ps1` when you want the explicit managed restart command.
- By default, the app stays headless and local. Managed wrappers suppress external browser launch, and `.streamlit/config.toml` keeps Streamlit headless unless you explicitly opt in to browser opening.
- If you only need to stop the app, use `stop_streamlit_port.ps1 -Port 8501`.
- If you need the slow but highest-confidence cycle, use `run-all.ps1 -RunApp`.

- Foreground local-only run (recommended while developing):

  ```powershell
  ./scripts/run_streamlit_local.ps1
  ```

- Stop app by closing terminal (`Ctrl+C`) or explicitly freeing port 8501:

  ```powershell
  ./scripts/stop_streamlit_port.ps1 -Port 8501
  ```

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

## Localhost security defaults

- Streamlit defaults are configured in `.streamlit/config.toml` to bind to `localhost` on port `8501`.
- `.streamlit/config.toml` keeps raw `python -m streamlit run app.py` headless by default, so the app stays inside the editor workflow unless you opt into browser opening.
- CORS and XSRF protection are enabled by default.
- `./scripts/run_streamlit_local.ps1` runs in the current terminal so stopping is explicit (`Ctrl+C`).
- `./scripts/start-app.ps1` intentionally launches a detached/background process for convenience, so it can continue after terminal/editor close.

### Optional LAN sharing (advanced)

- LAN exposure is opt-in. If you change server address to `0.0.0.0` or pass `--server.address 0.0.0.0`, devices on your network may be able to access the app.
- Only use LAN mode on trusted networks and restore localhost defaults when finished.

## App usage (current)

### Datasets

- Default active datasets are controlled by `data/active_datasets.json`.
- The default selector now prioritizes the full supported top-level set:
  - `armors`
  - `talismans`
  - `ashesOfWar`
  - `bosses`
  - `creatures`
  - `incantations`
  - `locations`
  - `npcs`
  - `shields`
  - `shields_upgrades`
  - `skills`
  - `sorceries`
  - `spiritAshes`
  - `weapons`
  - `weapons_upgrades`
  - Untouched `data/items/*` catalog datasets stay out of the main selector until they get a curated UI pass.
- If a registry entry is present but still deferred, the selector label appends `Not implemented yet` instead of silently hiding it.
- Upgrade tables use a browse-only progression view with grouped item details rather than the ranked item-card layout.

### Side-by-side mode

- Use the top-level `Layout:` control to switch from `Single dataset` to `Side by side`.
- Side-by-side mode renders two embedded panes, each running the existing dataset interface independently.
- Use `Left pane dataset:` and `Right pane dataset:` to choose starting datasets for each pane.
- Use `Pane height:` to increase the embedded pane height when you want more of each interface visible without scrolling.
- The embedded panes still use the full dataset UI, so each pane can switch datasets, views, ranking controls, and detail inspectors independently.

### Ranking and optimization behavior

- Single-stat selection uses direct sort behavior.
- Multi-stat selection (2+ valid stats) uses optimizer ranking.
- Upgrade-table datasets are browse-only and do not expose ranking controls.
- Current optimization methods:
  - `Maximin` (`maximin_normalized`, default)
  - `Weighted Sum` (`weighted_sum_normalized`)
- Optimization engines in UI (Optimization view):
  - `Legacy Ranking` (`legacy`)
  - `Advanced Optimizer` (`advanced`)
- Armor full-scope behavior:
  - `Advanced Optimizer` + `Stat Ranking` performs true full-set ranking using prune-first combination search.
  - `Advanced Optimizer` + `Encounter Survival` performs full-set encounter ranking.
  - `Advanced Optimizer` + `Custom` scope supports slot-lock constraints (`include_names`) while optimizing the remaining slots.
  - `Legacy Ranking` full-scope preview remains a per-slot composed view (not full-set combinatorial optimization).
- Weighted Sum now only uses stats whose weight is greater than zero.
  - If exactly one weighted stat remains active, ranking falls back to that stat's single-stat sort behavior.
  - If all weights are zero, optimization is blocked with a validation error.
- Optimization metadata columns include:
  - `__opt_score`
  - `__opt_tiebreak`
  - `__opt_method`
  - `__opt_rank`

### Where to access Advanced Optimizer in the app

- Dataset: `armors` (recommended)
- View mode: `Optimization view` (do not use `Detailed view` for this flow)
- In the right control column set:
  - `Optimization engine` = `Advanced Optimizer`
  - `Objective` = `Encounter Survival` (or keep `Stat Ranking`)
  - `Choose Scope` = `Custom` to lock specific armor slots and optimize around them
  - `Encounter profile` = one of `data/profiles/*.yaml`
  - `Status Penalty Weight` as desired

### Stat naming and icon conventions

- UI-facing stat labels are now centralized in `data/stat_ui_map.json`.
- The app uses permanently capitalized display names such as:
  - `Holy Damage Negation`
  - `Fire Damage Negation`
  - `Strike Damage Negation`
  - `Poison Resistance`
  - `Scarlet Rot Resistance`
  - `Bleed Resistance`
  - `Frost Resistance`
  - `Sleep Resistance`
  - `Madness Resistance`
  - `Death Blight Resistance`
- Stat icon metadata/provenance is maintained in `data/icons/icons.json`.
- App stat labels prefer local icon assets from `data/icons/icons.json` (`local_path`) and fall back to emoji labels if files are missing.
- Verify local icon asset availability with:

  ```powershell
  python scripts/verify_icon_assets.py
  ```
- Aggregated resistance names (`Immunity`, `Robustness`, `Focus`, `Vitality`) are kept internally for compatibility but hidden from user-facing card/table output.

### Launch behavior (new window)

- `./scripts/start-app.ps1` opens app URLs in a dedicated Edge window (`--new-window`) rather than opening a new tab.
- If an app window for the same localhost port already exists, the script focuses and refreshes it.

### Objective direction rules

- `weight` is minimized.
- Selected non-weight stats are maximized.
- For normalization-based methods, `weight` is inverted after normalization so higher normalized score is always better.

## Loading and reloading data

### Initial loading

- `DataLoader` reads from `data/` and `data/items/`.
- Column-loading profiles are driven by `data/column_loading_instructions.json`.
- Streamlit caching is used for file reads and loader resources.
- Cached dataset and column-instruction reads are keyed by each file's current size and modification time, so normal file edits should invalidate stale reads without a manual cache reset.

### If CSV content changes while the app is running

Use one of these reliable refresh paths:

1. **Managed restart for controller-owned sessions (recommended when you used `start-app.ps1` or `run-all.ps1 -RunApp`):**

   ```powershell
   ./scripts/recover-app.ps1
   ```

2. **Full reset + verify + launch:**

   ```powershell
   ./scripts/run-all.ps1 -RunApp
   ```

3. **Manual foreground restart for direct local runs:** stop Streamlit with `Ctrl+C`, then rerun:

   ```powershell
   ./scripts/run_streamlit_local.ps1
   ```

Regression note:

- File-based data loading and column-instruction caching are keyed by file signature, so normal edits invalidate stale reads.
- This behavior is covered by tests in `tests/`.

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

- Full regression suite:

  ```powershell
  python -m unittest discover tests
  ```

- Focused UI smoke suite:

  ```powershell
  python -m unittest tests.test_ui_smoke
  ```

- Fast verify mode:

  ```powershell
  ./scripts/verify-workspace.ps1 -Quick
  ```

### CI coverage

- Current GitHub Actions CI runs `ruff check .` and `python -m tools.workspace_verify`.
- `tools.workspace_verify` runs `tools.final_check`, `tools.optimizer_check`, and `unittest discover tests` by default.
- The unit-test suite now includes Streamlit UI smoke coverage for the default detailed view and the main optimization flow.
- `./scripts/verify-workspace.ps1 -Quick` keeps the wrapper fast by skipping optimizer and test execution.
- Use `python -m tools.workspace_verify` or the wrapper before release-critical changes when you need full verification.

### Typical issues and fixes

- **Issue: `Conda environment 'elden_ring_ui' was not found`**
  - Run `./scripts/ensure-conda-env.ps1`

- **Issue: app port conflict / stale Streamlit process**
  - Run `./scripts/reset-dev-session.ps1`
  - Or run `./scripts/stop_streamlit_port.ps1 -Port 8501`
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

- `optimizer/strategies/full_set_stat_rank.py`
  - Full-set stat-rank pruning + enumeration

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
