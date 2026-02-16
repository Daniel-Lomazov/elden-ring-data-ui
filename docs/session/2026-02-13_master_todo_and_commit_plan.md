# Master TODO + Commit Plan (Session-wide) — 2026-02-13

This is the consolidated, actionable list of all major issues encountered from session start through current state, plus a commit policy for what should and should not be tracked.

## A) Session-Wide TODO (Detailed)

### 1) Histogram Rendering Reliability

- [x] Fix interactive histogram cropping/truncation in constrained layouts.
- [x] Keep chart tuning controls consistently located under each chart block.
- [x] Prevent view-mode desync between dropdown and rendered output.
- [x] Normalize histogram mode state (single canonical value).
- [x] Harden side-by-side rendering to keep classic/interactive panel parity.
- [x] Add safer interactive fallback behavior instead of full block failure.
- [x] Resolve root cause for `Histogram render error: enter` by avoiding unconditional context-manager usage on non-container targets.
- [x] Final visual alignment polishing across all modes under browser resize conditions (unified embed height).
- [x] Expand tuning ranges and trim interactive embed height to reduce subtle panel drift.
- [x] Remove side-by-side option and make Interactive the default histogram view.
- [x] Remove manual tuning controls and lock histogram sizing to fixed defaults.
- [x] Increase interactive render height/margins to avoid axis-label clipping.

### 2) State and UX Consistency

- [x] Consolidate armor-mode handling and explicit placeholder behavior for non-implemented modes.
- [x] Persist and hydrate UI state via query params for repeatable sessions.
- [x] Add reset path for filters/stats and tuning state.
- [x] Preserve armor mode on reset (no forced return to single-piece mode).
- [x] Add safer numeric formatting and consistent metric rendering.
- [x] Preserve multi-stat ranking behavior for single-piece armor optimization.
- [x] Sync optimizer weight inputs when highlighted stats change.
- [x] Default single-piece armor selection to `Armor` when available.

### 3) Full Armor Set Preview UX

- [x] Implement five-column full-set preview: Helm/Armor/Gauntlets/Greaves/Overall.
- [x] Add Overall summary column that totals highlighted stats per row.
- [x] Render compact full-set cards via HTML for stable spacing and alignment.
- [x] Add phantom image spacer in Overall column for row alignment.
- [x] Center column headers and tighten card layout controls.
- [x] Add configurable column gaps via spacer columns.

### 3) Optimization and Ranking

- [x] Add optimizer module with method abstraction.
- [x] Implement `maximin_normalized` with objective-direction handling (`weight` minimized).
- [x] Implement `weighted_sum_normalized` method path.
- [x] Add output metadata (`__opt_score`, `__opt_rank`, etc.) and dev diagnostics view.
- [x] Expose `weighted_sum_normalized` weights in the sidebar and pass through to optimizer.
- [ ] Optional future: expose richer optimizer selection UX and Pareto-style views.

### 4) Ops/Automation Reliability

- [x] Add deterministic reset script (`scripts/reset-dev-session.ps1`).
- [x] Add deterministic env ensure/update script (`scripts/ensure-conda-env.ps1`).
- [x] Add workspace verify script (`scripts/verify-workspace.ps1`).
- [x] Add app startup script with readiness checks (`scripts/start-app.ps1`).
- [x] Add orchestration script (`scripts/run-all.ps1`).
- [x] Add one-command recovery script (`scripts/recover-app.ps1`).
- [x] Add optional browser auto-open (`-OpenBrowser`) flow.

### 5) Validation and Traceability

- [x] Keep `python -m tools.final_check` passing.
- [x] Add and run `python -m tools.optimizer_check`.
- [x] Verify app readiness by both listener and HTTP checks.
- [x] Document request catalog, timeline, nuanced review, sanity checks.
- [x] Keep session docs updated after next histogram-alignment pass.

---

## B) Commit Policy (Developer-only vs Commit-worthy)

### Commit-worthy (track in git)

1. **Application source code**
   - `app.py`, `data_loader.py`, `ui_components.py`
   - `histogram_views.py`, `histogram_layout.py`, `optimizer.py`, `tuning_controls.py`
2. **Dependency/runtime definitions**
   - `requirements.txt`, `environment.yml`
3. **Automation scripts**
   - `scripts/*.ps1` (except logs/artifacts)
4. **Verification/check scripts**
   - `tools/final_check.py`, `tools/optimizer_check.py`, `tools/secure_data.py`
5. **Documentation**
   - `README.md`, `ui_smoke_checklist.md`, `docs/session/*.md`
6. **Data assets**
   - `data/**/*.csv` should remain committed (as requested).

### Developer-only / local-generated (do NOT track)

- Python and tool caches: `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`
- Local app state: `.streamlit/`
- Runtime logs: `*.log`, including `scripts/last-seamless-run.log`
- Local backup archives: `*.zip`, `data_backup_*.zip`
- Generated local manifests/maps: `data_checksums.txt`, `data_checksums.json`, `armor_column_map.json`
- Local IDE noise: `.vscode/`, `.idea/`, swap files
- Local workspace file: `elden_ring_data_ui.code-workspace` (optional personal preference file)

---

## C) Immediate Commit Checklist (Current)

- [x] Review modified + untracked files.
- [x] Classify commit vs local-only files.
- [ ] Ensure `.gitignore` reflects this policy (especially stop ignoring core tracked files).
- [ ] Stage commit-worthy files only.
- [ ] Run verification checks (`python -m tools.final_check`, `python -m tools.optimizer_check`).
- [ ] Commit with one comprehensive message.
- [ ] Push to `origin/main`.

---

## D) Post-Commit Next Technical Focus

1. Histogram visual parity pass (classic vs interactive).
2. Browser-resize regression pass with debug border toggles.
3. Keep all changes minimal and constrained to rendering/layout paths.

---

## E) Current Session Focus (Planned + Executed)

1. Histogram alignment polish across modes (completed).
2. Expose weighted-sum optimizer weights in the UI (completed).
3. Tighten optimizer weight state sync/reset behavior (completed).
