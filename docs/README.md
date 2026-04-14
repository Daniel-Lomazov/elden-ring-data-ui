# Documentation Index

This folder contains repository-internal documentation artifacts, primarily session notes and deep-dive records.

## Start here

If you are onboarding to this repo, read in this order:

1. `../README.md` (project setup, usage, debugging, optimization overview)
2. `session/2026-02-14_repo_deep_dive.md`
3. `session/2026-02-15_startup_and_verify_deep_dive.md`
4. `session/2026-02-15_commit_summary.md`
5. `optimizer/README.md`
6. `developer/icon_and_stat_layout_customization.md`
7. `session/2026-02-16_optimizer_v2_iteration_summary.md`

If you are preparing a release or verifying a change, also read:

1. `../README.md` for the documented run and verification commands.
2. `specs/optimizer_dialect.md` for the current optimizer request contract.
3. `specs/encounter_profiles.md` for encounter input expectations.
4. `specs/icon_registry.md` for icon asset conventions.
5. `release/README.md` for the release documentation hub and checklist links.

## Quick verification

```powershell
uv venv --python 3.11 .venv
uv pip install --reinstall --python .\.venv\Scripts\python.exe -r requirements.txt
.\.venv\Scripts\Activate.ps1
./scripts/run_streamlit_local.ps1
./scripts/stop_streamlit_port.ps1 -Port 8501
./scripts/start-app.ps1 -OpenBrowser:$false
./scripts/recover-app.ps1 -OpenBrowser:$false
./scripts/stop_streamlit_port.ps1 -Port 8501
python -m tools.optimizer_smoke
python -m tools.workspace_verify
python -m unittest discover -s tests -q
python -m unittest tests.test_ui_smoke -q
python -m unittest tests.test_runtime_controller -q
./scripts/verify-workspace.ps1 -Quick
.\.venv\Scripts\python.exe -m tools.workspace_verify --quick
```

Runtime usage notes:

- `run_streamlit_local.ps1` is the direct foreground loop. Stop it with `Ctrl+C` or `stop_streamlit_port.ps1`.
- `start-app.ps1` is the managed detached flow backed by `tools.runtime_controller`; rerunning it against the same app on the same port now performs a controller-backed restart instead of reusing the old session.
- `start-app.ps1`, `recover-app.ps1`, and `run-all.ps1 -RunApp` keep external browser launch disabled by default.
- `.streamlit/config.toml` keeps direct `python -m streamlit run app.py` headless too.
- `recover-app.ps1` remains the explicit managed restart command.
- `run-all.ps1 -RunApp` is the full reset + environment refresh + verify + managed start wrapper.

Expected outcomes:

- App starts at `http://localhost:8501`.
- App binds to localhost by default (not `0.0.0.0`) via `.streamlit/config.toml`, and browser opening stays disabled unless it is explicitly requested.
- `.streamlit/config.toml` keeps Streamlit headless unless browser opening is explicitly requested.
- `start-app.ps1` leaves the app under controller ownership, and rerunning it while that same app already owns the port stops the old session and starts a fresh one.
- `recover-app.ps1` performs a controller-backed restart instead of a second independent launch.
- Managed restart flows only reopen the app in a fresh browser window when `-OpenBrowser` is explicitly requested.
- The dataset chooser includes the supported top-level datasets, including `Weapons Upgrades` and `Shields Upgrades`.
- Upgrade-table datasets render a browse-only progression summary plus grouped item-detail table instead of ranked cards.
- Any deferred dataset that remains registered should stay visible in the selector with a `Not implemented yet` suffix.
- Switching the left-sidebar `Layout:` dropdown to `Side by side` shows two embedded panes with independent dataset interfaces and pane-specific starting datasets.
- Smoke script prints top-5 sections and ends with `optimizer_smoke: SUCCESS`.
- Workspace verification passes for the current tree.
- Unit tests complete without failures in the current environment.
- The focused UI smoke suite covers the default detailed view and the main optimization flow.
- Quick verification mode intentionally skips optimizer and tests.

## Current CI coverage

The repository's GitHub Actions workflow currently runs:

- Linux:
  - `ruff check .`
  - `python -m tools.workspace_verify`
- Windows:
  - `python -m tools.workspace_verify --skip-optimizer --skip-smoke --tests-subset runtime`

`tools.workspace_verify` runs the final check, optimizer check, optimizer smoke, and split unit-test steps by default. On Windows it reports `tests_core` and `tests_runtime_controller` separately. Use `./scripts/verify-workspace.ps1 -Quick` when you want the wrapper to skip optimizer and tests during a fast local loop.

## Session docs (`docs/session/`)

- `2026-02-13_master_todo_and_commit_plan.md`
  - Master todo list and commit-oriented planning snapshot.
- `2026-02-13_request_catalog.md`
  - Normalized request inventory.
- `2026-02-13_timeline.md`
  - Time-ordered execution narrative.
- `2026-02-13_nuanced_change_review.md`
  - Commentary on nuanced or non-obvious implementation choices.
- `2026-02-13_sanity_checks.md`
  - Verification posture and sanity-check patterns.
- `2026-02-14_repo_deep_dive.md`
  - Broader audit of repository state and direction.
- `2026-02-15_startup_and_verify_deep_dive.md`
  - Startup/recovery/verification flow details.
- `2026-02-15_commit_summary.md`
  - High-level change summary from that session.
- `2026-02-15_armor_family_audit.json`
  - Structured armor-family audit output.
- `2026-02-15_armor_family_decisions.json`
  - Structured decision log for armor-family handling.

## Documentation conventions

- Keep `../README.md` user-facing and task-oriented.
- Keep `docs/session/` chronological and implementation-focused.
- Keep `docs/specs/` for stable contracts that are referenced by code and higher-level docs.
- Prefer short, searchable headings and concrete command examples.

### Session file minimum template

Each session doc should include:

- What changed
- How to verify
- Known limitations

## Glossary

- **ALMOP**: armor load/optimization profile (term used in optimizer planning notes).
- **Normalization**: scaling stat values to `[0,1]` for comparable scoring.
- **Dialect request**: structured optimization request (`version/scope/objective/constraints/encounter`).
