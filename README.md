# Elden Ring Data UI

A modular Streamlit application for loading, comparing, filtering, and optimizing Elden Ring datasets using least squares regression.

## Quick Start

This repository contains a compact Streamlit app focused on ranking and sorting Elden Ring datasets (armors, weapons, items). The trimmed project keeps only the app, data loader, parsing helpers, and dataset CSVs.

For optimization behavior (including objective directions and scoring), see [Best Armor Optimization (ALMOPs)](#best-armor-optimization-almops).

Windows (Conda, recommended):

```powershell
conda env create -f environment.yml
conda activate elden_ring_ui
streamlit run app.py
```

Cross-platform (venv):

```bash
python -m venv .venv
source .venv/bin/activate  # or .\.venv\Scripts\activate on Windows
pip install -r requirements.txt
streamlit run app.py
```

## Project Structure

```
elden_ring_data_ui/
├── app.py                  # Main minimal Streamlit application (ranking/sorting)
├── histogram_views.py      # Centralized histogram config + render helpers for all views
├── histogram_layout.py     # Shared histogram sizing/layout utilities
├── data_loader.py          # Data loading helper
├── ui_components.py        # Minimal parsing helpers
├── tools/                  # Verification/integrity utilities (with root wrappers)
│   ├── final_check.py
│   ├── optimizer_check.py
│   └── secure_data.py
├── requirements.txt        # Python dependencies
├── environment.yml         # Conda environment (recommended)
├── data/                   # CSV data directory
│   ├── armors.csv
│   ├── weapons.csv
│   └── items/
└── README.md               # This file
```

## Setup

1. Create the conda environment (recommended):

   ```powershell
   conda env create -f environment.yml
   conda activate elden_ring_ui
   ```

2. Or use a Python virtual environment and pip:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Add your CSV files to the `data/` directory and run the app:

   ```powershell
   streamlit run app.py
   ```

## PowerShell Automation (Reset + Setup + Verify + Run)

Use the script suite in [scripts/](scripts/) for clean, repeatable CLI control.

- [scripts/reset-dev-session.ps1](scripts/reset-dev-session.ps1)
   - Stops local Streamlit processes (including port `8501`) for this workspace.
   - Optional cache cleanup (`-RemovePycache`, `-ClearRuffCache`).
- [scripts/ensure-conda-env.ps1](scripts/ensure-conda-env.ps1)
   - Ensures `elden_ring_ui` exists (creates if missing).
   - Installs/updates `requirements.txt` via `conda run`.
- [scripts/verify-workspace.ps1](scripts/verify-workspace.ps1)
   - Verifies required files exist.
   - Runs `final_check.py` and `optimizer_check.py`.
- [scripts/run-all.ps1](scripts/run-all.ps1)
   - Orchestrator that runs reset → env setup → verification.
   - Optionally starts app with `-RunApp` via `start-app.ps1`.
   - Use `-OpenBrowser` to open the app URL automatically.
- [scripts/start-app.ps1](scripts/start-app.ps1)
   - Starts Streamlit in background using the selected env `python -m streamlit` and prints `APP_URL`, `START_PID`, `LISTENER_PID`, and `READY`.
   - Waits for listener + HTTP readiness (`-WaitForReadySeconds`, default `45`).
   - Optional `-OpenBrowser` opens the app URL automatically after readiness.
- [scripts/recover-app.ps1](scripts/recover-app.ps1)
   - Fast recovery shortcut: reset running app processes and immediately restart in background.
   - Optional `-OpenBrowser` opens the app URL automatically.

### One-command full bootstrap

```powershell
./scripts/run-all.ps1 -RunApp
```

Optionally customize launch port/readiness wait:

```powershell
./scripts/run-all.ps1 -RunApp -Port 8501 -WaitForReadySeconds 60
```

Seamless startup (auto-open browser):

```powershell
./scripts/run-all.ps1 -RunApp -OpenBrowser -WaitForReadySeconds 60
```

### Common commands

```powershell
# reset only
./scripts/reset-dev-session.ps1

# setup/repair environment only
./scripts/ensure-conda-env.ps1

# verify app checks only
./scripts/verify-workspace.ps1

# start app in background with URL + PID output
./scripts/start-app.ps1 -ResetFirst

# recover from a stuck/nonresponsive app terminal
./scripts/recover-app.ps1

# recover and auto-open browser
./scripts/recover-app.ps1 -OpenBrowser

# full flow without launching Streamlit
./scripts/run-all.ps1
```

### Legacy setup entrypoint

`setup.ps1` now delegates to `scripts/ensure-conda-env.ps1` for conda flows and still supports `-UseVenv`.

## Notes

- This trimmed project focuses on the ranking/sorting UI. Some earlier modules (filtering, optimization helpers, and tests) were removed during cleanup to keep the codebase minimal and focused.
- If you need the removed features restored, I can add them back or provide separate branches for experimental tooling.
- Root utility scripts `final_check.py`, `optimizer_check.py`, and `secure_data.py` remain stable entrypoints and delegate to implementations in `tools/`.

## Session Documentation Artifacts

- [docs/session/2026-02-13_request_catalog.md](docs/session/2026-02-13_request_catalog.md)
   - Normalized list of user asks and request classifications for this session.
- [docs/session/2026-02-13_timeline.md](docs/session/2026-02-13_timeline.md)
   - Detailed timeline of intent, code touchpoints, and outcomes.
- [docs/session/2026-02-13_nuanced_change_review.md](docs/session/2026-02-13_nuanced_change_review.md)
   - Focused review of high-impact/nuanced implementation decisions.
- [docs/session/2026-02-13_sanity_checks.md](docs/session/2026-02-13_sanity_checks.md)
   - Current sanity-check coverage, commands, and alignment-debug posture.
- [docs/session/2026-02-14_repo_deep_dive.md](docs/session/2026-02-14_repo_deep_dive.md)
   - Deep-dive repo audit summary: what happened, what is current, what is planned next.

## Best Armor Optimization (ALMOPs)

In **Single piece** armor mode, users can choose multiple highlighted stats and the app ranks candidate pieces to find the best armor options (ALMOPs) under those selected objectives.

- **Objective directions:**
   - `weight` is **minimized**.
   - All other selected stats are **maximized**.
- **What “best” means now:** the app currently uses `maximin_normalized` as the default method (configured in code), and returns a ranked list where rank 1 is the strongest current candidate.
- **UI behavior:**
   - 2+ selected stats → optimizer ranking is used.
   - 1 selected stat → legacy single-stat sort behavior is used.
   - Sidebar includes method selection, optional max-weight constraint, and reset action.
   - Reset filters/stats preserves the current armor mode.
   - When `weighted_sum_normalized` is selected, per-stat weight inputs appear in the sidebar.
   - Current ranked rows can be exported to CSV from the main view.

## Full Armor Set Preview (Armors)

The full armor set preview uses a compact, aligned layout to compare per-piece rankings side by side.

- 5 columns: `Helm`, `Armor`, `Gauntlets`, `Greaves`, plus `Overall` summary.
- The `Overall` column sums the highlighted stats across the four pieces for each row.
- Export buttons are available per column.
- The default single-piece selection is `Armor` when available.
- The `Overall` column uses a phantom image spacer to keep rows aligned.

### Where this is implemented

- **Optimizer module:** `optimizer.py`
   - `_is_minimize_stat(stat)`: marks `weight` as a minimize objective.
   - `_normalized_view(df, stats)`: min-max normalizes selected stats and inverts `weight` so higher normalized value is always better for scoring.
   - `_score_maximin_normalized(...)`: computes primary score and tie-break.
   - `optimize_single_piece(...)`: strategy entry point used by the UI.
- **UI entry point:** `app.py` in `main()` where single-piece armor results call `optimize_single_piece(...)` when 2+ stats are selected.

### Input/output contract

- **Inputs (`optimize_single_piece`)**
   - `df`: filtered candidate armor pieces (already narrowed by dataset/piece type/UI filters).
   - `selected_stats`: list of selected stat column names (2+ valid stats required).
   - `method`: optimization strategy key (default `maximin_normalized`).
   - `config`: optional method config (e.g., weights for weighted-sum strategy).
- **Output**
   - Ranked `DataFrame` of candidates, including metadata columns:
      - `__opt_score` (primary score)
      - `__opt_tiebreak` (secondary score)
      - `__opt_method` (method label)
      - `__opt_length` (number of selected stats)
      - `__opt_rank` (1-based ranking)

### Current method details (`maximin_normalized`)

- Conceptually: for each selected stat, values are min-max normalized; `weight` is inverted after normalization so lower weight improves score.
- Primary score: maximum of the **minimum normalized stat** per candidate (best worst-case stat balance).
- Tie-break: mean normalized stat (`__opt_tiebreak`) to prefer stronger overall profiles.
- Output meaning: a full ranked list is produced; UI shows top N according to “Rows to show”.

**Mini example**
- Selected stats: `weight`, `Res: Fir`.
- Piece A: lower weight, medium fire resistance.
- Piece B: higher weight, high fire resistance.
- Because `weight` is minimized (inverted) and fire resistance is maximized, the winner is the piece with the better balanced worst normalized value; ties go to higher mean normalized score.

## Optimization methods

- ✅ **Implemented now (default in UI):** `maximin_normalized`.
- ✅ **Implemented now (with per-stat weights UI):** `weighted_sum_normalized`.
- ⏳ **Recommended next methods to add/expose**
   - **Pareto frontier (non-dominated set):** useful when you want trade-off options instead of a single total order.
   - **Weighted sum (user-configurable weights):** now surfaced with sidebar weights and ready for refinement.
   - **Maximin variants:** useful for stricter fairness-style ranking (e.g., floors/thresholds per stat).
   - **Alternative normalization (z-score/robust scaling):** useful when stat distributions are skewed or have outliers.
   - **Constraint-based selection (e.g., `weight <= X`, then maximize Y):** useful when hard gameplay limits must be respected first.

### Lightweight optimizer check

Run:

```bash
python optimizer_check.py
```

This verifies baseline optimizer behavior without requiring a full test suite.

### UI smoke checklist

Use [ui_smoke_checklist.md](ui_smoke_checklist.md) for quick manual verification of sort, row limits, dev table columns, constraints, and export behavior.

## Histogram Customization (Single Control Surface)

All histogram behavior is centralized in [histogram_views.py](histogram_views.py), so developers can make one change and have it propagate to:

- Classic view
- Interactive (click-to-set) view

Manual tuning controls have been removed; histogram sizing now uses fixed defaults from [histogram_layout.py](histogram_layout.py). Interactive render height is padded and margins are adjusted to avoid axis-label clipping.

### Where to edit

- `HISTOGRAM_CONFIG` in [histogram_views.py](histogram_views.py): visual labels, colors, fonts, spacing, axes, cutoff line style, and compute defaults.
- `build_histogram_spec(...)` in [histogram_views.py](histogram_views.py): shared computational logic (bin count, bin size, y-axis headroom/ticks).
- `render_classic_histogram(...)` in [histogram_views.py](histogram_views.py): classic renderer using the shared config/spec.
- `build_interactive_histogram_figure(...)` in [histogram_views.py](histogram_views.py): interactive renderer figure using the same shared config/spec.
- `get_clicked_weight(...)` in [histogram_views.py](histogram_views.py): click-to-weight behavior for interactive mode.

### Common global tweaks

Edit `HISTOGRAM_CONFIG` keys once to affect all views:

- `compute.bin_count`: number of histogram intervals.
- `layout.bargap`: spacing between bars.
- `layout.height`, `layout.margin`: chart size and padding.
- `fonts.bold`, `fonts.axis_label_size`, `fonts.axis_title_size`: text appearance.
- `colors.within`, `colors.above`, `colors.cutoff`, `colors.grid`: visual palette.
- `x_axis.*`, `y_axis.*`: tick spacing, tick thickness, axis standoff.
- `cutoff.*`: vertical max-weight marker line style.

### Integration point in app

The app only orchestrates mode selection and interaction in [app.py](app.py); rendering and shared styling/math come from [histogram_views.py](histogram_views.py).

## Troubleshooting

- If packages fail to install, recreate the environment or use the venv approach above.
- Ensure CSV files are present in `data/`.

---

<!-- Removed assistant-suggested helper offer to keep README focused and minimal -->
<!-- CI trigger: heartbeat -->

## CI Schedule

- **Workflow:** `.github/workflows/ci.yml`
- **Schedule:** hourly at `:00` UTC (cron `0 * * * *`).
- **Manual runs:** can be started from the Actions UI (`workflow_dispatch`).

This CI job runs linting (`ruff`) and a smoke-import test to ensure core modules import cleanly. Adjust the schedule or workflow in `.github/workflows/ci.yml` if you prefer a different cadence.

### Manually triggering the workflow

You can run the CI workflow manually from GitHub (useful for immediate checks):

- Open the repository on GitHub and go to the **Actions** tab.
- Select the **CI** workflow from the list on the left.
- Click the **Run workflow** button on the right.
- Choose the branch (default: `main`) and click **Run workflow**.

Or run it from the command line with the GitHub CLI (authenticated):

```bash
gh workflow run .github/workflows/ci.yml --ref main
```
