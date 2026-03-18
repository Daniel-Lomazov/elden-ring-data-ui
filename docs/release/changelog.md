# Changelog

## Unreleased

### Added
- Release-management backbone under `docs/release/`.
- SemVer policy that defaults to `0.x` until release evidence supports `1.0.0`.
- Live risk register, checklist, and version decision record.
- Explicit `plotly==5.24.1` runtime dependency.
- CI execution of `python -m tools.workspace_verify`.
- Workspace verification that runs unit tests by default.
- Streamlit UI smoke coverage for the default detailed view and core optimization flow.
- File-signature cache keys and regression tests to reduce stale-cache risk in `DataLoader`.
- Verified app launch via Streamlit on `127.0.0.1:8765`.
- Verified app launch again on `127.0.0.1:8766` after the release-hardening changes.

### Fixed
- Missing `plotly` runtime dependency.
- Workspace verification gap that previously allowed unit tests to be skipped.
- DataLoader stale-cache risk caused by cache keys not tracking file signatures.
- App launch verification gap for the documented local run path.
- Git status warnings from transient repo-root `tmp*` artifacts.

### Known Gaps
- `app.py` remains a large monolithic UI file.
- Documentation drift remains a live risk during concurrent changes.

## 0.1.0

Planned first tracked baseline release.

### Highlights
- Streamlit UI for Elden Ring dataset exploration and ranking.
- Optimizer flows for armor and talisman selection.
- Documentation and release-control artifacts established.
- Release gates improved with explicit dependency, CI, backend verification, and automated UI smoke coverage.
