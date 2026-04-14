# Documentation Index

This folder contains both **canonical project documentation** and **internal historical
planning records**. See the sections below to distinguish between them.

---

## Canonical documentation (current and maintained)

| Document | Purpose |
|----------|---------|
| [`../README.md`](../README.md) | Project overview, setup, and runtime command matrix |
| [`DEVELOPMENT.md`](DEVELOPMENT.md) | Architecture guide, module roles, and testing conventions |
| [`specs/optimizer_dialect.md`](specs/optimizer_dialect.md) | Current optimizer request/response contract |
| [`specs/encounter_profiles.md`](specs/encounter_profiles.md) | Encounter input schema expectations |
| [`specs/icon_registry.md`](specs/icon_registry.md) | Icon asset conventions and registry format |
| [`optimizer/README.md`](optimizer/README.md) | Optimizer documentation hub |
| [`developer/icon_and_stat_layout_customization.md`](developer/icon_and_stat_layout_customization.md) | UI layout/icon/detailed-scope customization |
| [`release/README.md`](release/README.md) | Release documentation hub and checklist links |

---

## Internal historical records (archived planning material)

The following documents in this folder are **internal working notes** generated
during development sessions. They are kept for historical reference but do not
represent current architecture or active guidance:

| Document | Status |
|----------|--------|
| [`docs_onboarding_refactor_suggestions.md`](docs_onboarding_refactor_suggestions.md) | Historical — refactor suggestions from early session |
| [`optimizer_dialect_refactor_suggestions.md`](optimizer_dialect_refactor_suggestions.md) | Historical — optimizer dialect iteration notes |
| [`pr_commit_plan_optimizer_v2.md`](pr_commit_plan_optimizer_v2.md) | Historical — optimizer v2 commit planning notes |

The [`session/`](session/) subfolder contains dated deep-dive session notes. These
are internal records of development iterations, not contributor guides.

The [`release/`](release/) subfolder contains both the active release checklist and
internal analysis artifacts (flaw register, risk register, version decisions). See
[`release/README.md`](release/README.md) to understand which are current versus
historical.

---

## Start here (new contributor onboarding)

1. [`../README.md`](../README.md) — project setup, usage, debugging, optimization overview
2. [`DEVELOPMENT.md`](DEVELOPMENT.md) — architecture, module roles, test entry points
3. [`optimizer/README.md`](optimizer/README.md) — optimizer design and usage
4. [`developer/icon_and_stat_layout_customization.md`](developer/icon_and_stat_layout_customization.md) — UI layout customization

If you are preparing a release or verifying a change, also read:

1. [`specs/optimizer_dialect.md`](specs/optimizer_dialect.md) — current optimizer request contract
2. [`specs/encounter_profiles.md`](specs/encounter_profiles.md) — encounter input expectations
3. [`specs/icon_registry.md`](specs/icon_registry.md) — icon asset conventions
4. [`release/README.md`](release/README.md) — release documentation hub and checklist links

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
