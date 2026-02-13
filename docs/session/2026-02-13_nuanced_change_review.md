# Nuanced Change Review — Histogram + Ops Hardening (2026-02-13)

This document reviews the non-trivial implementation decisions and why they were made.

## 1) Histogram View-State Management

### Problem shape
- Multiple state variables controlled one visual concept (view mode), producing drift.

### Nuanced adjustment
- Established a canonical mode key and normalized mode values.
- Reduced post-widget mutations that can violate Streamlit lifecycle constraints.

### Why this matters
- Prevents hidden desync where dropdown text says one mode but renderer runs another.

---

## 2) Interactive Renderer Failure Isolation

### Problem shape
- Failures in interactive event handling could abort the entire histogram section.

### Nuanced adjustment
- Added layered fallback strategy:
  1. primary interactive event capture,
  2. compatibility retry,
  3. non-clickable interactive fallback,
  4. classic histogram fallback in-panel.

### Why this matters
- One flaky component no longer kills the whole chart area.

---

## 3) Root Cause: `enter` Error

### Problem shape
- Renderer used `with target_ui:` regardless of `target_ui` type.
- In interactive-only mode, `target_ui` can be `st` module (not a context manager).

### Nuanced adjustment
- Conditional context wrapper usage only when `__enter__`/`__exit__` exist.
- Direct method calls (`target_ui.warning`, `target_ui.plotly_chart`) for module targets.

### Why this matters
- Fixes the actual source, not the symptom message.

---

## 4) Launch Script Reliability

### Problem shape
- `cmd + conda` startup path could be inconsistent across shell environments.

### Nuanced adjustment
- Launch Streamlit using resolved env Python executable (`python -m streamlit`) from the target conda env path.
- Added explicit listener+HTTP readiness polling and machine-readable startup fields (`READY`, `LISTENER_PID`).

### Why this matters
- Predictable startup behavior independent of shell activation quirks.

---

## 5) Recovery and Ergonomics

### Problem shape
- Users got blocked by nonresponsive foreground terminals and manual recovery steps.

### Nuanced adjustment
- Added `recover-app.ps1` (reset + start).
- Added `-OpenBrowser` support to launch/recover orchestrations.

### Why this matters
- Reduces operator friction and repeated manual interventions.

---

## 6) Minimal-Change Policy Applied

- No redesign of optimizer/data paths.
- No broad component rewrites.
- Changes focused on:
  - histogram rendering path safety,
  - script lifecycle reliability,
  - operational traceability.

This preserves current behavior while eliminating repeated failure patterns.

---

## 7) Histogram Height Alignment

### Problem shape
- Side-by-side panels could visually diverge because classic and interactive embeds used different height targets.

### Nuanced adjustment
- Unified the embed height used by classic and interactive histograms.
- Ensured height configuration flows through both renderers consistently.

### Why this matters
- Keeps classic and interactive panels aligned across modes and resizes.

---

## 8) Weighted-Sum UI Exposure

### Problem shape
- `weighted_sum_normalized` existed but had no UI for per-stat weights.

### Nuanced adjustment
- Added per-stat weight inputs in the sidebar when the method is selected.
- Included weight signatures in cache keys to avoid stale ranking results.

### Why this matters
- Users can now express preference strength directly in the UI.

---

## 9) Optimizer Weight State Sync

### Problem shape
- Changing highlighted stats could leave orphaned weight inputs in state.

### Nuanced adjustment
- Synced and pruned optimizer weight keys whenever the highlighted stats set changes.

### Why this matters
- Prevents stale or misleading weights from leaking into new runs.

---

## 10) Histogram Tuning Range Expansion

### Problem shape
- The tuning controls were too constrained to correct outlier alignment issues.

### Nuanced adjustment
- Expanded width/height ratio bounds and offset bounds uniformly for classic and interactive panels.

### Why this matters
- Enables deeper alignment corrections without code edits.

---

## 11) Interactive Embed Height Trim

### Problem shape
- Interactive panels rendered slightly taller due to extra component padding.

### Nuanced adjustment
- Applied a small, view-specific trim to the interactive embed height override.

### Why this matters
- Reduces subtle visual height drift between classic and interactive panels.
